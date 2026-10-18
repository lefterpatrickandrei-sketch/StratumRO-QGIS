# -*- coding: utf-8 -*-
"""
StratumRO Headless CAD Compiler Engine
=======================================
Executes AutoCAD operations headlessly via Autodesk Core Console (accoreconsole.exe).
Eliminates out-of-process COM locks (0x8001010A), STA busy freezes, and GUI disruptions.

Supports:
- Headless DXF -> DWG conversion
- Script (.scr) batch execution
- TopoLT CAD layer generation and verification
- Off-GUI background processing with millisecond timing
"""

import os
import sys
import time
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Tuple, List

AUTOCAD_CANDIDATE_PATHS = [
    r"C:\Program Files\Autodesk\AutoCAD 2027\accoreconsole.exe",
    r"C:\Program Files\Autodesk\AutoCAD 2025\accoreconsole.exe",
    r"C:\Program Files\Autodesk\AutoCAD 2026\accoreconsole.exe",
    r"C:\Program Files\Autodesk\AutoCAD 2024\accoreconsole.exe",
]


class HeadlessCadCompiler:
    """
    Automates AutoCAD and Civil 3D headlessly through accoreconsole.exe.
    """

    def __init__(self, executable_path: Optional[str] = None):
        self.exe_path = executable_path or self._find_accoreconsole()
        if not self.exe_path or not os.path.exists(self.exe_path):
            raise FileNotFoundError(
                f"accoreconsole.exe could not be found. Checked candidates: {AUTOCAD_CANDIDATE_PATHS}"
            )

    @staticmethod
    def _find_accoreconsole() -> Optional[str]:
        # 1. Environment override
        env_path = os.environ.get("ACCORECONSOLE_PATH")
        if env_path and os.path.exists(env_path):
            return env_path

        # 2. Candidate paths
        for cand in AUTOCAD_CANDIDATE_PATHS:
            if os.path.exists(cand):
                return cand
        return None

    def execute_script(
        self,
        script_path: str,
        base_drawing: Optional[str] = None,
        timeout_sec: int = 60
    ) -> Tuple[bool, str, float]:
        """
        Executes a CAD .scr script file headlessly in accoreconsole.exe.

        Args:
            script_path: Path to the .scr command script.
            base_drawing: Optional base .dwg or .dxf drawing to load into session.
            timeout_sec: Maximum execution timeout in seconds.

        Returns:
            Tuple of (success: bool, stdout_output: str, duration_ms: float)
        """
        if not os.path.exists(script_path):
            return False, f"Script file not found: {script_path}", 0.0

        cmd = [self.exe_path, "/s", os.path.abspath(script_path), "/l", "en-US"]
        if base_drawing:
            if not os.path.exists(base_drawing):
                return False, f"Base drawing not found: {base_drawing}", 0.0
            cmd.extend(["/i", os.path.abspath(base_drawing)])

        t_start = time.perf_counter()
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout_sec
            )
            t_elapsed_ms = (time.perf_counter() - t_start) * 1000.0
            output = proc.stdout + "\n" + proc.stderr
            return (proc.returncode == 0), output, t_elapsed_ms
        except subprocess.TimeoutExpired:
            t_elapsed_ms = (time.perf_counter() - t_start) * 1000.0
            return False, f"Execution timed out after {timeout_sec}s", t_elapsed_ms
        except Exception as ex:
            t_elapsed_ms = (time.perf_counter() - t_start) * 1000.0
            return False, f"Subprocess invocation error: {ex}", t_elapsed_ms

    def compile_dxf_to_dwg(
        self,
        dxf_path: str,
        output_dwg_path: str,
        timeout_sec: int = 60
    ) -> Tuple[bool, str, float]:
        """
        Headlessly opens a DXF file and saves it out as a native DWG drawing file.
        """
        dxf_abs = os.path.abspath(dxf_path)
        dwg_abs = os.path.abspath(output_dwg_path)
        os.makedirs(os.path.dirname(dwg_abs), exist_ok=True)

        if os.path.exists(dwg_abs):
            try:
                os.remove(dwg_abs)
            except OSError as ex:
                return False, f"Target DWG file is locked: {ex}", 0.0

        # Script commands for DXFIN and SAVEAS DWG
        scr_content = f"""DXFIN
"{dxf_abs}"
ZOOM
E
SAVEAS
2018
"{dwg_abs}"
QUIT
Y
"""
        with tempfile.NamedTemporaryFile("w", suffix=".scr", delete=False, encoding="utf-8") as f_scr:
            f_scr.write(scr_content)
            temp_scr_path = f_scr.name

        try:
            success, log, elapsed_ms = self.execute_script(temp_scr_path, timeout_sec=timeout_sec)
            dwg_created = os.path.exists(dwg_abs) and os.path.getsize(dwg_abs) > 0
            if success and not dwg_created:
                # Some accoreconsole versions require separate save command syntax
                return False, f"accoreconsole executed but target DWG was not written. Log: {log[:500]}", elapsed_ms
            return (success and dwg_created), log, elapsed_ms
        finally:
            if os.path.exists(temp_scr_path):
                try:
                    os.remove(temp_scr_path)
                except Exception:
                    pass


def main():
    import argparse
    parser = argparse.ArgumentParser(description="StratumRO Headless CAD Compiler Engine")
    parser.add_argument("--script", help="Path to .scr script to execute")
    parser.add_argument("--dwg", help="Base DWG drawing path")
    parser.add_argument("--dxf", help="Source DXF to compile to DWG")
    parser.add_argument("--out-dwg", help="Destination DWG path")
    parser.add_argument("--probe", action="store_true", help="Probe accoreconsole installation")

    args = parser.parse_args()

    try:
        compiler = HeadlessCadCompiler()
        print(f"[FOUND] accoreconsole.exe: {compiler.exe_path}")
    except Exception as ex:
        print(f"[ERROR] {ex}")
        sys.exit(1)

    if args.probe:
        print("[OK] Headless CAD engine is available and ready.")
        sys.exit(0)

    if args.dxf and args.out_dwg:
        print(f"Compiling {args.dxf} -> {args.out_dwg} headlessly...")
        ok, log, ms = compiler.compile_dxf_to_dwg(args.dxf, args.out_dwg)
        print(f"Result: success={ok}, elapsed={ms:.1f}ms")
        if not ok:
            print("Log:\n", log)
        sys.exit(0 if ok else 1)

    if args.script:
        print(f"Executing script {args.script}...")
        ok, log, ms = compiler.execute_script(args.script, base_drawing=args.dwg)
        print(f"Result: success={ok}, elapsed={ms:.1f}ms")
        if not ok:
            print("Log:\n", log)
        sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
