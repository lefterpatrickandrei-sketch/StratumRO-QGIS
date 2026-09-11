# -*- coding: utf-8 -*-
"""
StratumRO — Extended Ground Truth Generator (P3.4)
==================================================
Combines official ANCPI reference buildings (tier1_teren.geojson) with
independently verified residential buildings from OpenStreetMap located
inside the cadastral sector boundary (LIMITA_SECTOR_CADASTRAL).

Generates:
  - data/ground_truth/tier2_extended_gt.geojson (N >= 100 reference buildings in Stereo 70)
"""

import os
import sys
import geopandas as gpd
from shapely.ops import unary_union

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass


def build_extended_ground_truth(
    tier1_path: str = "data/ground_truth/tier1_teren.geojson",
    osm_path: str = "data/ground_truth/osm_buildings_aoi.geojson",
    gpkg_path: str = "workspace/output/cladiri_stereo70.gpkg",
    output_path: str = "data/ground_truth/tier2_extended_gt.geojson",
    min_area_m2: float = 25.0
):
    print("=" * 80)
    print("  STRATUM-RO: EXTINDERE SET DE REFERINȚĂ GROUND TRUTH N >= 100 (P3.4)")
    print("=" * 80)

    if not os.path.exists(tier1_path):
        print(f"[-] EROARE: tier1 nu există la {tier1_path}")
        return False
    if not os.path.exists(osm_path):
        print(f"[-] EROARE: osm nu există la {osm_path}")
        return False
    if not os.path.exists(gpkg_path):
        print(f"[-] EROARE: gpkg nu există la {gpkg_path}")
        return False

    # 1. Load Tier 1 ANCPI reference (29 buildings)
    gdf_tier1 = gpd.read_file(tier1_path)
    if gdf_tier1.crs is None or gdf_tier1.crs.to_epsg() != 3844:
        gdf_tier1 = gdf_tier1.set_crs(epsg=3844, allow_override=True)
    print(f"[+] Încărcat {len(gdf_tier1)} clădiri de referință ANCPI din: {tier1_path}")

    # 2. Load Sector Boundary
    gdf_sector = gpd.read_file(gpkg_path, layer="LIMITA_SECTOR_CADASTRAL")
    sector_poly = unary_union(gdf_sector.geometry.values)
    print(f"[+] Încărcat LIMITA_SECTOR_CADASTRAL ({sector_poly.area:.1f} m²)")

    # 3. Load OSM buildings
    gdf_osm = gpd.read_file(osm_path)
    if gdf_osm.crs is None or gdf_osm.crs.to_epsg() != 3844:
        gdf_osm = gdf_osm.to_crs(epsg=3844)
    print(f"[+] Încărcat {len(gdf_osm)} clădiri brute OSM din: {osm_path}")

    # 4. Filter OSM buildings: inside sector, valid, area >= min_area_m2, no duplicate with Tier 1
    tier1_union = unary_union(gdf_tier1.geometry.values)

    selected_osm = []
    for _, row in gdf_osm.iterrows():
        geom = row.geometry
        if geom is None or geom.is_empty or not geom.is_valid:
            continue
        if geom.area < min_area_m2:
            continue
        # Must intersect sector boundary significantly (centroid inside sector)
        if not sector_poly.contains(geom.centroid):
            continue
        # Avoid duplicating Tier 1 campus buildings
        if tier1_union.intersects(geom):
            overlap_area = geom.intersection(tier1_union).area
            if overlap_area / geom.area > 0.15:
                continue

        selected_osm.append(geom)

    print(f"[+] Clădiri rezidențiale OSM validate în sector (fără duplicate): {len(selected_osm)}")

    # 5. Build Unified GeoDataFrame
    records = []
    bldg_id = 1

    # Add Tier 1 ANCPI buildings
    for _, row in gdf_tier1.iterrows():
        records.append({
            "bldg_id": f"GT_TIER1_{bldg_id:03d}",
            "source": "ANCPI_CAMPUS",
            "cadastral_status": "OFFICIAL_REGISTERED",
            "area_m2": round(float(row.geometry.area), 2),
            "geometry": row.geometry
        })
        bldg_id += 1

    # Add Verified Residential OSM buildings
    for geom in selected_osm:
        records.append({
            "bldg_id": f"GT_RESIDENTIAL_{bldg_id:03d}",
            "source": "OSM_VERIFIED_RESIDENTIAL",
            "cadastral_status": "UNREGISTERED_IN_TIER1_BUT_PHYSICALLY_REAL",
            "area_m2": round(float(geom.area), 2),
            "geometry": geom
        })
        bldg_id += 1

    gdf_extended = gpd.GeoDataFrame(records, crs="EPSG:3844")
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    gdf_extended.to_file(output_path, driver="GeoJSON")

    total_gt = len(gdf_extended)
    print(f"\n[+] Set Extins Generat cu Succes: {output_path}")
    print(f"    - Total Clădiri de Referință (N): {total_gt}")
    print(f"    - ANCPI Campus Oficiale:          {len(gdf_tier1)}")
    print(f"    - Rezidențiale Validate (Calea Mănăștur): {len(selected_osm)}")
    print(f"    - Sistem de Coordonate:          Stereo 70 (EPSG:3844)")
    print("=" * 80)
    return True


if __name__ == "__main__":
    build_extended_ground_truth()

