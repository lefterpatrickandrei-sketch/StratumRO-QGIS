# -*- coding: utf-8 -*-
"""
Module for extracting and structuring ANCPI Land Use Categories (Ordinul 600/2023)
from OpenStreetMap and spatial boundaries for StratumRO.
"""

import os
import json
import urllib.request
import numpy as np
import geopandas as gpd
from shapely.geometry import shape, Polygon, MultiPolygon, LineString, Point, box
from shapely.ops import unary_union, transform
import pyproj

def get_ancpi_landuse(bounds_stereo70, sector_boundary, cache_file="workspace/output/osm_ancpi_cache.json"):
    """
    Extrage și clasifică categoriile de folosință ale terenului conform ANCPI Ordinul 600/2023:
      - DR: Căi de comunicații rutiere (drumuri, străzi, parcări, alei)
      - HR: Hidrografie / Ape curgătoare (pâraie, canale, râuri)
      - VN: Vii și plantații viticole
      - CIMITIR: Terenuri cu destinație specială (TDS / subcategorie CC)
      - A: Terenuri arabile / agricole deschise
    """
    to_wgs84 = pyproj.Transformer.from_crs("EPSG:3844", "EPSG:4326", always_xy=True).transform
    to_stereo70 = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:3844", always_xy=True).transform

    minx, miny, maxx, maxy = bounds_stereo70
    lon_min, lat_min = to_wgs84(minx, miny)
    lon_max, lat_max = to_wgs84(maxx, maxy)

    os.makedirs(os.path.dirname(cache_file), exist_ok=True)
    osm_data = None

    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                osm_data = json.load(f)
        except Exception:
            osm_data = None

    if not osm_data:
        url = "https://overpass-api.de/api/interpreter"
        query = f"""[out:json][timeout:30];
(
  way["highway"]({lat_min - 0.001},{lon_min - 0.001},{lat_max + 0.001},{lon_max + 0.001});
  way["waterway"]({lat_min - 0.001},{lon_min - 0.001},{lat_max + 0.001},{lon_max + 0.001});
  way["landuse"]({lat_min - 0.001},{lon_min - 0.001},{lat_max + 0.001},{lon_max + 0.001});
  way["amenity"]({lat_min - 0.001},{lon_min - 0.001},{lat_max + 0.001},{lon_max + 0.001});
);
out body;
>;
out skel qt;
"""
        req = urllib.request.Request(
            url,
            data=query.encode("utf-8"),
            headers={"User-Agent": "StratumRO-Cadastru/2.0 (ancpi@stratum.ro)"}
        )
        try:
            with urllib.request.urlopen(req, timeout=25) as r:
                osm_data = json.loads(r.read().decode("utf-8"))
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(osm_data, f)
        except Exception as e:
            print(f"[StratumRO LandUse] Avertisment la descărcare OSM: {e}")
            osm_data = {"elements": []}

    # Index nodes
    nodes = {}
    for el in osm_data.get("elements", []):
        if el.get("type") == "node":
            nodes[el["id"]] = (el["lon"], el["lat"])

    roads = []
    waters = []
    vineyards = []
    cemeteries = []
    arabiles = []

    for el in osm_data.get("elements", []):
        if el.get("type") != "way" or "nodes" not in el:
            continue
        pts = [nodes[nid] for nid in el["nodes"] if nid in nodes]
        if len(pts) < 2:
            continue

        tags = el.get("tags", {})
        coords_st70 = [to_stereo70(p[0], p[1]) for p in pts]

        # 1. Drumuri (DR)
        if "highway" in tags:
            hw = tags["highway"]
            width = 4.0
            if hw in ["primary", "trunk"]: width = 12.0
            elif hw in ["secondary"]: width = 9.0
            elif hw in ["tertiary"]: width = 7.0
            elif hw in ["residential"]: width = 6.0
            elif hw in ["service"]: width = 4.5
            elif hw in ["footway", "path", "cycleway", "steps", "pedestrian"]: width = 2.5

            ls = LineString(coords_st70)
            poly_road = ls.buffer(width / 2.0, cap_style=2, join_style=2)
            if poly_road.is_valid and not poly_road.is_empty:
                roads.append(poly_road)

        if tags.get("amenity") == "parking":
            if len(coords_st70) >= 3 and coords_st70[0] == coords_st70[-1]:
                p_park = Polygon(coords_st70)
                if p_park.is_valid:
                    roads.append(p_park)

        # 2. Hidrografie (HR)
        if "waterway" in tags:
            ls = LineString(coords_st70)
            poly_water = ls.buffer(3.0, cap_style=2)
            if poly_water.is_valid:
                waters.append(poly_water)

        # 3. Cimitir (CIMITIR / TDS / CC)
        if tags.get("landuse") == "cemetery" or tags.get("amenity") == "grave_yard" or "cimitir" in str(tags).lower():
            if len(coords_st70) >= 3:
                p_cem = Polygon(coords_st70)
                if p_cem.is_valid and p_cem.area > 50.0:
                    cemeteries.append(p_cem)

        # 4. Vii (VN) & Livezi
        lu = tags.get("landuse", "")
        name = str(tags.get("name", "")).lower()
        if (lu in ["vineyard", "orchard"] or "podgori" in name or "livada" in name or "vie" in name or "grape" in str(tags).lower()):
            if len(coords_st70) >= 3:
                p_vin = Polygon(coords_st70)
                if p_vin.is_valid and p_vin.area > 50.0:
                    vineyards.append(p_vin)
        elif lu in ["farmland", "farm", "meadow", "grass", "allotments"]:
            if len(coords_st70) >= 3:
                p_arab = Polygon(coords_st70)
                if p_arab.is_valid and p_arab.area > 50.0:
                    arabiles.append(p_arab)

    # Convert to single MultiPolygons clipped by sector_boundary
    def clean_and_clip(poly_list):
        if not poly_list:
            return Polygon()
        u = unary_union(poly_list)
        if sector_boundary is not None and not sector_boundary.is_empty:
            u = u.intersection(sector_boundary)
        return u

    geom_roads = clean_and_clip(roads)
    geom_waters = clean_and_clip(waters)
    geom_cemeteries = clean_and_clip(cemeteries)
    geom_vineyards = clean_and_clip(vineyards)
    geom_arabiles = clean_and_clip(arabiles)

    return {
        "DR": geom_roads,
        "HR": geom_waters,
        "CIMITIR": geom_cemeteries,
        "VN": geom_vineyards,
        "A": geom_arabiles
    }
