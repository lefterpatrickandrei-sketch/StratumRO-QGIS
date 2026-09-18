# -*- coding: utf-8 -*-
import subprocess
import os
import sys

qgis_exe = r"C:\Program Files\QGIS 3.40.0\bin\qgis-bin.exe"
code_script = os.path.abspath(r"tools\open_stratum_ro_real.py")

cmd = [qgis_exe, "--noplugins", "--nologo", "--code", code_script]
print(f"Starting QGIS interactive session: {' '.join(cmd)}", flush=True)

proc = subprocess.Popen(cmd)
print(f"QGIS_PID: {proc.pid}", flush=True)

# Wait for QGIS to be closed by the user in GUI
proc.wait()
print(f"QGIS closed with code {proc.returncode}")
