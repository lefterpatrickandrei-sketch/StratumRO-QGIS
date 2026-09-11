# -*- coding: utf-8 -*-
"""
StratumRO — Verificare și Clasificare Automată False Positives (116 FP) vs. OpenStreetMap
========================================================================================
Efectuează intersecția spațială riguroasă între cele 116 detecții AI calificate drept „FP”
față de setul de 29 clădiri ANCPI și registrul OpenStreetMap (OSM) pentru întregul AOI USAMV Cluj:
  1. FP confirmat de OSM (IoU >= 0.20 sau suprapunere >= 40%) -> Clădire reală ne-cartată în etalonul ANCPI.
  2. FP fără corespondent OSM -> Anexă gospodărească, șopron/container temporar, vegetație sau artefact.
Salvează raportul complet în reports/tier1_cadastre/fp_osm_verification.csv.
"""

import os
import sys
import json
import csv
import time
from pathlib import Path
from typing import Dict, List, Any, Optional

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

import requests
import numpy as np
import geopandas as gpd
from shapely.geometry import Polygon, box
from shapely.validation import make_valid
from pyproj import Transformer

sys.path.insert(0, os.path.abspath('.'))
from engine.evaluation import evaluate_dataset, compute_iou
from stratum_ro.vectorizer import CadastralVectorizer


GT_PATH = "data/ground_truth/tier1_teren.geojson"
PRED_PATH = "workspace/output/cladiri_stereo70.gpkg"
PRED_LAYER = "CLADIRI_HIBRID"
OSM_GEOJSON_CACHE = "data/ground_truth/osm_buildings_aoi.geojson"
OUTPUT_CSV = "reports/tier1_cadastre/fp_osm_verification.csv"
OUTPUT_JSON = "reports/tier1_cadastre/fp_osm_summary.json"

# Bounding box AOI USAMV Cluj (WGS84 și Stereo 70)
AOI_BBOX_WGS84 = (46.754171, 23.565300, 46.763773, 23.578778)


def fetch_osm_buildings_aoi(cache_path: str = OSM_GEOJSON_CACHE) -> gpd.GeoDataFrame:
    """Descarcă sau încarcă din cache clădirile OSM din AOI în Stereo 70."""
    if os.path.exists(cache_path):
        print(f"[+] Încărcare clădiri OSM din cache local: {cache_path}")
        gdf = gpd.read_file(cache_path)
        if gdf.crs is None or gdf.crs.to_epsg() != 3844:
            gdf = gdf.to_crs("EPSG:3844")
        return gdf

    print("[*] Descărcare clădiri OSM din Overpass API pentru AOI Cluj USAMV...")
    minlat, minlon, maxlat, maxlon = AOI_BBOX_WGS84
    query = f"""[out:json][timeout:35];
(
  way["building"]({minlat}, {minlon}, {maxlat}, {maxlon});
  relation["building"]({minlat}, {minlon}, {maxlat}, {maxlon});
);
out body;
>;
out skel qt;"""

    headers = {"User-Agent": "StratumRO-Evaluation/1.0 (Geomatics Research Cluj; https://github.com/lefterpatrickandrei-sketch/StratumRO-QGIS)"}
    resp = requests.post("https://overpass-api.de/api/interpreter", data={"data": query}, headers=headers, timeout=40)
    resp.raise_for_status()
    data = resp.json()

    nodes = {e["id"]: (e["lon"], e["lat"]) for e in data.get("elements", []) if e["type"] == "node"}
    transformer = Transformer.from_crs("EPSG:4326", "EPSG:3844", always_xy=True)

    records = []
    for e in data.get("elements", []):
        if e.get("type") == "way" and "tags" in e and "building" in e["tags"]:
            node_ids = e.get("nodes", [])
            if len(node_ids) >= 4 and node_ids[0] == node_ids[-1]:
                pts_geo = [nodes[nid] for nid in node_ids if nid in nodes]
                if len(pts_geo) == len(node_ids):
                    pts_st70 = [transformer.transform(lon, lat) for lon, lat in pts_geo]
                    poly = make_valid(Polygon(pts_st70))
                    if isinstance(poly, Polygon) and poly.is_valid and poly.area >= 5.0:
                        records.append({
                            "osm_id": str(e["id"]),
                            "building_tag": e["tags"].get("building", "yes"),
                            "name": e["tags"].get("name", ""),
                            "amenity": e["tags"].get("amenity", ""),
                            "area_m2": round(poly.area, 2),
                            "geometry": poly
                        })

    gdf = gpd.GeoDataFrame(records, geometry="geometry", crs="EPSG:3844")
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    gdf.to_file(cache_path, driver="GeoJSON")
    print(f"[+] Salvat {len(gdf)} clădiri OSM în: {cache_path}")
    return gdf


