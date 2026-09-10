# -*- coding: utf-8 -*-
"""
StratumRO — Modul de Ingestie Date Teren / Cadastru Oficial (Tier 1 & Tier 2)
=============================================================================
Convertește planurile topografice / cadastrale AutoCAD (DXF) sau extrasele ANCPI
în poligoane de referință Stereo 70 (EPSG:3844) pentru evaluarea oficială.

Suportă:
  - DXF exportat din TopoLT / AutoCAD (Release 12 - 2024 via ezdxf)
  - Filtrare inteligentă pe layere cadastrale uzuale:
    CLADIRI, CONSTRUCTII, IMOBIL, DETALII, 2D_CLADIRI, CAD_C1, etc.
  - Reconstrucție automată de poligoane închise din entități LINE / LWPOLYLINE.
"""

import os
import sys
from typing import List, Dict, Any, Optional
import ezdxf
from shapely.geometry import Polygon, LineString, MultiPolygon
from shapely.ops import polygonize, unary_union
import geopandas as gpd

CADASTRAL_LAYER_KEYWORDS = [
    "CLADIR", "CONSTR", "IMOBIL", "CAD", "CORP", "C1", "C2", "DETAL", "TOPO", "HOUSE", "BLDG"
]

def import_dxf_ground_truth(
    dxf_path: str,
    output_geojson: Optional[str] = None,
    layer_filter: Optional[List[str]] = None,
    min_area_m2: float = 8.0
) -> gpd.GeoDataFrame:
    """
    Încarcă un fișier DXF (Tier 1 TopoLT / RTK) și extrage contururile clădirilor în Stereo 70.
    """
    if not os.path.exists(dxf_path):
        raise FileNotFoundError(f"Fișierul DXF nu a fost găsit la: {dxf_path}")

    doc = ezdxf.readfile(dxf_path)
    msp = doc.modelspace()

    lines = []
    direct_polys = []

    for entity in msp:
        layer_name = entity.dxf.layer.upper()
        if layer_filter:
            if not any(lf.upper() in layer_name for lf in layer_filter):
                continue
        else:
            # Auto-detect layer keywords if no filter specified
            if not any(kw in layer_name for kw in CADASTRAL_LAYER_KEYWORDS):
                continue

        etype = entity.dxftype()
        if etype == "LWPOLYLINE":
            pts = [(p[0], p[1]) for p in entity.get_points("xy")]
            if len(pts) >= 3 and entity.is_closed:
                p = Polygon(pts)
                if p.is_valid and p.area >= min_area_m2:
                    direct_polys.append(p)
            elif len(pts) >= 2:
                lines.append(LineString(pts))
        elif etype == "POLYLINE":
            pts = [(p.dxf.location.x, p.dxf.location.y) for p in entity.vertices]
            if len(pts) >= 3 and entity.is_closed:
                p = Polygon(pts)
                if p.is_valid and p.area >= min_area_m2:
                    direct_polys.append(p)
            elif len(pts) >= 2:
                lines.append(LineString(pts))
        elif etype == "LINE":
            p1 = (entity.dxf.start.x, entity.dxf.start.y)
            p2 = (entity.dxf.end.x, entity.dxf.end.y)
            lines.append(LineString([p1, p2]))

    # Reconstruim poligoane din linii disparate
    if lines:
        reconstructed = list(polygonize(lines))
        for poly in reconstructed:
            if poly.is_valid and poly.area >= min_area_m2:
                direct_polys.append(poly)

    if not direct_polys:
        # Fallback: scan all layers if strict keywords yielded nothing
        print("   [Avertisment] Nicio clădire găsită pe layerele standard. Scanăm toate entitățile închise...")
        for entity in msp:
            if entity.dxftype() == "LWPOLYLINE" and entity.is_closed:
                pts = [(p[0], p[1]) for p in entity.get_points("xy")]
                if len(pts) >= 3:
                    p = Polygon(pts)
                    if p.is_valid and p.area >= min_area_m2:
                        direct_polys.append(p)

    # Curățare și agregare în GeoDataFrame
    clean_polys = []
    for p in direct_polys:
        if p.is_valid and p.area >= min_area_m2:
            clean_polys.append(p)

    gdf = gpd.GeoDataFrame(
        [{"id": f"REF_TIER1_{i+1:03d}", "survey_source": "TOPO_CAD_DXF", "area_m2": round(p.area, 2), "geometry": p}
         for i, p in enumerate(clean_polys)],
        crs="EPSG:3844"
    )

    if output_geojson:
        os.makedirs(os.path.dirname(output_geojson), exist_ok=True)
        gdf.to_file(output_geojson, driver="GeoJSON")
        print(f"[+] Salvat {len(gdf)} corpuri de clădire de referință în: {output_geojson}")

    return gdf


if __name__ == "__main__":
    if len(sys.argv) > 1:
        dxf_file = sys.argv[1]
        out_file = sys.argv[2] if len(sys.argv) > 2 else "data/ground_truth/tier1_survey_cadastre.geojson"
        import_dxf_ground_truth(dxf_file, out_file)
    else:
        print("Utilizare: python tools/import_tier1_cad.py <cale_fisier.dxf> [iesire.geojson]")
