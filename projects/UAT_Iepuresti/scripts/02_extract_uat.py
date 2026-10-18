# -*- coding: utf-8 -*-
"""G2.3: Extract Iepuresti UAT polygon from admin_level=8 candidates (already EPSG:3844 via ogr2ogr)."""
import json

src = json.load(open("data/processed/ancpi/limita_UAT_raw.geojson", encoding="utf-8"))
feats = [f for f in src["features"] if "Iepure" in str(f["properties"].get("name", ""))]
assert len(feats) == 1, "expected 1 Iepuresti feature, got %d" % len(feats)
f = feats[0]
props = f["properties"]
print("name:", props.get("name"))
print("osm_relation_id:", props.get("osm_relation_id"), "osm_way_id:", props.get("osm_way_id"))
print("geometry:", f["geometry"]["type"])
ot = str(props.get("other_tags"))
for t in ot.split('","'):
    if "sirut" in t.lower():
        print("TAG:", t)

out = {
    "type": "FeatureCollection",
    "name": "limita_UAT",
    "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:EPSG::3844"}},
    "features": [{
        "type": "Feature",
        "properties": {
            "name": props.get("name"),
            "siruta": "103684",
            "source": "OpenStreetMap / Geofabrik romania-latest.osm.pbf (admin_level=8)",
            "source_id": str(props.get("osm_relation_id") or props.get("osm_way_id") or ""),
            "license": "ODbL 1.0",
            "notes": "OSM commune boundary, NOT an official ANCPI cadastral UAT limit. Geoportal.ancpi.ro unreachable (DNS).",
        },
        "geometry": f["geometry"],
    }],
}
with open("data/processed/ancpi/limita_UAT.geojson", "w", encoding="utf-8") as fh:
    json.dump(out, fh, ensure_ascii=False)
print("written data/processed/ancpi/limita_UAT.geojson")
