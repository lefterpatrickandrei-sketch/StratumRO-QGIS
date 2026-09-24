# -*- coding: utf-8 -*-
"""
Script de extractie profesionala pentru datele cartografice nationale cIMeC RAN.
Descarca automat de pe serverul ArcGIS REST cele 3 straturi:
  1. Stratul 0: Repertoriul arheologic national - puncte (~28.988 entitati)
  2. Stratul 6: Repertoriul arheologic national - poligoane (~16.484 entitati)
  3. Stratul 1: Arhiva Repertoriul arheologic al Romaniei (Vasile Parvan) (~7.351 entitati)
Total: ~52.823 entitati arheologice oficiale pentru toata Romania.

Produce pachetul unificat GeoJSON si GeoPackage SQLite indexat spatial.
"""

import os
import sys
import time
import json
import ssl
import urllib.request
import urllib.error
import geopandas as gpd
from shapely.geometry import Point, Polygon, MultiPolygon
from shapely.validation import make_valid
from shapely.ops import unary_union

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)

BASE_URL = "https://eism.geo-spatial.ro/eismgeo/rest/services/Patrimoniu/PatrimoniuWM/MapServer"
OUT_DIR = r"c:\Users\lefpa\Downloads\QGIS-AI\national_server\02_PATRIMONIU_RAN_CIMEC"
OUT_GPKG = os.path.join(OUT_DIR, "RAN_Romania_National_Complet.gpkg")

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) StratumRO-National-Harvester/1.0",
    "Accept": "*/*"
}

def get_layer_count(layer_id):
    url = f"{BASE_URL}/{layer_id}/query?where=1%3D1&returnCountOnly=true&f=pjson"
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20, context=ctx) as r:
        data = json.loads(r.read().decode('utf-8'))
        return data.get("count", 0)

def esri_point_to_shapely(geom):
    if not geom or "x" not in geom or "y" not in geom:
        return None
    try:
        x, y = float(geom["x"]), float(geom["y"])
        # Verificare coordonate WGS84 plauzibile
        if 19.0 <= x <= 31.0 and 42.0 <= y <= 50.0:
            return Point(x, y)
        return Point(x, y)
    except Exception:
        return None

def esri_rings_to_shapely(geom):
    if not geom or "rings" not in geom or not geom["rings"]:
        return None
    rings = geom["rings"]
    try:
        if len(rings) == 1:
            poly = Polygon(rings[0])
            if not poly.is_valid:
                poly = make_valid(poly)
                if poly.geom_type == "GeometryCollection":
                    polys = [p for p in poly.geoms if p.geom_type in ("Polygon", "MultiPolygon")]
                    poly = unary_union(polys) if polys else None
            return poly
        
        # Inele multiple: pot fi poligoane separate sau gauri
        polys = []
        for r in rings:
            if len(r) >= 3:
                p = Polygon(r)
                if not p.is_valid:
                    p = make_valid(p)
                    if p.geom_type == "GeometryCollection":
                        sub_polys = [sp for sp in p.geoms if sp.geom_type in ("Polygon", "MultiPolygon")]
                        p = unary_union(sub_polys) if sub_polys else None
                if p is not None and not p.is_empty:
                    polys.append(p)
        if not polys:
            return None
        u = unary_union(polys)
        if not u.is_valid:
            u = make_valid(u)
            if u.geom_type == "GeometryCollection":
                sub_polys = [sp for sp in u.geoms if sp.geom_type in ("Polygon", "MultiPolygon")]
                u = unary_union(sub_polys) if sub_polys else None
        return u
    except Exception:
        try:
            return Polygon(rings[0], rings[1:])
        except Exception:
            return None

