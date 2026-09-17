# -*- coding: utf-8 -*-
"""
StratumRO — Desktop Operator Module.
Controls, monitors, and captures real desktop operations for QGIS 3.40 on Windows.

Features:
- Rigorous capability check (REAL_DESKTOP vs PYQGIS_ONLY)
- Windows UI & Desktop switching (Win32 OpenDesktopW / SetThreadDesktop)
- Live QGIS process and top-level window detection
- Foreground window activation and window geometry inspection
- Full-resolution interactive desktop screenshot capture (GDI/ImageGrab)
- Structured operator event logging for provenance audits
"""

import os
import sys
import time
import subprocess
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any, List, Tuple
from PIL import ImageGrab


@dataclass
class OperatorEvent:
    timestamp: float
    stage: str
    action: str
    status: str
    details: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class DesktopOperator:
    """Automates and monitors QGIS 3.40 on the interactive Windows desktop."""

    QGIS_DEFAULT_EXE = r"C:\Program Files\QGIS 3.40.0\bin\qgis-bin.exe"
    QGIS_DEFAULT_BAT = r"C:\Program Files\QGIS 3.40.0\bin\qgis.bat"

    def __init__(self, evidence_dir: Optional[str] = None):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.evidence_dir = evidence_dir or os.path.join(base_dir, "workspace", "e2e", "evidence")
        os.makedirs(self.evidence_dir, exist_ok=True)
        self.events: List[OperatorEvent] = []
        self.capability = self.check_desktop_capability()
        self.mode = "REAL_DESKTOP" if self.capability.get("available") else "PYQGIS_ONLY"

    def log_event(self, stage: str, action: str, status: str, **kwargs) -> OperatorEvent:
        event = OperatorEvent(
            timestamp=time.time(),
            stage=stage,
            action=action,
            status=status,
            details=kwargs
        )
        self.events.append(event)
        return event

    def check_desktop_capability(self) -> Dict[str, Any]:
        """
        Verifies whether real desktop interaction & screenshot capture are available.
        Does not fake success.
        """
        if sys.platform != "win32":
            return {
                "available": False,
                "mode": "PYQGIS_ONLY",
                "reason": f"Platform is {sys.platform}, not Windows win32"
            }

        try:
            import ctypes
            user32 = ctypes.windll.user32
            # Check if OpenDesktopW('default') succeeds
            h_def = user32.OpenDesktopW("default", 0, False, 0x01FF)
            if not h_def:
                return {
                    "available": False,
                    "mode": "PYQGIS_ONLY",
                    "reason": "OpenDesktopW('default') failed to acquire handle"
                }

            ok = user32.SetThreadDesktop(h_def)
            if not ok:
                return {
                    "available": False,
                    "mode": "PYQGIS_ONLY",
                    "reason": "SetThreadDesktop(h_def) failed"
                }

            # Test actual screenshot capture
            test_img = ImageGrab.grab()
            if test_img is None or test_img.size[0] < 100 or test_img.size[1] < 100:
                return {
                    "available": False,
                    "mode": "PYQGIS_ONLY",
                    "reason": "ImageGrab returned empty/invalid image"
                }

            return {
                "available": True,
                "mode": "REAL_DESKTOP",
                "screen_size": list(test_img.size),
                "details": "Win32 Interactive Desktop switching and GDI capture verified"
            }
        except Exception as e:
            return {
                "available": False,
                "mode": "PYQGIS_ONLY",
                "reason": f"Desktop capability check exception: {str(e)}"
            }

    def attach_thread_desktop(self) -> bool:
        """Attaches current thread to user's interactive desktop 'default'."""
        if sys.platform != "win32":
            return False
        try:
            import ctypes
            user32 = ctypes.windll.user32
            h_def = user32.OpenDesktopW("default", 0, False, 0x01FF)
            if h_def:
                return bool(user32.SetThreadDesktop(h_def))
        except Exception:
            pass
        return False

    def find_qgis_window(self) -> Optional[Dict[str, Any]]:
        """Finds active top-level QGIS window on the interactive desktop."""
        if sys.platform != "win32":
            return None

        self.attach_thread_desktop()
        import ctypes
        user32 = ctypes.windll.user32

        qgis_info = None

        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_size_t, ctypes.c_size_t)

        def enum_windows_callback(hwnd, lparam):
            nonlocal qgis_info
            if user32.IsWindowVisible(hwnd):
                length = user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buff = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buff, length + 1)
                    title = buff.value
                    if "qgis" in title.lower():
                        # Get PID
                        pid = ctypes.c_ulong()
                        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                        qgis_info = {
                            "hwnd": hwnd,
                            "title": title,
                            "pid": pid.value
                        }
                        return False  # Stop enumeration
            return True

        user32.EnumWindows(WNDENUMPROC(enum_windows_callback), 0)
        return qgis_info

    def focus_qgis(self, hwnd: int) -> bool:
        """Brings the QGIS window to foreground."""
        if sys.platform != "win32" or not hwnd:
            return False
        self.attach_thread_desktop()
        import ctypes
        user32 = ctypes.windll.user32
        try:
            user32.ShowWindow(hwnd, 9)  # SW_RESTORE
            user32.SetForegroundWindow(hwnd)
            time.sleep(0.5)
            return True
        except Exception:
            return False

    def launch_qgis(self, project_path: Optional[str] = None, timeout_sec: int = 35) -> Dict[str, Any]:
        """Launches QGIS 3.40 if not already running."""
        existing = self.find_qgis_window()
        if existing:
            self.log_event("init", "find_qgis", "found_existing", **existing)
            self.focus_qgis(existing["hwnd"])
            return {"status": "already_running", "window": existing}

        qgis_bin = self.QGIS_DEFAULT_EXE if os.path.isfile(self.QGIS_DEFAULT_EXE) else self.QGIS_DEFAULT_BAT
        if not os.path.isfile(qgis_bin):
            raise FileNotFoundError(f"QGIS executable not found at {qgis_bin}")

        cmd = [qgis_bin]
        if project_path and os.path.isfile(project_path):
            cmd.append(os.path.abspath(project_path))

        self.log_event("init", "launch_qgis", "launching", command=" ".join(cmd))
        proc = subprocess.Popen(cmd)

        start_t = time.time()
        while time.time() - start_t < timeout_sec:
            time.sleep(2.0)
            w = self.find_qgis_window()
            if w:
                self.focus_qgis(w["hwnd"])
                self.log_event("init", "launch_qgis", "ready", window=w, wait_time_sec=round(time.time() - start_t, 2))
                return {"status": "launched", "pid": proc.pid, "window": w}

        return {"status": "timeout_waiting_for_window", "pid": proc.pid}

    def capture_stage_screenshot(self, stage_name: str) -> str:
        """Captures real full-desktop screenshot and saves as evidence."""
        self.attach_thread_desktop()
        filename = f"{stage_name}_{int(time.time())}.png"
        filepath = os.path.join(self.evidence_dir, filename)

        try:
            img = ImageGrab.grab()
            img.save(filepath, format="PNG")
            self.log_event(stage_name, "capture_screenshot", "success", path=filepath, size=list(img.size))
            return filepath
        except Exception as e:
            self.log_event(stage_name, "capture_screenshot", "failed", error=str(e))
            return ""
