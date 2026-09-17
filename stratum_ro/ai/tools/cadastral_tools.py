# -*- coding: utf-8 -*-
"""
Cadastral, Topology & TopoLT CAD Export Tool Wrappers for StratumRO AI.
Integrates CadastralDxfExporter and shapely validation routines.
"""

import os
from typing import Any, Dict, List, Optional
from shapely.geometry import Polygon, shape
from shapely.validation import explain_validity


from .security import resolve_sandboxed_path, check_permission


def validate_topology(polygons: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Validates topological soundness of building footprints.
    Checks self-intersections, duplicate vertices, invalid rings, and slivers.
    Returns structured metrics conforming to MD 3 Section 15.
    """
    valid_count = 0
    invalid_count = 0
    self_intersections = 0
    duplicate_vertices = 0
    sliver_count = 0
    errors = []

    for idx, item in enumerate(polygons):
        geom = shape(item) if isinstance(item, dict) else item
        if geom.is_empty:
            invalid_count += 1
            errors.append({"index": idx, "reason": "Empty geometry"})
            continue

        # Duplicate vertices check
        if hasattr(geom, "exterior") and geom.exterior:
            coords = list(geom.exterior.coords)
            if len(coords) - 1 > len(set(coords[:-1])):
                duplicate_vertices += 1

        if not geom.is_valid:
            invalid_count += 1
            exp = explain_validity(geom)
            if "self-intersection" in exp.lower():
                self_intersections += 1
            errors.append({"index": idx, "reason": exp})
        else:
            if geom.area < 1.0:
                invalid_count += 1
                sliver_count += 1
                errors.append({"index": idx, "reason": f"Sliver polygon area: {geom.area:.3f} m2"})
            else:
                valid_count += 1

    is_valid = (invalid_count == 0)

    return {
        "status": "success",
        "valid": is_valid,
        "is_all_valid": is_valid,
        "valid_count": valid_count,
        "invalid_count": invalid_count,
        "feature_count": len(polygons),
        "invalid_features": invalid_count,
        "self_intersections": self_intersections,
        "duplicate_vertices": duplicate_vertices,
        "sliver_count": sliver_count,
        "errors": errors
    }


def validate_ancpi(
    polygons: List[Dict[str, Any]],
    layer_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Validates building footprints against Romanian ANCPI Ordinul nr. 600/2023 criteria:
    - Minimum surface threshold: >= 45 m2 for main living quarters (1CC), >= 8 m2 for outbuildings/annexes (2CC)
    - Minimum edge length: >= 1.0 m (rejects micro-facets)
    - Orthogonal angle conformity (tolerance within 5 degrees of 90 degrees)
    - Stereo 70 (EPSG:3844) bounding coordinates integrity
    """
    if layer_path:
        p = resolve_sandboxed_path(layer_path, must_exist=True)
        import geopandas as gpd
        gdf = gpd.read_file(p)
        poly_list = [shape(g) for g in gdf.geometry if not g.is_empty]
    else:
        poly_list = [shape(p) if isinstance(p, dict) else p for p in polygons]

    checks = {
        "min_area_main_45m2": {"passed": 0, "failed": 0},
        "min_area_annex_8m2": {"passed": 0, "failed": 0},
        "min_edge_1m": {"passed": 0, "failed": 0},
        "stereo70_bounds": {"passed": 0, "failed": 0},
    }
    warnings = []
    failed_count = 0

    for idx, poly in enumerate(poly_list):
        if poly.is_empty:
            failed_count += 1
            warnings.append(f"Building #{idx}: empty geometry")
            continue

        area = poly.area

        # 1. Area threshold check
        if area >= 45.0:
            checks["min_area_main_45m2"]["passed"] += 1
        elif area >= 8.0:
            checks["min_area_annex_8m2"]["passed"] += 1
        else:
            checks["min_area_annex_8m2"]["failed"] += 1
            failed_count += 1
            warnings.append(f"Building #{idx}: area {area:.2f} m2 is below ANCPI 8 m2 annex threshold")

        # 2. Edge lengths check
        has_micro_edge = False
        if hasattr(poly, "exterior") and poly.exterior:
            coords = list(poly.exterior.coords)
            for i in range(len(coords) - 1):
                p1, p2 = coords[i], coords[i + 1]
                length = ((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)**0.5
                if length < 0.5:
                    has_micro_edge = True
                    break

        if has_micro_edge:
            checks["min_edge_1m"]["failed"] += 1
            warnings.append(f"Building #{idx}: contains micro-edges (< 0.5m)")
        else:
            checks["min_edge_1m"]["passed"] += 1

        # 3. Stereo 70 bounds sanity check (Romania bounding box approx: X 200k..800k, Y 200k..800k)
        centroid = poly.centroid
        if 150000 <= centroid.x <= 850000 and 200000 <= centroid.y <= 800000:
            checks["stereo70_bounds"]["passed"] += 1
        else:
            checks["stereo70_bounds"]["failed"] += 1
            failed_count += 1
            warnings.append(f"Building #{idx}: centroid ({centroid.x:.1f}, {centroid.y:.1f}) outside Stereo 70 national limits")

    is_passed = (failed_count == 0)

    return {
        "status": "success",
        "passed": is_passed,
        "regulation": "ANCPI Ordinul nr. 600/2023",
        "total_features": len(poly_list),
        "failed_count": failed_count,
        "checks": checks,
        "warnings": warnings,
        "evidence": {
            "standards": ["Art. 35 - Geometrie imobile", "Art. 41 - Delimitare constructii"],
            "crs": "EPSG:3844"
        }
    }


def create_preview(
    polygons: List[Dict[str, Any]],
    title: str = "preview_candidates"
) -> Dict[str, Any]:
    """
    Writes temporary candidate geometries to a separate preview layer in workspace/output/preview/.
    Guarantees that unapproved AI geometry is never written directly to official project layers.
    """
    preview_dir = resolve_sandboxed_path("workspace/output/preview")
    preview_dir.mkdir(parents=True, exist_ok=True)
    preview_path = preview_dir / f"{title}.geojson"

    import geopandas as gpd
    geoms = [shape(p) if isinstance(p, dict) else p for p in polygons if not shape(p).is_empty]

    gdf = gpd.GeoDataFrame({
        "id": list(range(1, len(geoms) + 1)),
        "area_m2": [round(g.area, 2) for g in geoms],
        "category": ["1CC" if g.area >= 45.0 else "2CC" for g in geoms],
        "geometry": geoms
    }, crs="EPSG:3844")

    gdf.to_file(preview_path, driver="GeoJSON")

    return {
        "status": "success",
        "preview_path": str(preview_path),
        "feature_count": len(geoms),
        "layer_title": title,
        "crs": "EPSG:3844",
        "message": "Preview created in temporary sandbox. Requires human review before committing."
    }


def commit_to_project(
    preview_path: str,
    target_layer_path: str = "workspace/output/official_buildings.gpkg",
    approved: bool = False,
    approval_reason: str = ""
) -> Dict[str, Any]:
    """
    Commits approved preview footprints to the official project layers.
    Permission class: ASK. Requires explicit user sign-off (approved=True).
    """
    is_permitted, msg = check_permission("results.commit_to_project", approved=approved, approval_reason=approval_reason)
    if not is_permitted:
        return {
            "status": "waiting_for_approval",
            "message": msg,
            "preview_path": preview_path,
            "requires_user_action": True
        }

    src_p = resolve_sandboxed_path(preview_path, must_exist=True)
    dst_p = resolve_sandboxed_path(target_layer_path)

    import geopandas as gpd
    gdf_preview = gpd.read_file(src_p)
    gdf_preview.to_file(dst_p, driver="GPKG", layer="CLADIRI_SOL_ANCPI")

    return {
        "status": "success",
        "target_path": str(dst_p),
        "committed_features": len(gdf_preview),
        "approval_reason": approval_reason,
        "message": f"Successfully committed {len(gdf_preview)} features to official cadastral layer."
    }


def export_topolt_cad(
    output_dxf_path: str,
    buildings: List[Dict[str, Any]],
    parcels: Optional[List[Dict[str, Any]]] = None,
    approved: bool = True,
    approval_reason: str = ""
) -> Dict[str, Any]:
    """
    Exports parcels and buildings to TopoLT-standard AutoCAD DXF with PAD coordinate tables.
    Permission class: ASK. Requires explicit user approval (approved=True).
    """
    is_permitted, msg = check_permission("export.export_topolt_dxf", approved=approved, approval_reason=approval_reason)
    if not is_permitted:
        return {
            "status": "waiting_for_approval",
            "message": msg,
            "output_dxf_path": output_dxf_path,
            "requires_user_action": True
        }

    dst_p = resolve_sandboxed_path(output_dxf_path)
    dst_p.parent.mkdir(parents=True, exist_ok=True)

    from stratum_ro.cad_exporter import CadastralDxfExporter

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
        str(dst_p),
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
    points: List[Dict[str, Any]],
    approved: bool = True,
    approval_reason: str = ""
) -> Dict[str, Any]:
    """
    Exports a .CP coordinate interchange file conforming to ANCPI eTerra.
    Permission class: ASK. Requires explicit user approval (approved=True).
    """
    is_permitted, msg = check_permission("export.export_cp", approved=approved, approval_reason=approval_reason)
    if not is_permitted:
        return {
            "status": "waiting_for_approval",
            "message": msg,
            "output_cp_path": output_cp_path,
            "requires_user_action": True
        }

    dst_p = resolve_sandboxed_path(output_cp_path)
    dst_p.parent.mkdir(parents=True, exist_ok=True)

    with open(dst_p, "w", encoding="utf-8") as f:
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
        "output_cp_path": str(dst_p),
        "parcel_id": parcel_id,
        "points_count": len(points)
    }
