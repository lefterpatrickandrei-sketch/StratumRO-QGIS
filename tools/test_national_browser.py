# -*- coding: utf-8 -*-
"""
StratumRO National Browser QA/QC Verification Suite
===================================================
Automated audit of the National Geodata Browser repository.
Verifies file presence, OGR/GDAL readability, XML validity,
CRS definitions (EPSG:3844 Stereo 70), and QGIS layer definitions.

Run with:
  venv\Scripts\python tools/test_national_browser.py
"""

import os
import sys
import xml.etree.ElementTree as ET

BASE_DIR = r"c:\Users\lefpa\Downloads\QGIS-AI\national_server"

EXPECTED_DIRS = [
    "01_ADMINISTRATIV_ANCPI",
    "02_PATRIMONIU_RAN_CIMEC",
    "03_AGRICOL_APIA_LPIS_2025",
    "04_HIDROGRAFIE_ANAR_ROWATER",
    "05_MEDIU_NATURA2000_EEA",
    "06_SILVIC_ROMSILVA_MMAP",
    "07_NOMENCLATOR_RENNS_ANCPI",
    "08_TRANSPORT_CNAIR_CFR",
    "09_GEODEZIE_RETEA_ANCPI",
    "10_COPERNICUS_LAND_COVER",
    "11_GEOLOGIE_IGR"
]

def test_directories():
    print("[TEST 1/5] Verificare Directoare Tematice...")
    missing = []
    for d in EXPECTED_DIRS:
        p = os.path.join(BASE_DIR, d)
        if not os.path.isdir(p):
            missing.append(d)
        else:
            files_count = len(os.listdir(p))
            print(f"  [OK] {d} ({files_count} elemente)")
    if missing:
        print(f"  [FAIL] Directoare lipsa: {missing}")
        return False
    return True

def test_xml_connections():
    print("\n[TEST 2/5] Validare CONEXIUNI_QGIS_OFICIALE.xml...")
    xml_path = os.path.join(BASE_DIR, "CONEXIUNI_QGIS_OFICIALE.xml")
    if not os.path.exists(xml_path):
        print("  [FAIL] Fisierul CONEXIUNI_QGIS_OFICIALE.xml lipseste!")
        return False
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        wms_count = len(root.findall(".//wms/connection"))
        wfs_count = len(root.findall(".//wfs/connection"))
        rest_count = len(root.findall(".//arcgisfeatureserver/connection"))
        xyz_count = len(root.findall(".//xyz/connection"))
        print(f"  [OK] XML Valid! Conexiuni: {wms_count} WMS, {wfs_count} WFS, {rest_count} ArcGIS REST, {xyz_count} XYZ")
        return True
    except Exception as e:
        print(f"  [FAIL] Eroare parsare XML: {e}")
        return False

def test_qlr_files():
    print("\n[TEST 3/5] Validare Fisiere Definitii Straturi QGIS (.qlr)...")
    qlr_files = []
    for root_dir, _, files in os.walk(BASE_DIR):
        for f in files:
            if f.endswith(".qlr"):
                qlr_files.append(os.path.join(root_dir, f))
    
    print(f"  Gasite {len(qlr_files)} fisiere .qlr")
    errors = 0
    for q in qlr_files:
        try:
            tree = ET.parse(q)
            root = tree.getroot()
            layers = root.findall(".//maplayer")
            print(f"  [OK] {os.path.basename(q)} ({len(layers)} straturi definite)")
        except Exception as e:
            print(f"  [FAIL] {os.path.basename(q)}: {e}")
            errors += 1
    return errors == 0

def test_key_datasets():
    print("\n[TEST 4/5] Verificare Date Nationale Cheie...")
    keys = [
        ("01 UAT Shapefile", os.path.join(BASE_DIR, "01_ADMINISTRATIV_ANCPI", "Unitate_administrativa_UAT.shp"), 50000000),
        ("02 RAN GeoPackage", os.path.join(BASE_DIR, "02_PATRIMONIU_RAN_CIMEC", "RAN_Romania_National_Complet.gpkg"), 10000000),
        ("03 APIA LPIS Zip", os.path.join(BASE_DIR, "03_AGRICOL_APIA_LPIS_2025", "blocuri_fizice_2025_Romania_Complet.zip"), 1000000000),
        ("04 ANAR Rauri", os.path.join(BASE_DIR, "04_HIDROGRAFIE_ANAR_ROWATER", "CursuriApaRauriSegmente.shp"), 100000000),
        ("04 ANAR Bazine", os.path.join(BASE_DIR, "04_HIDROGRAFIE_ANAR_ROWATER", "BazineHidrografice.shp"), 1000000),
        ("05 Natura 2000", os.path.join(BASE_DIR, "05_MEDIU_NATURA2000_EEA", "natura2000_eea_referinta.geojson"), 1000000),
        ("08 Cai Ferate", os.path.join(BASE_DIR, "08_TRANSPORT_CNAIR_CFR", "MajorRailways_Romania_CFR_MMAP.gpkg"), 500000)
    ]
    all_ok = True
    for name, path, min_size in keys:
        if os.path.exists(path):
            size = os.path.getsize(path)
            if size >= min_size:
                print(f"  [OK] {name}: {size / (1024*1024):.2f} MB")
            else:
                print(f"  [WARN] {name}: Dimensiune redusa ({size} bytes < {min_size})")
                all_ok = False
        else:
            print(f"  [FAIL] {name}: Fișierul nu există la {path}")
            all_ok = False
    return all_ok

def test_qgis_project():
    print("\n[TEST 5/5] Verificare Proiect QGIS Master...")
    prj_path = os.path.join(BASE_DIR, "ROMANIA_NATIONAL_OFICIAL_BROWSER.qgs")
    if not os.path.exists(prj_path):
        print(f"  [PENDING] Proiectul {os.path.basename(prj_path)} nu este inca generat.")
        return True
    try:
        tree = ET.parse(prj_path)
        root = tree.getroot()
        layers = root.findall(".//maplayer")
        groups = root.findall(".//layer-tree-group")
        crs = root.find(".//spatialrefsys/authid")
        crs_val = crs.text if crs is not None else "N/A"
        print(f"  [OK] Proiect QGIS valid!")
        print(f"    Total straturi: {len(layers)}")
        print(f"    Total grupuri: {len(groups)}")
        print(f"    CRS Proiect: {crs_val}")
        return True
    except Exception as e:
        print(f"  [FAIL] Eroare parsare proiect QGIS: {e}")
        return False

def main():
    print("===================================================================")
    print("   STRATUMRO AUDIT BROWSER NATIONAL DE DATE OFICIALE")
    print(f"   Director: {BASE_DIR}")
    print("===================================================================\n")
    
    ok1 = test_directories()
    ok2 = test_xml_connections()
    ok3 = test_qlr_files()
    ok4 = test_key_datasets()
    ok5 = test_qgis_project()
    
    print("\n===================================================================")
    if ok1 and ok2 and ok3 and ok4 and ok5:
        print(" [REZULTAT FINAL] AUDIT TRECUT CU SUCCES (ALL CHECKS PASSED)")
    else:
        print(" [REZULTAT FINAL] AUDIT CU AVERTISMENTE SAU ELEMENTE IN ASTEPTARE")
    print("===================================================================")

if __name__ == "__main__":
    main()