def main():
    print("=" * 80)
    print("  STRATUM-RO: VERIFICARE & CLASIFICARE AUTOMATĂ A CELOR 116 FALSE POSITIVES")
    print("=" * 80)

    if not os.path.exists(GT_PATH) or not os.path.exists(PRED_PATH):
        print(f"[-] EROARE: Fișierele de intrare lipsesc: {GT_PATH} sau {PRED_PATH}")
        sys.exit(1)

    # 1. Încărcare date
    gdf_gt = gpd.read_file(GT_PATH)
    gdf_pred = gpd.read_file(PRED_PATH, layer=PRED_LAYER)
    gdf_osm = fetch_osm_buildings_aoi()

    print(f"    - Clădiri de referință ANCPI: {len(gdf_gt)}")
    print(f"    - Predicții AI hibride:       {len(gdf_pred)}")
    print(f"    - Clădiri OSM în AOI:         {len(gdf_osm)}")

    # 2. Identificare predicții TP și FP față de ANCPI
    eval_summary = evaluate_dataset(gdf_pred, gdf_gt, min_iou_match=0.30)
    matched_pred_ids = set()
    for b in eval_summary.building_results:
        if b.matched and not b.pred_id.startswith("NONE"):
            matched_pred_ids.add(str(b.pred_id))

    # Predicțiile care nu au făcut match cu niciuna din cele 29 clădiri ANCPI sunt FP
    fp_items = []
    vectorizer = CadastralVectorizer(crs="EPSG:3844")

    for idx, row in gdf_pred.iterrows():
        p_id = str(row.get("id", idx))
        if p_id not in matched_pred_ids:
            fp_items.append(row)

    print(f"\n[+] Număr identificat de False Positives (FP) față de ANCPI GT: {len(fp_items)}")

    # 3. Intersecție spațială FP vs. OSM
    results = []
    osm_confirmed_count = 0
    osm_spatial_overlap_count = 0
    temporary_container_count = 0
    annex_outbuilding_count = 0
    dense_canopy_noise_count = 0

    spatial_index_osm = gdf_osm.sindex

    for row in fp_items:
        fp_geom = row.geometry
        fp_id = str(row.get("id"))
        fp_area = float(row.get("area_m2", fp_geom.area))
        mean_h = float(row.get("inaltime_med_m", 4.0))
        max_h = float(row.get("inaltime_max_m", 5.5))

        # Căutare clădiri OSM candidate prin sindex
        possible_matches_idx = list(spatial_index_osm.intersection(fp_geom.bounds))
        possible_matches = gdf_osm.iloc[possible_matches_idx]

        best_osm_id = "NONE"
        best_osm_tag = ""
        best_osm_name = ""
        best_iou = 0.0
        best_overlap_pct = 0.0

        for _, osm_row in possible_matches.iterrows():
            osm_poly = osm_row.geometry
            if fp_geom.intersects(osm_poly):
                inter_area = fp_geom.intersection(osm_poly).area
                iou = compute_iou(fp_geom, osm_poly)
                overlap_fp = (inter_area / fp_geom.area) * 100.0
                overlap_osm = (inter_area / osm_poly.area) * 100.0
                max_overlap = max(overlap_fp, overlap_osm)

                if iou > best_iou or max_overlap > best_overlap_pct:
                    best_iou = max(best_iou, iou)
                    best_overlap_pct = max(best_overlap_pct, max_overlap)
                    best_osm_id = str(osm_row.get("osm_id", "YES"))
                    best_osm_tag = str(osm_row.get("building_tag", "yes"))
                    best_osm_name = str(osm_row.get("name", ""))

        # Clasificare semantică a FP-ului
        # 1. Confirmat de OSM
        if best_iou >= 0.20 or best_overlap_pct >= 40.0:
            osm_confirmed_count += 1
            cat = "CLADIRE_REALA_CONFIRMATA_OSM"
            status_desc = f"Clădire fizică reală înregistrată în OSM (id={best_osm_id}, tag={best_osm_tag})"
        elif best_overlap_pct >= 15.0:
            osm_spatial_overlap_count += 1
            cat = "CLADIRE_REALA_PARTIAL_SUPRAPUSA_OSM"
            status_desc = f"Corp adiacent/aripă parțial suprapusă cu clădire OSM (id={best_osm_id})"
        else:
            # 2. Nu există în OSM - analiză morfologică
            temp_check = vectorizer.classify_temporary_structure(fp_geom)
            if temp_check.get("is_temporary"):
                temporary_container_count += 1
                cat = temp_check.get("type", "STRUCTURA_TEMPORARA")
                status_desc = f"Structură provizorie ({temp_check.get('type')}, {temp_check.get('width_m', 0):.1f}x{temp_check.get('length_m', 0):.1f}m)"
            elif fp_area < 45.0:
                annex_outbuilding_count += 1
                cat = "ANEXA_INDIVIDUALA_MICA"
                status_desc = f"Anexă gospodărească/garaj ({fp_area:.1f} mp, H={mean_h:.1f}m)"
            elif mean_h < 3.2 and fp_area > 150.0:
                cat = "SERA_SAU_PLATFORMA_ACOPERITA"
                status_desc = f"Platformă/seră joasă ({fp_area:.1f} mp, H={mean_h:.1f}m)"
            else:
                dense_canopy_noise_count += 1
                cat = "CLADIRE_POTENTIALA_SAU_VEGETATIE_DENSA"
                status_desc = f"Corp izolat în campus/curte ({fp_area:.1f} mp, H={mean_h:.1f}m)"

        results.append({
            "fp_id": fp_id,
            "area_m2": round(fp_area, 2),
            "mean_height_m": round(mean_h, 2),
            "max_height_m": round(max_h, 2),
            "osm_matched": best_iou >= 0.20 or best_overlap_pct >= 40.0,
            "osm_id": best_osm_id,
            "osm_tag": best_osm_tag,
            "osm_name": best_osm_name,
            "osm_iou": round(best_iou, 4),
            "osm_overlap_pct": round(best_overlap_pct, 1),
            "category_estimated": cat,
            "description": status_desc
        })

    # 4. Salvare fișiere de raport
    os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(results[0].keys()))
        writer.writeheader()
        writer.writerows(results)
    print(f"\n[+] Raport tabelar CSV salvat în: {OUTPUT_CSV}")

    total_real_osm = osm_confirmed_count + osm_spatial_overlap_count
    pct_real = (total_real_osm / len(results)) * 100.0 if results else 0.0

    summary_data = {
        "total_fp_evaluated": len(results),
        "osm_confirmed_real_buildings": osm_confirmed_count,
        "osm_partial_overlap_buildings": osm_spatial_overlap_count,
        "total_osm_backed_real_structures": total_real_osm,
        "pct_osm_backed_real": round(pct_real, 2),
        "temporary_containers_or_sheds": temporary_container_count,
        "small_annexes_or_garages": annex_outbuilding_count,
        "other_unmapped_or_canopy": len(results) - total_real_osm - temporary_container_count - annex_outbuilding_count,
        "categories_breakdown": {
            cat: sum(1 for r in results if r["category_estimated"] == cat)
            for cat in sorted(set(r["category_estimated"] for r in results))
        }
    }

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2, ensure_ascii=False)
    print(f"[+] Raport sumar JSON salvat în: {OUTPUT_JSON}")

    # 5. Afișare rezultate
    print("\n" + "=" * 80)
    print("              REZULTAT AUDIT FALSE POSITIVES (116 FP) vs. OSM")
    print("=" * 80)
    print(f"  Total predicții analizate (FP față de GT ANCPI 29):    {len(results)}")
    print(f"  [+] Clădiri fizice REALE confirmate de OpenStreetMap: {total_real_osm} din {len(results)} ({pct_real:.1f}%)")
    print(f"      - Confirmate 1:1 prin IoU/Overlap mare:           {osm_confirmed_count}")
    print(f"      - Corpuri adiacente/aripi suprapuse parțial OSM:  {osm_spatial_overlap_count}")
    print(f"  [~] Anexe mici / garaje neînregistrate în ANCPI:      {annex_outbuilding_count}")
    print(f"  [~] Containere modulare / construcții provizorii:     {temporary_container_count}")
    print(f"  [-] Alte corpuri ne-cartate / zgomot coronament:      {summary_data['other_unmapped_or_canopy']}")
    print("-" * 80)
    print("  Distribuția exactă pe categorii:")
    for cat, count in summary_data["categories_breakdown"].items():
        print(f"    * {cat:40s}: {count:3d} ({count/len(results)*100:.1f}%)")
    print("=" * 80)


if __name__ == "__main__":
    main()
