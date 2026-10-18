# -*- coding: utf-8 -*-
"""G4 (Production): Populare straturi GPKG din GeoJSON procesat cu GEOS/OGR."""
from datetime import datetime, timezone
import json, logging, sys
from pathlib import Path
from osgeo import gdal, ogr, osr

gdal.UseExceptions()
ogr.UseExceptions()

ROOT = Path(r"C:\Users\lefpa\Downloads\QGIS-AI\projects\UAT_Iepuresti")
LOG_FILE = ROOT / "logs" / "04_production.log"
STATE_FILE = ROOT / "state" / "state.json"
GPKG_PATH = ROOT / "output" / "UAT_Iepuresti.gpkg"
DATA_PROC = ROOT / "data" / "processed"

def stamp():
    return datetime.now(timezone.utc).isoformat()

def setup_logger():
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(LOG_FILE, encoding="utf-8"),
            logging.StreamHandler(sys.stdout)
        ]
    )

def get_transformer(src_srs, dst_epsg=3844):
    dst_srs = osr.SpatialReference()
    dst_srs.ImportFromEPSG(dst_epsg)
    dst_srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    if src_srs is None:
        src_srs = osr.SpatialReference()
        src_srs.ImportFromEPSG(4326)
    src_srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    return osr.CoordinateTransformation(src_srs, dst_srs)

def normalize_geometries(geom, target_type):
    """Adapteaza tipul de geometrie la schema stratului destinatie."""
    if geom is None or geom.IsEmpty():
        return []
    
    src_type = ogr.GT_Flatten(geom.GetGeometryType())
    
    # Strat destinatie: Polygon
    if target_type == ogr.wkbPolygon:
        if src_type == ogr.wkbPolygon:
            return [geom]
        elif src_type == ogr.wkbMultiPolygon:
            if geom.GetGeometryCount() == 1:
                return [geom.GetGeometryRef(0).Clone()]
            return [geom.GetGeometryRef(i).Clone() for i in range(geom.GetGeometryCount())]
        return [geom]

    # Strat destinatie: MultiPolygon
    elif target_type == ogr.wkbMultiPolygon:
        if src_type == ogr.wkbPolygon:
            return [ogr.ForceToMultiPolygon(geom)]
        return [geom]

    # Strat destinatie: LineString
    elif target_type == ogr.wkbLineString:
        if src_type == ogr.wkbLineString:
            return [geom]
        elif src_type == ogr.wkbMultiLineString:
            if geom.GetGeometryCount() == 1:
                return [geom.GetGeometryRef(0).Clone()]
            return [geom.GetGeometryRef(i).Clone() for i in range(geom.GetGeometryCount())]
        return [geom]

    # Strat destinatie: MultiLineString
    elif target_type == ogr.wkbMultiLineString:
        if src_type == ogr.wkbLineString:
            return [ogr.ForceToMultiLineString(geom)]
        return [geom]

    return [geom]

