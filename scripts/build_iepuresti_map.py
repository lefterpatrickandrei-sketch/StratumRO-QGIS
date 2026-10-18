from __future__ import annotations

import json
import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from xml.sax.saxutils import escape

import geopandas as gpd
import requests
from pyproj import CRS
from shapely.geometry import LineString, MultiPolygon, Polygon, shape
from shapely.ops import polygonize, unary_union


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "workspace" / "UAT_Iepuresti"
OUT.mkdir(parents=True, exist_ok=True)
GPKG = OUT / "UAT_Iepuresti.gpkg"
QGZ = OUT / "UAT_Iepuresti.qgz"
CRS_OUT = "EPSG:3844"
OVERPASS_ENDPOINTS = [
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass-api.de/api/interpreter",
]


def overpass(query: str) -> dict:
    last_error = None
    for endpoint in OVERPASS_ENDPOINTS:
        try:
            response = requests.get(
                endpoint,
                params={"data": query},
                headers={"User-Agent": "StratumRO-UAT-Iepuresti/1.0"},
                timeout=35,
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            last_error = exc
    raise RuntimeError(f"Overpass endpoints unavailable: {last_error}")


def relation_boundary() -> Polygon | MultiPolygon:
    # Nominatim provides the OSM administrative boundary efficiently; the
    # feature layers themselves are subsequently retrieved from Overpass.
    response = requests.get(
        "https://nominatim.openstreetmap.org/search",
        params={"q": "Iepurești, Giurgiu, Romania", "format": "json", "polygon_geojson": 1, "limit": 10},
        headers={"User-Agent": "StratumRO-UAT-Iepuresti/1.0"},
        timeout=90,
    )
    response.raise_for_status()
    candidates = [x for x in response.json() if x.get("geojson") and x.get("type") in ("administrative", "boundary")]
    if candidates:
        return shape(candidates[0]["geojson"]).buffer(0)
    raise RuntimeError("OSM administrative relation for Iepurești was not found")
    rel = data["elements"][0]
    rings = []
    for member in rel.get("members", []):
        if member.get("type") == "way" and member.get("geometry"):
            rings.append([(p["lon"], p["lat"]) for p in member["geometry"]])
    if not rings:
        raise RuntimeError("Administrative relation has no geometry")
    # Relation members are often unclosed segments; polygonize their merged linework.
    lines = [LineString(r) for r in rings if len(r) >= 2]
    polygons = list(polygonize(unary_union(lines)))
    if not polygons:
        polygons = [Polygon(r) for r in rings if len(r) >= 4 and r[0] == r[-1]]
    if not polygons:
        raise RuntimeError("Administrative relation geometry could not be polygonized")
    boundary = unary_union(polygons).buffer(0)
    if boundary.is_empty:
        raise RuntimeError("Administrative boundary is empty")
    return boundary


def element_features(data: dict, tag_filter: str, geom_type: str):
    features = []
    for el in data.get("elements", []):
        geom = el.get("geometry")
        if not geom or el.get("type") != "way":
            continue
        coords = [(p["lon"], p["lat"]) for p in geom]
        if geom_type == "polygon" and len(coords) >= 4 and coords[0] == coords[-1]:
            g = Polygon(coords)
        elif geom_type == "line" and len(coords) >= 2:
            g = LineString(coords)
        else:
            continue
        if g.is_empty:
            continue
        tags = el.get("tags", {})
        features.append({"geometry": g, "osm_id": el.get("id"), "source": "OSM", "tag": tags.get(tag_filter, "")})
    return features


def query_bbox(boundary):
    minx, miny, maxx, maxy = boundary.bounds
    return f"{miny},{minx},{maxy},{maxx}"


def fetch_layers(boundary):
    bbox = query_bbox(boundary)
    try:
        query = f'''[out:json][timeout:45];(way["building"]({bbox});way["highway"]({bbox});way["waterway"]({bbox});way["natural"="wood"]({bbox});way["landuse"="forest"]({bbox}););out geom;'''
        data = overpass(query)
        elements = data.get("elements", [])
        buildings = {"elements": [x for x in elements if "building" in x.get("tags", {})]}
        roads = {"elements": [x for x in elements if "highway" in x.get("tags", {})]}
        water = {"elements": [x for x in elements if "waterway" in x.get("tags", {})]}
        forest = {"elements": [x for x in elements if x.get("tags", {}).get("natural") == "wood"]}
        forest2 = {"elements": [x for x in elements if x.get("tags", {}).get("landuse") == "forest"]}
    except RuntimeError:
        # OSM API map is the documented fallback when Overpass is unavailable.
        minx, miny, maxx, maxy = boundary.bounds
        xml = requests.get(
            "https://api.openstreetmap.org/api/0.6/map",
            params={"bbox": f"{minx},{miny},{maxx},{maxy}"},
            headers={"User-Agent": "StratumRO-UAT-Iepuresti/1.0"},
            timeout=90,
        ).text
        root = ET.fromstring(xml)
        nodes = {n.attrib["id"]: (float(n.attrib["lon"]), float(n.attrib["lat"])) for n in root.findall("node")}
        elements = []
        for way in root.findall("way"):
            tags = {t.attrib["k"]: t.attrib["v"] for t in way.findall("tag")}
            coords = [nodes.get(nd.attrib["ref"]) for nd in way.findall("nd")]
            coords = [c for c in coords if c]
            elements.append({"type": "way", "id": int(way.attrib["id"]), "tags": tags, "geometry": [{"lon": c[0], "lat": c[1]} for c in coords]})
        buildings = {"elements": [x for x in elements if "building" in x["tags"]]}
        roads = {"elements": [x for x in elements if "highway" in x["tags"]]}
        water = {"elements": [x for x in elements if "waterway" in x["tags"]]}
        forest = {"elements": [x for x in elements if x["tags"].get("natural") == "wood"]}
        forest2 = {"elements": [x for x in elements if x["tags"].get("landuse") == "forest"]}
    return (
        element_features(buildings, "building", "polygon"),
        element_features(roads, "highway", "line"),
        element_features(water, "waterway", "line"),
        element_features(forest, "natural", "polygon")
        + element_features(forest2, "landuse", "polygon"),
    )


def frame(features, geometry_type, boundary=None):
    if not features:
        return gpd.GeoDataFrame({"status": ["DATA GAP"]}, geometry=[], crs="EPSG:4326")
    gdf = gpd.GeoDataFrame(features, geometry="geometry", crs="EPSG:4326")
    if boundary is not None:
        gdf = gdf[gdf.geometry.intersects(boundary)].copy()
        gdf.geometry = gdf.geometry.intersection(boundary)
    return gdf.to_crs(CRS_OUT)


def empty_layer(name, geometry_type, status):
    return gpd.GeoDataFrame(
        {"status": [], "source": []},
        geometry=gpd.GeoSeries([], crs=CRS_OUT),
    )


def write_layer(gdf, name, mode):
    gdf = gdf.copy()
    if len(gdf):
        gdf["geometry"] = gdf.geometry.apply(
            lambda geom: geom.buffer(0) if geom is not None and geom.geom_type in ("Polygon", "MultiPolygon") else geom
        )
    gdf.to_file(GPKG, layer=name, driver="GPKG", engine="pyogrio", mode=mode)


def qgs_xml(layer_names):
    groups = {"00_CONTROL": ["limita_UAT", "limita_intravilan"], "01_RASTER": [], "02_REFERENCE": ["imobile_cadastrale"], "03_OUTPUT_VECTOR": ["constructii", "drumuri_poligon", "drumuri_ax", "cursuri_apa", "paduri"], "04_QA_QC": []}
    nodes = []
    layer_nodes = []
    for group, names in groups.items():
        children = "".join(
            f'<layer-tree-layer id="{escape(n)}" name="{escape(n)}" '
            f'providerKey="ogr" checked="Qt::Checked"/>'
            for n in names if n in layer_names
        )
        nodes.append(f'<layer-tree-group name="{escape(group)}" expanded="1">{children}</layer-tree-group>')
    for n in layer_names:
        layer_nodes.append(
            f'<maplayer type="vector" name="{escape(n)}" geometry="Unknown" simplifyDrawingHints="1" simplifyLocal="1" simplifyMaxScale="1" simplifyDrawingTol="1" readOnly="0" provider="ogr">'
            f'<datasource>{escape(str(GPKG) + "|layername=" + n)}</datasource>'
            f'<layername>{escape(n)}</layername><srs><spatialrefsys>'
            f'<authid>{CRS_OUT}</authid></spatialrefsys></srs></maplayer>'
        )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<qgis projectname="UAT_Iepuresti" version="3.40.0">'
        f'<projectCrs><spatialrefsys><authid>{CRS_OUT}</authid></spatialrefsys></projectCrs>'
        f'<layer-tree-root>{"".join(nodes)}</layer-tree-root>'
        f'<projectlayers>{"".join(layer_nodes)}</projectlayers></qgis>'
    )