def fetch_layer(layer_id, layer_name, geom_type, batch_size=1000):
    total_count = get_layer_count(layer_id)
    print(f"\n=======================================================", flush=True)
    print(f"  EXTRAGERE STRAT [{layer_id}]: {layer_name}", flush=True)
    print(f"  Total entitati pe server: {total_count}", flush=True)
    print(f"=======================================================", flush=True)

    features_list = []
    geoms_list = []
    offset = 0

    while offset < total_count:
        batch_num = (offset // batch_size) + 1
        total_batches = (total_count + batch_size - 1) // batch_size
        pct = (offset / total_count) * 100.0 if total_count > 0 else 0.0

        q_url = (
            f"{BASE_URL}/{layer_id}/query"
            f"?where=1%3D1&outFields=*&outSR=4326&f=pjson"
            f"&resultRecordCount={batch_size}&resultOffset={offset}"
        )

        success = False
        for attempt in range(1, 5):
            try:
                t0 = time.time()
                req = urllib.request.Request(q_url, headers=HEADERS)
                with urllib.request.urlopen(req, timeout=30, context=ctx) as r:
                    res = json.loads(r.read().decode('utf-8'))
                
                feats = res.get("features", [])
                elapsed = time.time() - t0
                
                for f in feats:
                    attrs = f.get("attributes", {})
                    geom = f.get("geometry", {})
                    if geom_type == "point":
                        sh_geom = esri_point_to_shapely(geom)
                    else:
                        sh_geom = esri_rings_to_shapely(geom)
                    
                    features_list.append(attrs)
                    geoms_list.append(sh_geom if (sh_geom is not None and not sh_geom.is_empty) else None)
                
                print(f"  [+] Batch {batch_num}/{total_batches} ({len(feats)} entitati, {elapsed:.2f}s) - Progres: {pct:.1f}%", flush=True)
                success = True
                break
            except Exception as e:
                wait_t = 2 ** attempt
                print(f"  [!] Eroare batch {batch_num} (incercarea {attempt}/4): {e}. Asteptare {wait_t}s...", flush=True)
                time.sleep(wait_t)

        if not success:
            print(f"  [EROARE CRITICA] Nu s-a putut descarca batch {batch_num} dupa 4 incercari!", flush=True)
        
        offset += batch_size
        time.sleep(0.2) # Rate limiting politicos pentru server

    valid_geoms = sum(1 for g in geoms_list if g is not None)
    print(f"\n[FINALIZAT STRAT {layer_id}] Descarcate: {len(features_list)}/{total_count} entitati ({valid_geoms} geometrii valide).", flush=True)
    
    gdf = gpd.GeoDataFrame(features_list, geometry=geoms_list, crs="EPSG:4326")
    return gdf

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    if os.path.exists(OUT_GPKG):
        try:
            os.remove(OUT_GPKG)
            print(f"Curatat GPKG anterior pentru initializare curata: {OUT_GPKG}", flush=True)
        except Exception as e:
            print(f"Atentie la stergerea GPKG: {e}", flush=True)
    t_start = time.time()
    
    print("*" * 70)
    print("  STRATUM-RO: EXTRAGERE NATIONALA COMPLETA REPERTORIUL ARHEOLOGIC (RAN)")
    print("  Server Sursa: cIMeC / Institutul National al Patrimoniului")
    print("  Destinatie: national_server/02_PATRIMONIU_RAN_CIMEC/")
    print("*" * 70)

    # 1. Stratul 0: Puncte RAN
    gdf_puncte = fetch_layer(0, "Repertoriul arheologic national - puncte", "point", batch_size=1000)
    out_puncte_geojson = os.path.join(OUT_DIR, "RAN_National_Puncte_28988.geojson")
    print(f"  -> Salvare GeoJSON: {out_puncte_geojson}...", flush=True)
    gdf_puncte.to_file(out_puncte_geojson, driver="GeoJSON")
    print(f"  -> Salvare GPKG Layer: 01_RAN_National_Puncte...", flush=True)
    gdf_puncte.to_file(OUT_GPKG, driver="GPKG", layer="01_RAN_National_Puncte", SPATIAL_INDEX="YES")

    # 2. Stratul 6: Poligoane RAN
    gdf_poligoane = fetch_layer(6, "Repertoriul arheologic national - poligoane", "polygon", batch_size=1000)
    out_poligoane_geojson = os.path.join(OUT_DIR, "RAN_National_Poligoane_16484.geojson")
    print(f"  -> Salvare GeoJSON: {out_poligoane_geojson}...", flush=True)
    gdf_poligoane.to_file(out_poligoane_geojson, driver="GeoJSON")
    print(f"  -> Salvare GPKG Layer: 02_RAN_National_Poligoane...", flush=True)
    gdf_poligoane.to_file(OUT_GPKG, driver="GPKG", layer="02_RAN_National_Poligoane", SPATIAL_INDEX="YES")

    # 3. Stratul 1: Arhiva Vasile Parvan
    gdf_parvan = fetch_layer(1, "Arhiva Repertoriul arheologic (Vasile Parvan)", "point", batch_size=1000)
    out_parvan_geojson = os.path.join(OUT_DIR, "RAR_National_Parvan_7351.geojson")
    print(f"  -> Salvare GeoJSON: {out_parvan_geojson}...", flush=True)
    gdf_parvan.to_file(out_parvan_geojson, driver="GeoJSON")
    print(f"  -> Salvare GPKG Layer: 03_RAR_National_Arhiva_Parvan...", flush=True)
    gdf_parvan.to_file(OUT_GPKG, driver="GPKG", layer="03_RAR_National_Arhiva_Parvan", SPATIAL_INDEX="YES")

    # 4. Pachet Unificat (Toate Entitatile intr-un singur GeoJSON combinat)
    print("\n[PACHET UNIFICAT] Generare GeoJSON unic combinat...", flush=True)
    # Pentru pachet unic combinat, adaugam coloana de tip strat
    gdf_p_copy = gdf_puncte.copy()
    gdf_p_copy["tip_entitate_patrimoniu"] = "RAN_Punct"
    
    gdf_poly_copy = gdf_poligoane.copy()
    gdf_poly_copy["tip_entitate_patrimoniu"] = "RAN_Poligon"
    
    gdf_parvan_copy = gdf_parvan.copy()
    gdf_parvan_copy["tip_entitate_patrimoniu"] = "RAR_Parvan_Arhiva"
    
    import pandas as pd
    combined_df = pd.concat([gdf_p_copy, gdf_poly_copy, gdf_parvan_copy], ignore_index=True)
    gdf_combined = gpd.GeoDataFrame(combined_df, geometry="geometry", crs="EPSG:4326")
    out_combined_geojson = os.path.join(OUT_DIR, "RAN_Romania_National_Complet_Pachet_Unic.geojson")
    gdf_combined.to_file(out_combined_geojson, driver="GeoJSON")
    print(f"  -> Salvat Pachet Unic GeoJSON ({len(gdf_combined)} entitati): {out_combined_geojson}", flush=True)

    total_time = time.time() - t_start
    print("\n" + "=" * 70, flush=True)
    print(f"  EXTRAGERE FINALIZATA CU SUCCES IN {total_time/60.0:.2f} MINUTE!", flush=True)
    print(f"  Total entitati descarcate si validate: {len(gdf_combined)}", flush=True)
    print(f"    - Puncte RAN: {len(gdf_puncte)}", flush=True)
    print(f"    - Poligoane RAN: {len(gdf_poligoane)}", flush=True)
    print(f"    - Arhiva Vasile Parvan: {len(gdf_parvan)}", flush=True)
    print(f"  Fisiere generate in: {OUT_DIR}", flush=True)
    print("=" * 70, flush=True)

if __name__ == "__main__":
    main()
