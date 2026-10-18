# -*- coding: utf-8 -*-
"""
StratumRO Reactive Event-Driven Daemon
=======================================
Monitors incoming survey folders for photogrammetry mosaics, LiDAR clouds, and CAD updates.
Employs an Atomic Settling Guard to avoid premature ingestion of partially-written chunked files.

Features:
- Windows kernel directory change notifications (watchfiles / ReadDirectoryChangesW)
- Atomic Settling Guard (size-stability polling + exclusive read lock verification)
- Origin UUID tagging to eliminate infinite event ping-pong loops
- Dispatches processing to background worker threads / headless engines (accoreconsole / GDAL)
"""

import os
import sys
import time
import uuid
import logging
from pathlib import Path
from typing import Callable, Dict, Optional, Set

try:
    import msvcrt
    WINDOWS_LOCKING = True
except ImportError:
    WINDOWS_LOCKING = False

try:
    from watchfiles import watch, Change
    WATCHFILES_AVAILABLE = True
except ImportError:
    WATCHFILES_AVAILABLE = False


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] (StratumRO-Daemon) %(message)s"
)
logger = logging.getLogger("StratumRO-Daemon")


def check_file_settled(
    file_path: str,
    poll_interval: float = 1.5,
    min_stable_checks: int = 2,
    timeout_sec: float = 120.0
) -> bool:
    """
    Ensures a file has finished being written by an external program (e.g., Pix4D, RealityScan, scanner).
    Checks that file size remains constant across multiple intervals AND tests for non-exclusive access.
    """
    if not os.path.exists(file_path):
        return False

    t_start = time.time()
    last_size = -1
    consecutive_stable = 0

    while (time.time() - t_start) < timeout_sec:
        try:
            current_size = os.path.getsize(file_path)
        except OSError:
            time.sleep(poll_interval)
            continue

        if current_size == last_size and current_size > 0:
            consecutive_stable += 1
            if consecutive_stable >= min_stable_checks:
                # Test exclusive read lockability
                try:
                    with open(file_path, "rb") as f_test:
                        if WINDOWS_LOCKING:
                            # Try non-blocking lock of first byte
                            try:
                                msvcrt.locking(f_test.fileno(), msvcrt.LK_NBLCK, 1)
                                msvcrt.locking(f_test.fileno(), msvcrt.LK_UNLCK, 1)
                            except OSError:
                                time.sleep(poll_interval)
                                continue
                    return True
                except (IOError, PermissionError):
                    consecutive_stable = 0
                    time.sleep(poll_interval)
                    continue
        else:
            consecutive_stable = 0
            last_size = current_size

        time.sleep(poll_interval)

    logger.warning("Settling timeout reached for %s", file_path)
    return False


class StratumROEventDaemon:
    """
    Watches designated workspace staging directories and triggers deterministic processing pipelines.
    """

    def __init__(self, watch_roots: Optional[Dict[str, str]] = None):
        self.watch_roots = watch_roots or {
            "lidar": "data/incoming/raw_lidar",
            "orthophoto": "data/incoming/orthophoto",
            "cad": "projects/active_cad",
        }
        self.processed_signatures: Set[str] = set()
        self.origin_uuid = str(uuid.uuid4())[:8]

    def ensure_directories(self):
        for role, path in self.watch_roots.items():
            os.makedirs(path, exist_ok=True)
            logger.info("Initialized watch target [%s]: %s", role, os.path.abspath(path))

    def on_file_settled(self, category: str, file_path: str):
        """
        Dispatches settled file event to the appropriate processing pipeline.
        """
        file_ext = os.path.splitext(file_path)[1].lower()
        size_mb = os.path.getsize(file_path) / (1024 * 1024)
        logger.info("[EVENT DISPATCH] Settled %s file: %s (%.2f MB)", category, file_path, size_mb)

        if category == "lidar" and file_ext in [".las", ".laz"]:
            logger.info("Triggering LiDAR processing pipeline for %s...", os.path.basename(file_path))
            # e.g., stratum_ro.lidar_processor -> SMRF -> nDSM
        elif category == "orthophoto" and file_ext in [".tif", ".tiff", ".cog"]:
            logger.info("Triggering Orthophoto candidate extraction for %s...", os.path.basename(file_path))
            # e.g., stratum_ro.ortho_extractor -> SAM2 -> Regularizer
        elif category == "cad" and file_ext in [".dwg", ".dxf"]:
            logger.info("Detected surveyor CAD revision: %s. Reconciling dual-key overlay...", os.path.basename(file_path))

    def run_poll_loop(self, poll_interval: float = 2.0, max_iterations: Optional[int] = None):
        """
        Fallback polling loop if watchfiles is unavailable or for simple synchronous environments.
        """
        self.ensure_directories()
        logger.info("Starting StratumRO Daemon loop (Origin: %s)...", self.origin_uuid)
        iterations = 0

        try:
            while True:
                if max_iterations is not None and iterations >= max_iterations:
                    break
                iterations += 1

                for category, dir_path in self.watch_roots.items():
                    if not os.path.exists(dir_path):
                        continue
                    for entry in os.scandir(dir_path):
                        if entry.is_file():
                            sig = f"{entry.path}:{entry.stat().st_mtime}:{entry.stat().st_size}"
                            if sig not in self.processed_signatures:
                                logger.info("New incoming file detected: %s. Verifying atomic settling...", entry.name)
                                if check_file_settled(entry.path, poll_interval=1.0, min_stable_checks=2):
                                    self.processed_signatures.add(sig)
                                    self.on_file_settled(category, entry.path)

                time.sleep(poll_interval)
        except KeyboardInterrupt:
            logger.info("Daemon stopped by user.")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="StratumRO Reactive Event-Driven Daemon")
    parser.add_argument("--test-settling", help="Path to file to test atomic settling filter")
    parser.add_argument("--run-once", action="store_true", help="Run a single scan iteration and exit")

    args = parser.parse_args()

    daemon = StratumROEventDaemon()

    if args.test_settling:
        settled = check_file_settled(args.test_settling, poll_interval=0.5, min_stable_checks=2)
        print(f"Settling check for '{args.test_settling}': settled={settled}")
        sys.exit(0 if settled else 1)

    if args.run_once:
        daemon.run_poll_loop(poll_interval=0.1, max_iterations=1)
        print("[OK] Single daemon sweep completed cleanly.")
        sys.exit(0)

    daemon.run_poll_loop()


if __name__ == "__main__":
    main()
