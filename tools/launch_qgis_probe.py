import subprocess
import os
import sys

qgis_exe = r"C:\Program Files\QGIS 3.40.0\bin\qgis-bin.exe"
project = os.path.abspath(r"workspace\output\StratumRO_Rezultate.qgz")
probe = os.path.abspath(r"tools\qt_ui_probe.py")

cmd = [qgis_exe, "--project", project, "--code", probe]
proc = subprocess.Popen(cmd)
print(f"LAUNCHED_PID: {proc.pid}")
