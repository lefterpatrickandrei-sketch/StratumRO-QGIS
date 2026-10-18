# -*- coding: utf-8 -*-
"""
StratumRO Master GeoPackage Consolidation Engine (PyOGRIO / GeoPandas)
====================================================================
Consolidates all official statutory layers, PUG zoning reference layers,
and national transport corridors into a single, high-performance SQLite
GeoPackage: projects/UAT_Iepuresti/UAT_Iepuresti_PUG_Master.gpkg.

All layers are unified into EPSG:3844 (Stereo 70) with 100% attribute fidelity.
"""

import sys
import os
import geopandas as gpd
import pyogrio

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)

OUT_DIR = r"c:\Users\lefpa\Downloads\QGIS-AI\projects\UAT_Iepuresti"
os.makedirs(OUT_DIR, exist_ok=True)
OUT_GPKG = os.path.join(OUT_DIR, "UAT_Iepuresti_PUG_Master.gpkg")

if os.path.exists(OUT_GPKG):
    try:
        os.remove(OUT_GPKG)
        print(f"[CLEAN] Sters GPKG anterior: {OUT_GPKG}")
    except Exception as e:
        print(f"[WARN] Eroare la stergere GPKG anterior: {e}")

TARGET_CRS = "EPSG:3844"

# Table definitions: (Source path, Source layer, Target table name, Description, Category)
LAYERS_TO_CONSOLIDATE = [
    # --- 01. OFICIAL STAT (UAT IEPURESTI) ---
    (
        r"C:\Users\lefpa\Downloads\QGIS-AI\projects\UAT_Iepuresti\output\UAT_Iepuresti_Oficial.gpkg",
        "IEP_00_limita_UAT_ANCPI_oficial",
        "01_oficial_limita_uat_ancpi",
        "Limita oficiala UAT Iepuresti (ANCPI, Legea 7/1996)"
    ),
    (
        r"C:\Users\lefpa\Downloads\QGIS-AI\projects\UAT_Iepuresti\output\UAT_Iepuresti_Oficial.gpkg",
        "IEP_06_apia_blocuri_fizice_2025",
        "02_oficial_parcele_agricole_apia_2025",
        "Parcele de referinta blocuri fizice 2025 (APIA / MADR)"
    ),
    (
        r"C:\Users\lefpa\Downloads\QGIS-AI\projects\UAT_Iepuresti\output\UAT_Iepuresti_Oficial.gpkg",
        "IEP_01_situri_arheologice_RAN",
        "03_oficial_situri_arheologice_ran_cimec",
        "Situri arheologice clasate RAN (cIMeC / INP, OG 43/2000)"
    ),
    (
        r"C:\Users\lefpa\Downloads\QGIS-AI\projects\UAT_Iepuresti\output\UAT_Iepuresti_Oficial.gpkg",
        "IEP_02_natura2000_eea",
        "04_oficial_natura2000_protectie_eea",
        "Arii naturale protejate Natura 2000 (EEA / ANANP)"
    ),
    (
        r"C:\Users\lefpa\Downloads\QGIS-AI\projects\UAT_Iepuresti\output\UAT_Iepuresti_Oficial.gpkg",
        "IEP_04_rowater_cursuri_apa",
        "05_oficial_hidrografie_neajlov_anar",
        "Cursuri de apa cadastrate Neajlov (ANAR ROWATER)"
    ),
    
    # --- 02. MODELE URBANISM & PUG (DE REFERINTA - SCARI CONFORM GHID GP 038/99) ---
    (
        r"C:\Users\lefpa\Downloads\QGIS-AI\projects\UAT_Iepuresti\output\UAT_Iepuresti_Oficial.gpkg",
        "IEP_constructii_cadastru",
        "10_referinta_cladiri_topolt_1cc_scara_1000",
        "Cladiri existente vectorizate TopoLT 1CC (de referinta | PUG 1:1.000)"
    ),
    (
        r"C:\Users\lefpa\Downloads\QGIS-AI\projects\UAT_Iepuresti\output\UAT_Iepuresti_Master.gpkg",
        "zona_curti_constructii",
        "11_referinta_intravilan_curti_constructii_cc_scara_1000",
        "Zonificare UTR Curti-Constructii Intravilan CC (de referinta | PUG 1:1.000)"
    ),
    (
        r"C:\Users\lefpa\Downloads\QGIS-AI\projects\UAT_Iepuresti\output\UAT_Iepuresti_Master.gpkg",
        "drumuri_strazi",
        "12_referinta_strazi_locale_st_scara_1000",
        "Trame stradale locale intravilan ST (de referinta | PUG 1:1.000)"
    ),
    (
        r"C:\Users\lefpa\Downloads\QGIS-AI\projects\UAT_Iepuresti\output\UAT_Iepuresti_Oficial.gpkg",
        "IEP_03_renns_nomenclator_strazi",
        "13_referinta_renns_adrese_nomenclator_scara_1000",
        "Nomenclator stradal si adrese postale RENNS (de referinta | PUG 1:1.000)"
    ),
    (
        r"C:\Users\lefpa\Downloads\QGIS-AI\projects\UAT_Iepuresti\output\UAT_Iepuresti_Master.gpkg",
        "drumuri_nationale",
        "14_referinta_drumuri_nationale_dn_scara_5000",
        "Drumuri nationale DN extravilan (de referinta | PUG 1:5.000)"
    ),
    (
        r"C:\Users\lefpa\Downloads\QGIS-AI\projects\UAT_Iepuresti\output\UAT_Iepuresti_Master.gpkg",
        "drumuri_judetene",
        "15_referinta_drumuri_judetene_dj_scara_5000",
        "Drumuri judetene DJ extravilan (de referinta | PUG 1:5.000)"
    ),
    (
        r"C:\Users\lefpa\Downloads\QGIS-AI\projects\UAT_Iepuresti\output\UAT_Iepuresti_Master.gpkg",
        "drumuri_comunale",
        "16_referinta_drumuri_comunale_dc_scara_5000",
        "Drumuri comunale DC extravilan (de referinta | PUG 1:5.000)"
    ),
    (
        r"C:\Users\lefpa\Downloads\QGIS-AI\projects\UAT_Iepuresti\output\UAT_Iepuresti_Master.gpkg",
        "zona_forestiera",
        "17_referinta_fond_forestier_vpd_scara_5000",
        "Fond forestier / paduri V_PD (de referinta | PUG 1:5.000)"
    ),
    (
        r"C:\Users\lefpa\Downloads\QGIS-AI\projects\UAT_Iepuresti\output\UAT_Iepuresti_Master.gpkg",
        "zona_agricola_arabil",
        "18_referinta_terenuri_arabile_aar_scara_5000",
        "Terenuri agricole arabile A_Ar (de referinta | PUG 1:5.000)"
    ),
    (
        r"C:\Users\lefpa\Downloads\QGIS-AI\projects\UAT_Iepuresti\output\UAT_Iepuresti_Master.gpkg",
        "zona_pasuni_fanete",
        "19_referinta_pasuni_fanete_ap_scara_5000",
        "Pasuni si fanete A_P (de referinta | PUG 1:5.000)"
    ),
    (
        r"C:\Users\lefpa\Downloads\QGIS-AI\projects\UAT_Iepuresti\output\UAT_Iepuresti_Master.gpkg",
        "zona_ape",
        "20_referinta_zone_umede_ape_zha_scara_5000",
        "Zone umede si ape ZHA (de referinta | PUG 1:5.000)"
    ),
    (
        r"C:\Users\lefpa\Downloads\QGIS-AI\projects\UAT_Iepuresti\output\UAT_Iepuresti_Oficial.gpkg",
        "IEP_04_rowater_zona_inundabila_T100",
        "21_referinta_banda_inundabila_t100_scara_5000",
        "Banda inundabila T100 modelare (de referinta | PUG 1:5.000)"
    ),

    # --- 03. TRANSPORT NATIONAL (REPROIECTAT STEREO 70) ---
    (
        r"c:\Users\lefpa\Downloads\QGIS-AI\national_server\08_TRANSPORT_CNAIR_CFR\MajorRoads_Romania_CNAIR_MMAP.gpkg",
        None,
        "30_oficial_cnair_drumuri_majore_national",
        "CNAIR / MMAP Drumuri Majore Nationale (reproiectat Stereo 70)"
    ),
    (
        r"c:\Users\lefpa\Downloads\QGIS-AI\national_server\08_TRANSPORT_CNAIR_CFR\MajorRailways_Romania_CFR_MMAP.gpkg",
        None,
        "31_oficial_cfr_cai_ferate_national",
        "CFR / MMAP Cai Ferate Nationale (reproiectat Stereo 70)"
    )
]

