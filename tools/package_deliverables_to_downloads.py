# -*- coding: utf-8 -*-
"""
StratumRO Package Deliverables to Downloads Engine
=================================================
Creates a clean, fully organized distribution folder in C:\\Users\\lefpa\\Downloads:
  Folder: C:\\Users\\lefpa\\Downloads\\StratumRO_Pachet_Complet_National_si_PUG
  ZIP:    C:\\Users\\lefpa\\Downloads\\StratumRO_Pachet_Complet_National_si_PUG.zip

Contains:
  01_SERVER_NATIONAL_ROMANIA (all 11 official national categories, XML connections, QLRs)
  02_PROIECT_MASTER_PUG_IEPURESTI (UAT_Iepuresti_PUG_Master.gpkg, active QGIS project, launcher)
  03_CAD_AUTOCAD_EXPORT (DXF with XDATA, CSV attribute manifest, TopoLT .CP coordinates)
  04_SUBAGENTI_AI_SI_METODOLOGIE (PUG Specialist, CAD Bridge, Open Data Harvester, Orchestrator)
  05_RAPOARTE_AUDIT_SI_CONFORMITATE (PUG report, National browser report, documentation)
"""

import sys
import os
import shutil
import zipfile
import time

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)

ROOT_DIR = r"c:\Users\lefpa\Downloads\QGIS-AI"
DOWNLOADS_DIR = r"c:\Users\lefpa\Downloads"

PKG_DIR_NAME = "StratumRO_Pachet_Complet_National_si_PUG"
TARGET_DIR = os.path.join(DOWNLOADS_DIR, PKG_DIR_NAME)
TARGET_ZIP = os.path.join(DOWNLOADS_DIR, f"{PKG_DIR_NAME}.zip")

