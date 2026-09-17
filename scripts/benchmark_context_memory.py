# -*- coding: utf-8 -*-
"""
Performance Benchmarking Suite for Context & Memory Engine (MD 4 Section 33).
Measures:
1. Cold context snapshot creation latency
2. Cached context snapshot retrieval latency
3. SQLite memory write & query latency
4. Combined Agent Context Package generation latency
"""

import json
import os
import sys
import tempfile
import time
from pathlib import Path

# Ensure repository root is in sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from stratum_ro.ai.context import ContextEngine, get_agent_context_package
from stratum_ro.ai.memory.session import SessionMemory


def run_benchmarks():
    print("=" * 65)
    print("  STRATUMRO-QGIS: CONTEXT & MEMORY PERFORMANCE BENCHMARKS")
    print("=" * 65)

    results = {}

    # 1. Cold Context Snapshot
    engine = ContextEngine(config_path="config.yaml", cache_ttl_sec=10.0)
    engine.invalidate()

    t0 = time.perf_counter()
    cold_snap = engine.get_snapshot()
    t_cold_ms = (time.perf_counter() - t0) * 1000.0
    results["cold_context_ms"] = round(t_cold_ms, 2)
    print(f"[*] Cold Context Snapshot:        {t_cold_ms:.2f} ms")

    # Verify size
    snap_size_bytes = len(json.dumps(cold_snap).encode("utf-8"))
    results["snapshot_size_bytes"] = snap_size_bytes
    print(f"    Payload Size:                 {snap_size_bytes} bytes ({snap_size_bytes / 1024.0:.1f} KB)")

    # 2. Cached Context Snapshot (100 iterations)
    t_cache_start = time.perf_counter()
    for _ in range(100):
        _ = engine.get_snapshot()
    t_cache_ms = ((time.perf_counter() - t_cache_start) / 100.0) * 1000.0
    results["cached_context_ms"] = round(t_cache_ms, 4)
    print(f"[*] Cached Context Retrieval:     {t_cache_ms:.4f} ms per call")

    # 3. Memory SQLite Persistence (Write + Query)
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "bench_memory.db")
    memory = SessionMemory(session_id="bench_session", db_path=db_path)

    # 3a. Write latency (50 tasks)
    t_write_start = time.perf_counter()
    for i in range(50):
        memory.record_task(
            task_id=f"t_{i}",
            tool="raster.inspect",
            status="SUCCESS",
            duration_sec=0.01,
            outputs={"valid": True}
        )
    t_write_ms = ((time.perf_counter() - t_write_start) / 50.0) * 1000.0
    results["sqlite_write_ms"] = round(t_write_ms, 3)
    print(f"[*] SQLite Task Write:            {t_write_ms:.3f} ms per task")

    # 3b. Query latency (50 queries)
    t_query_start = time.perf_counter()
    for _ in range(50):
        _ = memory.get_recent_runs(limit=10)
    t_query_ms = ((time.perf_counter() - t_query_start) / 50.0) * 1000.0
    results["sqlite_query_ms"] = round(t_query_ms, 3)
    print(f"[*] SQLite Recent Runs Query:     {t_query_ms:.3f} ms per query")

    # 4. Combined Agent Context Package
    t_pkg_start = time.perf_counter()
    pkg = get_agent_context_package(task_type="segmentation", session_id="bench_session")
    t_pkg_ms = (time.perf_counter() - t_pkg_start) * 1000.0
    results["agent_context_package_ms"] = round(t_pkg_ms, 2)
    print(f"[*] Agent Context Package:        {t_pkg_ms:.2f} ms")

    memory.close()
    try:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
    except Exception:
        pass

    print("=" * 65)
    print("  ALL BENCHMARKS COMPLETED SUCCESSFULLY")
    print("=" * 65)
    return results


if __name__ == "__main__":
    run_benchmarks()
