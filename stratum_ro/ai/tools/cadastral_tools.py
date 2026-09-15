# -*- coding: utf-8 -*-
"""
Cadastral, Topology & TopoLT CAD Export Tool Wrappers for StratumRO AI.
Integrates CadastralDxfExporter and shapely validation routines.
"""

import os
from typing import Any, Dict, List, Optional
from shapely.geometry import Polygon, shape
from shapely.validation import explain_validity


def validate_topology(polygons: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Validates topological soundness of building footprints.
    Checks self-intersections, duplicate vertices, invalid rings, and slivers.
    """
    valid_count = 0
    invalid_count = 0
    errors = []

    for idx, item in enumerate(polygons):
        geom = shape(item) if isinstance(item, dict) else item
        if geom.is_empty:
            invalid_count += 1
            errors.append({"index": idx, "reason": "Empty geometry"})
            continue

        if not geom.is_valid:
            invalid_count += 1
            errors.append({"index": idx, "reason": explain_validity(geom)})
        else:
            if geom.area < 1.0:
                invalid_count += 1
                errors.append({"index": idx, "reason": f"Sliver polygon area: {geom.area:.3f} m2"})
            else:
                valid_count += 1

    return {
        "status": "success",
        "total_checked": len(polygons),
        "valid_count": valid_count,
        "invalid_count": invalid_count,
        "is_all_valid": invalid_count == 0,
        "errors": errors
    }


def export_topolt_cad(
    output_dxf_path: str,
    buildings: List[Dict[str, Any]],
    parcels: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Exports parcels and buildings to TopoLT-standard AutoCAD DXF with PAD coordinate tables.
    """
    from stratum_ro.cad_exporter import CadastralDxfExporter

    os.makedirs(os.path.dirname(os.path.abspath(output_dxf_path)), exist_ok=True)
    exporter = CadastralDxfExporter(dxf_version="R2010")

    b_shapes = [
        {"id": idx + 1, "geometry": shape(b), "area_m2": round(shape(b).area, 2)}
        for idx, b in enumerate(buildings) if not shape(b).is_empty
    ]
    p_shapes = [
        {"id": idx + 1, "geometry": shape(p), "area_m2": round(shape(p).area, 2)}
        for idx, p in enumerate(parcels or []) if not shape(p).is_empty
    ]

    cat_dict = {
        "CLADIRI_PRINCIPALE": b_shapes,
        "ANEXE_GOSPODARESTI": p_shapes
    }

    res_path = exporter.export_multicategory_to_dxf(
        cat_dict,
        output_dxf_path,
        include_labels=True,
        topolt_mode=True,
        draw_pad_table=True
    )

    file_size_kb = round(os.path.getsize(res_path) / 1024.0, 1)

    return {
        "status": "success",
        "output_dxf_path": res_path,
        "file_size_kb": file_size_kb,
        "buildings_exported": len(b_shapes),
        "parcels_exported": len(p_shapes),
        "layers_created": ["1CC", "2CC", "VARFURI", "NUMERE_PCT", "TABEL_PAD"]
    }


def export_cp_file(
    output_cp_path: str,
    parcel_id: str,
    points: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Exports a .CP coordinate interchange file conforming to ANCPI eTerra.
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_cp_path)), exist_ok=True)

    with open(output_cp_path, "w", encoding="utf-8") as f:
        f.write(f"; StratumRO eTerra .CP Export - Imobil {parcel_id}\n")
        f.write("; NrPct, X_Stereo70, Y_Stereo70, Cota_Z\n")
        for pt in points:
            nr = pt.get("nr", 1)
            x = pt.get("x", 0.0)
            y = pt.get("y", 0.0)
            z = pt.get("z", 0.0)
            f.write(f"{nr},{x:.3f},{y:.3f},{z:.3f}\n")

    return {
        "status": "success",
        "output_cp_path": output_cp_path,
        "parcel_id": parcel_id,
        "points_count": len(points)
    }