def main():
    if GPKG.exists():
        GPKG.unlink()
    boundary_wgs = relation_boundary()
    building_f, road_f, water_f, forest_f = fetch_layers(boundary_wgs)
    boundary = gpd.GeoDataFrame([{"source": "OSM", "name": "Iepurești", "status": "SOURCE_OPEN_DATA"}], geometry=[boundary_wgs], crs="EPSG:4326").to_crs(CRS_OUT)
    buildings = frame(building_f, "polygon", boundary_wgs)
    if len(buildings):
        buildings["geometry"] = buildings.geometry.buffer(0.50).buffer(0)
        buildings["offset_m"] = 0.50
        buildings["source"] = "OSM building footprint + outward buffer"
    roads = frame(road_f, "line", boundary_wgs)
    water = frame(water_f, "line", boundary_wgs)
    forest = frame(forest_f, "polygon", boundary_wgs)
    road_poly = roads.copy()
    if len(road_poly):
        road_poly["geometry"] = road_poly.geometry.buffer(3.0, cap_style=2, join_style=2)
        road_poly["buffer_m"] = 3.0
        road_poly["source"] = "OSM centerline buffered approximation"
    layers = {
        "limita_UAT": boundary,
        "limita_intravilan": empty_layer("limita_intravilan", "Polygon", "DATA GAP — INTRAVILAN"),
        "imobile_cadastrale": empty_layer("imobile_cadastrale", "Polygon", "DATA GAP — CADASTRAL REFERENCE"),
        "constructii": buildings,
        "drumuri_poligon": road_poly,
        "drumuri_ax": roads,
        "cursuri_apa": water,
        "paduri": forest,
    }
    first = True
    for name, gdf in layers.items():
        write_layer(gdf, name, "w" if first else "a")
        first = False
    xml = qgs_xml(list(layers))
    qgs = OUT / "UAT_Iepuresti.qgs"
    qgs.write_text(xml, encoding="utf-8")
    with zipfile.ZipFile(QGZ, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(qgs, "UAT_Iepuresti.qgs")
    qgs.unlink()
    print(json.dumps({"gpkg": str(GPKG), "qgz": str(QGZ), "counts": {k: int(len(v)) for k, v in layers.items()}, "crs": CRS_OUT}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
