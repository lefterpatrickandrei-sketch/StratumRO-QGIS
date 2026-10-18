# -*- coding: utf-8 -*-
import os
import sys
import glob
from pathlib import Path
import winreg

def check_dirs():
    print("=== CHECKING PROJ & GRID DIRECTORIES ===")
    localappdata = os.environ.get("LOCALAPPDATA", "")
    appdata = os.environ.get("APPDATA", "")
    candidates = [
        r"C:\Program Files\QGIS 3.40.0\share\proj",
        os.path.join(localappdata, "proj"),
        os.path.join(appdata, "QGIS", "QGIS3", "profiles", "default"),
        r"C:\OSGeo4W\share\proj",
        r"C:\ProgramData\PROJ",
        r"C:\PROJ",
        r"C:\TransDATRO",
        r"C:\TransDAT",
        r"C:\ANCPI"
    ]
    for c in candidates:
        if os.path.exists(c):
            print(f"[EXISTS] {c}")
            # check for gsb, tif, or romania grids
            for root, dirs, files in os.walk(c):
                for f in files:
                    fl = f.lower()
                    if fl.endswith('.gsb') or 'etrs' in fl or 'stereo' in fl or 'transdat' in fl or fl.startswith('ro_'):
                        print(f"   -> Found file: {os.path.join(root, f)}")
        else:
            print(f"[NOT FOUND] {c}")

def check_registry():
    print("\n=== CHECKING WINDOWS REGISTRY FOR TRANSDAT / ANCPI ===")
    reg_roots = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Uninstall")
    ]
    found = False
    for root_key, subkey in reg_roots:
        try:
            with winreg.OpenKey(root_key, subkey) as k:
                num_subkeys, _, _ = winreg.QueryInfoKey(k)
                for i in range(num_subkeys):
                    try:
                        app_subname = winreg.EnumKey(k, i)
                        with winreg.OpenKey(k, app_subname) as app_k:
                            try:
                                disp_name, _ = winreg.QueryValueEx(app_k, "DisplayName")
                                if any(x in disp_name.lower() for x in ["transdat", "ancpi", "stereo"]):
                                    found = True
                                    try:
                                        inst_loc, _ = winreg.QueryValueEx(app_k, "InstallLocation")
                                    except:
                                        inst_loc = "N/A"
                                    print(f"   [REGISTRY MATCH] {disp_name} | Location: {inst_loc}")
                            except:
                                pass
                    except:
                        pass
        except Exception as e:
            pass
    if not found:
        print("   No TransDATRO or ANCPI registration found in standard uninstall keys.")

if __name__ == "__main__":
    check_dirs()
    check_registry()
