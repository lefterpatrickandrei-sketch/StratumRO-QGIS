import os
import sys
import time

sys.path.insert(0, os.path.abspath("."))

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import geopandas as gpd
from stratum_ro.cadastral_product import CadastralProductGenerator
from stratum_ro.pug_product import PugProductGenerator

print("=================================================================")
print("  STRATUM-RO: GENERARE DUBLA PRODUSE ADMINISTRATIVE SPECIALIZATE ")
print("  1. CADASTRU (Standard ANCPI / Carte Funciara)                  ")
print("  2. URBANISM & PUG (Plan Urbanistic General & Spatii Verzi)     ")
print("=================================================================\n")

# Citim datele de fuziune hibrida deja procesate
source_gpkg = r"workspace\output\cladiri_stereo70.gpkg"
if not os.path.exists(source_gpkg):
    print(f"Eroare: Fisierul sursa {source_gpkg} lipseste.")
    sys.exit(1)

print(f"1. Incarcare geometrii validate din: {source_gpkg}")
gdf_bldg = gpd.read_file(source_gpkg, layer="CLADIRI_HIBRID")
gdf_anexe = gpd.read_file(source_gpkg, layer="ANEXE_GOSPODARESTI")
gdf_trees = gpd.read_file(source_gpkg, layer="ARBORI")
gdf_poles = gpd.read_file(source_gpkg, layer="STALPI_TURNURI")

# Convertim in formate de dictionar pentru generatoare
raw_bldgs = []
for _, r in gdf_bldg.iterrows():
    raw_bldgs.append({
        "id": int(r.get("id", 0)),
        "geometry": r.geometry,
        "inaltime_med_m": float(r.get("inaltime_med_m", 4.0)),
        "inaltime_max_m": float(r.get("inaltime_max_m", 5.5)),
        "sam2_score": float(r.get("sam2_score", 0.7)),
        "status": str(r.get("validare", "CONFIRMAT_HIBRID")),
        "area_m2": float(r.get("area_m2", r.geometry.area))
    })

raw_anexe = []
for _, r in gdf_anexe.iterrows():
    raw_anexe.append({
        "id": int(r.get("id", 0)),
        "geometry": r.geometry,
        "area_m2": float(r.geometry.area)
    })

tree_pts = []
for _, r in gdf_trees.iterrows():
    tree_pts.append({
        "x": float(r.geometry.x),
        "y": float(r.geometry.y),
        "height_m": float(r.get("height_m", 4.0))
    })

pole_pts = []
for _, r in gdf_poles.iterrows():
    pole_pts.append({
        "x": float(r.geometry.x),
        "y": float(r.geometry.y),
        "height_m": float(r.get("height_m", 12.0)),
        "type": str(r.get("type", "Stalp"))
    })

# =================================================================
# GENERARE PRODUSUL 1: CADASTRU (ANCPI)
# =================================================================
print("\n--- GENERARE PRODUSUL 1: CADASTRU (ANCPI) ---")
cad_gen = CadastralProductGenerator(crs="EPSG:3844")
cad_gpkg = r"workspace\output\cadastru_ancpi.gpkg"
cad_dxf = r"workspace\output\cadastru_ancpi.dxf"

t0 = time.time()
res_cad = cad_gen.generate_cadastral_package(
    raw_buildings=raw_bldgs,
    raw_outbuildings=raw_anexe,
    tree_points=tree_pts,
    pole_points=pole_pts,
    output_gpkg=cad_gpkg,
    output_dxf=cad_dxf
)
print(f"   [OK] Finalizat in {time.time()-t0:.2f}s:")
print(f"        - Clădiri principale (C1): {res_cad['count_main']}")
print(f"        - Anexe gospodărești (C2): {res_cad['count_anexe']}")
print(f"        - Arbori aliniament (în afara clădirilor): {res_cad['count_trees']}")
print(f"        - Copaci eliminați de pe acoperișuri: {res_cad['eliminated_trees_on_roofs']}")
print(f"        - Fișier GeoPackage: {res_cad['gpkg_path']}")
print(f"        - Fișier AutoCAD DXF: {res_cad['dxf_path']}")

# =================================================================
# GENERARE PRODUSUL 2: URBANISM & PUG
# =================================================================
print("\n--- GENERARE PRODUSUL 2: URBANISM & PUG ---")
pug_gen = PugProductGenerator(crs="EPSG:3844")
pug_gpkg = r"workspace\output\urbanism_pug.gpkg"
pug_report = r"workspace\output\raport_indicatori_pug.json"

t1 = time.time()
res_pug = pug_gen.generate_pug_package(
    raw_buildings=raw_bldgs,
    raw_outbuildings=raw_anexe,
    tree_points=tree_pts,
    pole_points=pole_pts,
    output_gpkg=pug_gpkg,
    output_report_json=pug_report
)
print(f"   [OK] Finalizat in {time.time()-t1:.2f}s:")
print(f"        - Clădiri volumetrice LOD1 (cu H_cornisa, H_coama, Sd): {res_pug['buildings_lod1']}")
print(f"        - Anexe volumetrice: {res_pug['anexe_count']}")
print(f"        - Registru Spații Verzi (Arbori pe Sol): {res_pug['trees_count']}")
print(f"        - Celule analiză UTR (POT & CUT calculate): {res_pug['utr_cells']}")
print(f"        - POT mediu estimat: {res_pug['mean_pot']:.1f}%")
print(f"        - CUT mediu estimat: {res_pug['mean_cut']:.2f}")
print(f"        - Fișier GeoPackage Urbanism: {res_pug['gpkg_path']}")
print(f"        - Raport JSON Indicatori: {res_pug['report_path']}")

print("\n=================================================================")
print("  PROCESARE DUBLA FINALIZATA CU SUCCES!                          ")
print("=================================================================")