def populate_layer(gpkg_ds, layer_name, geojson_path, source_name, license_name, notes_default, buffer_dist=0.0):
    if not geojson_path.exists():
        logging.warning("Sursa %s lipseste.", geojson_path)
        return 0

    in_ds = ogr.Open(str(geojson_path))
    if in_ds is None:
        logging.error("Nu s-a putut deschide fisierul: %s", geojson_path)
        return 0

    out_layer = gpkg_ds.GetLayerByName(layer_name)
    if out_layer is None:
        raise RuntimeError(f"Stratul destinatie {layer_name} nu exista in GPKG master")

    # Golire inregistrare anterioara
    out_layer.StartTransaction()
    for fid in [f.GetFID() for f in out_layer]:
        out_layer.DeleteFeature(fid)
    out_layer.CommitTransaction()

    in_layer = in_ds.GetLayer(0)
    transformer = get_transformer(in_layer.GetSpatialRef(), 3844)
    out_defn = out_layer.GetLayerDefn()
    target_geom_type = ogr.GT_Flatten(out_defn.GetGeomType())

    count = 0
    out_layer.StartTransaction()
    for in_feat in in_layer:
        geom = in_feat.GetGeometryRef()
        if geom is None or geom.IsEmpty():
            continue

        geom_3844 = geom.Clone()
        geom_3844.Transform(transformer)

        if buffer_dist > 0.0:
            geom_3844 = geom_3844.Buffer(buffer_dist)
            if geom_3844 is None or geom_3844.IsEmpty():
                continue

        # Identificare sigura a id-ului de sursa fara KeyError
        src_id = str(in_feat.GetFID())
        for id_field in ("osm_id", "id", "@id", "osm_way_id", "name"):
            idx = in_feat.GetFieldIndex(id_field)
            if idx != -1:
                val = in_feat.GetField(idx)
                if val is not None and str(val).strip():
                    src_id = str(val)
                    break

        # Normalizare tip geometrie pentru schema GPKG
        geoms = normalize_geometries(geom_3844, target_geom_type)
        for g in geoms:
            out_feat = ogr.Feature(out_defn)
            out_feat.SetGeometry(g)

            if out_defn.GetFieldIndex("source") != -1:
                out_feat.SetField("source", source_name)
            if out_defn.GetFieldIndex("source_id") != -1:
                out_feat.SetField("source_id", src_id[:64])
            if out_defn.GetFieldIndex("license") != -1:
                out_feat.SetField("license", license_name)
            if out_defn.GetFieldIndex("notes") != -1:
                out_feat.SetField("notes", notes_default[:254])

            out_layer.CreateFeature(out_feat)
            count += 1

    out_layer.CommitTransaction()
    logging.info("Strat '%s' populat cu %d entitati.", layer_name, count)
    return count

def main():
    setup_logger()
    logging.info("--- Lansare Etapa G4 (Production) ---")
    gpkg_ds = ogr.Open(str(GPKG_PATH), 1)
    if gpkg_ds is None:
        logging.error("Nu s-a putut deschide GPKG master: %s", GPKG_PATH)
        return 1

    counts = {}
    counts["limita_UAT"] = populate_layer(gpkg_ds, "limita_UAT", DATA_PROC / "ancpi" / "limita_UAT.geojson", "OSM_PROXY", "ODbL", "REFERENCE: OSM admin_level=8 proxy")
    counts["constructii"] = populate_layer(gpkg_ds, "constructii", DATA_PROC / "osm" / "buildings.geojson", "OSM", "ODbL", "OSM building +0.50m outward buffer", 0.50)
    counts["drumuri_ax"] = populate_layer(gpkg_ds, "drumuri_ax", DATA_PROC / "osm" / "roads.geojson", "OSM", "ODbL", "OSM highway centerlines")
    counts["drumuri_poligon"] = populate_layer(gpkg_ds, "drumuri_poligon", DATA_PROC / "osm" / "roads.geojson", "OSM", "ODbL", "Road polygon buffer 3.0m offset", 3.0)
    counts["cursuri_apa"] = populate_layer(gpkg_ds, "cursuri_apa", DATA_PROC / "osm" / "waterways.geojson", "OSM", "ODbL", "OSM waterway lines")
    counts["paduri"] = populate_layer(gpkg_ds, "paduri", DATA_PROC / "osm" / "forests.geojson", "OSM", "ODbL", "OSM landuse=forest polygons")
    counts["poduri"] = populate_layer(gpkg_ds, "poduri", DATA_PROC / "osm" / "bridges.geojson", "OSM", "ODbL", "OSM bridge=yes linear features")
    counts["limita_intravilan"] = 0
    counts["imobile_cadastrale"] = 0
    gpkg_ds = None

    state = json.loads(STATE_FILE.read_text(encoding="utf-8-sig")) if STATE_FILE.exists() else {}
    state["gate"] = "G4_complete"
    state["gate_since"] = state["updated_at"] = stamp()
    state["production_summary"] = {
        "layer_counts": counts,
        "buffer_applied": {"constructii": "0.50m", "drumuri_poligon": "3.00m"},
        "crs": "EPSG:3844",
        "status": "SUCCESS"
    }
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    logging.info("G4_complete salvat in state.json")
    return 0

if __name__ == "__main__":
    sys.exit(main())