def main():
    print("===================================================================")
    print("   CONSOLIDARE MASTER GEOPACKAGE (GPKG) — UAT IEPUREȘTI")
    print(f"   Destinație: {OUT_GPKG}")
    print("===================================================================\n")

    first = True
    total_features = 0
    consolidated_layers = 0

    for src_path, src_layer, target_table, desc in LAYERS_TO_CONSOLIDATE:
        if not os.path.exists(src_path):
            print(f"  [SKIP] Sursă inexistentă: {src_path}")
            continue

        try:
            if src_layer:
                gdf = gpd.read_file(src_path, layer=src_layer)
            else:
                gdf = gpd.read_file(src_path)

            if gdf.empty:
                print(f"  [WARN] Strat gol ({target_table})")
                continue

            # Reproiectare la Stereo 70 (EPSG:3844) dacă este necesar
            if gdf.crs is None:
                gdf.set_crs(TARGET_CRS, inplace=True)
            elif gdf.crs.to_string() != TARGET_CRS:
                print(f"    [REPROJECT] {target_table} din {gdf.crs.to_string()} -> {TARGET_CRS}")
                gdf = gdf.to_crs(TARGET_CRS)

            # Salvare în GeoPackage
            mode = "w" if first else "a"
            gdf.to_file(OUT_GPKG, layer=target_table, driver="GPKG", mode=mode)
            first = False

            f_count = len(gdf)
            total_features += f_count
            consolidated_layers += 1
            print(f"  [OK] {target_table} -> {f_count} entități ({desc})")

        except Exception as e:
            print(f"  [FAIL] Eroare la procesarea {target_table}: {e}")

    file_size_mb = os.path.getsize(OUT_GPKG) / (1024 * 1024) if os.path.exists(OUT_GPKG) else 0
    print("\n===================================================================")
    print(f" [SUCCESS] Master GeoPackage creat cu succes!")
    print(f"  Locație fișier: {OUT_GPKG}")
    print(f"  Dimensiune disc: {file_size_mb:.2f} MB")
    print(f"  Total tabele vectoriale: {consolidated_layers}")
    print(f"  Total entități spațiale: {total_features:,}")
    print(f"  Sistem de referință spațială: {TARGET_CRS} (Stereo 70)")
    print("===================================================================")

if __name__ == "__main__":
    main()