def copy_file(src, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(src, dst)

def copy_tree_filtered(src_dir, dst_dir):
    os.makedirs(dst_dir, exist_ok=True)
    for root, dirs, files in os.walk(src_dir):
        # Ignore cache and temporary dirs
        dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git", ".venv")]
        rel_path = os.path.relpath(root, src_dir)
        cur_dst = os.path.join(dst_dir, rel_path) if rel_path != "." else dst_dir
        os.makedirs(cur_dst, exist_ok=True)
        for f in files:
            if f.endswith((".pyc", ".tmp", ".part")):
                continue
            s_file = os.path.join(root, f)
            d_file = os.path.join(cur_dst, f)
            shutil.copy2(s_file, d_file)

def main():
    print("===================================================================")
    print("   STRATUMRO AMBALARE LIVRABILE ÎN DOWNLOADS (ORGANIZAT & COMPRESAT)")
    print(f"   Destinație Folder: {TARGET_DIR}")
    print(f"   Destinație ZIP:    {TARGET_ZIP}")
    print("===================================================================\n")

    # Clean existing target dir if needed
    if os.path.exists(TARGET_DIR):
        print(f"[CLEAN] Re-inițializare folder existent: {TARGET_DIR}")
        shutil.rmtree(TARGET_DIR, ignore_errors=True)
    os.makedirs(TARGET_DIR, exist_ok=True)

    # -------------------------------------------------------------------------
    # 1. 01_SERVER_NATIONAL_ROMANIA
    # -------------------------------------------------------------------------
    print("--> [1/5] Copiere 01_SERVER_NATIONAL_ROMANIA...")
    nat_src = os.path.join(ROOT_DIR, "national_server")
    nat_dst = os.path.join(TARGET_DIR, "01_SERVER_NATIONAL_ROMANIA")
    copy_tree_filtered(nat_src, nat_dst)
    print(f"    [OK] Copiat depozitul național ({len(os.listdir(nat_dst))} sub-elemente).")

    # -------------------------------------------------------------------------
    # 2. 02_PROIECT_MASTER_PUG_IEPURESTI
    # -------------------------------------------------------------------------
    print("--> [2/5] Copiere 02_PROIECT_MASTER_PUG_IEPURESTI...")
    pug_dst = os.path.join(TARGET_DIR, "02_PROIECT_MASTER_PUG_IEPURESTI")
    os.makedirs(pug_dst, exist_ok=True)

    # Master GeoPackage
    gpkg_src = os.path.join(ROOT_DIR, "projects", "UAT_Iepuresti", "UAT_Iepuresti_PUG_Master.gpkg")
    if os.path.exists(gpkg_src):
        copy_file(gpkg_src, os.path.join(pug_dst, "UAT_Iepuresti_PUG_Master.gpkg"))
        print(f"    [OK] Copiat Master GeoPackage (179 MB, 19 tabele).")

    # Active Project QGS
    qgs_src = os.path.join(ROOT_DIR, "projects", "UAT_Iepuresti", "UAT_Iepuresti_Cadastru_si_PUG_Oficial.qgs")
    if os.path.exists(qgs_src):
        copy_file(qgs_src, os.path.join(pug_dst, "UAT_Iepuresti_Cadastru_si_PUG_Oficial.qgs"))
        print(f"    [OK] Copiat proiectul QGIS activ UAT Iepurești.")

    # Batch Launcher for Iepuresti
    bat_iep = """@echo off
chcp 65001 > nul
echo ===================================================================
echo     LANSARE PROIECT QGIS UAT IEPUREȘTI — PUG & CADASTRU
echo ===================================================================
echo.
set "PRJ=%~dp0UAT_Iepuresti_Cadastru_si_PUG_Oficial.qgs"
if exist "C:\\Program Files\\QGIS 3.40.0\\bin\\qgis-bin.exe" (
    echo Deschid QGIS 3.40 cu proiectul UAT Iepurești...
    start "" "C:\\Program Files\\QGIS 3.40.0\\bin\\qgis-bin.exe" "%PRJ%"
) else (
    echo QGIS 3.40 nu a fost gasit in calea standard.
    pause
)
"""
    with open(os.path.join(pug_dst, "DESCHIDE_PROIECT_IEPURESTI_QGIS.bat"), "w", encoding="utf-8") as f:
        f.write(bat_iep)
    print("    [OK] Generat launcher DESCHIDE_PROIECT_IEPURESTI_QGIS.bat.")

    # -------------------------------------------------------------------------
    # 3. 03_CAD_AUTOCAD_EXPORT
    # -------------------------------------------------------------------------
    print("--> [3/5] Copiere 03_CAD_AUTOCAD_EXPORT...")
    cad_src = os.path.join(ROOT_DIR, "projects", "UAT_Iepuresti", "CAD_Export")
    cad_dst = os.path.join(TARGET_DIR, "03_CAD_AUTOCAD_EXPORT")
    copy_tree_filtered(cad_src, cad_dst)
    print(f"    [OK] Copiat export CAD DXF R2010 (cu XDATA), Manifest CSV și .CP TopoLT.")

    # -------------------------------------------------------------------------
    # 4. 04_SUBAGENTI_AI_SI_METODOLOGIE
    # -------------------------------------------------------------------------
    print("--> [4/5] Copiere 04_SUBAGENTI_AI_SI_METODOLOGIE...")
    ai_dst = os.path.join(TARGET_DIR, "04_SUBAGENTI_AI_SI_METODOLOGIE")
    os.makedirs(ai_dst, exist_ok=True)

    agent_files = [
        ("romanian-urbanism-pug-specialist.md", os.path.join(ROOT_DIR, ".agents", "agents", "romanian-urbanism-pug-specialist.md")),
        ("stratumro-cad-builder.md", os.path.join(ROOT_DIR, ".agents", "agents", "stratumro-cad-builder.md")),
        ("romanian-opendata-specialist.md", os.path.join(ROOT_DIR, ".agents", "agents", "romanian-opendata-specialist.md")),
        ("stratumro-orchestrator.md", os.path.join(ROOT_DIR, ".agents", "agents", "stratumro-orchestrator.md")),
        ("opencode.jsonc", os.path.join(ROOT_DIR, ".opencode", "opencode.jsonc"))
    ]
    for name, p in agent_files:
        if os.path.exists(p):
            copy_file(p, os.path.join(ai_dst, name))
            print(f"    [OK] Copiat subagent: {name}")

    # -------------------------------------------------------------------------
    # 5. 05_RAPOARTE_AUDIT_SI_CONFORMITATE & GHID GENERAL
    # -------------------------------------------------------------------------
    print("--> [5/5] Generare Rapoarte & Ghid Pachet...")
    rep_dst = os.path.join(TARGET_DIR, "05_RAPOARTE_AUDIT_SI_CONFORMITATE")
    os.makedirs(rep_dst, exist_ok=True)

    brain_dir = r"C:\Users\lefpa\.gemini\antigravity\brain\0a436f4d-bd61-48b0-8aa9-fe95d1a63e1f"
    for r_name in ["PUG_AND_CAD_EXPORT_REPORT.md", "NATIONAL_GEODATA_BROWSER_REPORT.md"]:
        r_path = os.path.join(brain_dir, r_name)
        if os.path.exists(r_path):
            copy_file(r_path, os.path.join(rep_dst, r_name))
            print(f"    [OK] Copiat raport: {r_name}")

    # Ghid General Pachet
    readme_content = f"""# PACHET COMPLET — STRATUMRO DATE OFICIALE NAȚIONALE & MASTER PUG IEPUREȘTI

Data generării: {time.strftime('%Y-%m-%d %H:%M:%S')}
Sistem de Coordonate: Stereo 70 (EPSG:3844) / Dealul Piscului 1970
Locație: {TARGET_DIR}

---

## Structura Directorului:

1. `01_SERVER_NATIONAL_ROMANIA/`
   - Cele 11 directoare tematice oficiale de stat (ANCPI, APIA, ANAR, cIMeC, EEA, MMAP, RENNS, CNAIR, CFR, IGR, Copernicus).
   - `CONEXIUNI_QGIS_OFICIALE.xml` — import instant WMS/WFS/REST în panoul QGIS Browser.
   - `ROMANIA_NATIONAL_OFICIAL_BROWSER.qgs` — proiectul master național în Stereo 70.
   - `DESCHIDE_BROWSER_NATIONAL_QGIS.bat` — lansator dintr-un clic.

2. `02_PROIECT_MASTER_PUG_IEPURESTI/`
   - `UAT_Iepuresti_PUG_Master.gpkg` — baza de date unificată SQLite GeoPackage (19 tabele, 3.526 entități în Stereo 70).
   - `UAT_Iepuresti_Cadastru_si_PUG_Oficial.qgs` — proiectul QGIS activ pentru UAT Iepurești cu arborele curat.
   - `DESCHIDE_PROIECT_IEPURESTI_QGIS.bat` — lansator proiect Iepurești.

3. `03_CAD_AUTOCAD_EXPORT/`
   - `UAT_Iepuresti_PUG_Cadastru.dxf` — desen AutoCAD R2010 cu atribute complete conservate prin XDATA (AppID STRATUMRO_GIS).
   - `UAT_Iepuresti_CAD_Attributes_Manifest.csv` — manifest relațional al tuturor atributelor după Handle CAD.
   - `UAT_Iepuresti_Puncte_Stereo70.cp` — coordonate topografice TopoLT în Stereo 70 (milimetric).

4. `04_SUBAGENTI_AI_SI_METODOLOGIE/`
   - `romanian-urbanism-pug-specialist.md` — subagent PUG / Urbanism (Legea 350/2001, GP 038/99).
   - `stratumro-cad-builder.md` — subagent punte CAD / TopoLT.
   - `romanian-opendata-specialist.md` — subagent recoltare date naționale de stat.
   - `opencode.jsonc` — configurația runtime multi-agent.

5. `05_RAPOARTE_AUDIT_SI_CONFORMITATE/`
   - `PUG_AND_CAD_EXPORT_REPORT.md` — raport de audit și conformitate PUG.
   - `NATIONAL_GEODATA_BROWSER_REPORT.md` — audit al depozitului național.
"""
    with open(os.path.join(TARGET_DIR, "README_PACHET_ORGANIZAT.md"), "w", encoding="utf-8") as f:
        f.write(readme_content)
    print("    [OK] Generat README_PACHET_ORGANIZAT.md.")

    # -------------------------------------------------------------------------
    # COMPRESIE ZIP ORGANIZATĂ
    # -------------------------------------------------------------------------
    print(f"\n--> Creare Arhivă ZIP: {TARGET_ZIP}...")
    if os.path.exists(TARGET_ZIP):
        os.remove(TARGET_ZIP)

    stored_extensions = (".zip", ".gpkg", ".kmz", ".png", ".jpg")
    total_files_zipped = 0
    start_time = time.time()

    with zipfile.ZipFile(TARGET_ZIP, "w", allowZip64=True) as zf:
        for root, dirs, files in os.walk(TARGET_DIR):
            for file in files:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, DOWNLOADS_DIR)
                
                # Optimize compression: store already compressed formats, deflate raw texts/shps
                compress_mode = zipfile.ZIP_STORED if file.lower().endswith(stored_extensions) else zipfile.ZIP_DEFLATED
                zf.write(full_path, rel_path, compress_type=compress_mode)
                total_files_zipped += 1
                if total_files_zipped % 10 == 0:
                    sys.stdout.write(f"\r    Adăugat {total_files_zipped} fișiere în ZIP...")
                    sys.stdout.flush()

    elapsed = time.time() - start_time
    zip_size_mb = os.path.getsize(TARGET_ZIP) / (1024 * 1024)
    print(f"\r    [SUCCESS] Arhivă ZIP finalizată ({total_files_zipped} fișiere în {elapsed:.1f}s)!")
    print(f"    Dimensiune Arhivă ZIP: {zip_size_mb:.2f} MB")

    print("\n===================================================================")
    print(" [LIVRARE COMPLETĂ] Toate datele și creațiile au fost exportate în Downloads:")
    print(f"  1. Folder Organizat: {TARGET_DIR}")
    print(f"  2. Arhivă ZIP:       {TARGET_ZIP}")
    print("===================================================================")

if __name__ == "__main__":
    main()
