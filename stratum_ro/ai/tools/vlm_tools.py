# -*- coding: utf-8 -*-
"""
StratumRO AI Tools — VLM Building Verification & Audit Tools.
Wraps VLMVerifier for execution within the Antigravity Task Graph and MCP server.
"""

import os
from typing import Any, Dict, List, Optional
from shapely import wkt
from shapely.geometry import shape, Polygon

from stratum_ro.ai.vlm_verifier import VLMVerifier, VLMVerificationResult


def vlm_verify_single_building_tool(
    geometry_wkt: str,
    ortho_path: str,
    building_id: str = "bldg_0",
    ndsm_height_m: Optional[float] = None
) -> Dict[str, Any]:
    """
    Validates a single building geometry candidate against orthophoto imagery using VLM.
    """
    try:
        geom = wkt.loads(geometry_wkt)
    except Exception as e:
        return {
            "status": "error",
            "message": f"Invalid WKT geometry: {e}",
            "building_id": building_id,
            "verdict": "REJECTED"
        }

    verifier = VLMVerifier()
    res = verifier.verify_building(
        polygon=geom,
        ortho_path=ortho_path,
        building_id=building_id,
        ndsm_height_m=ndsm_height_m
    )
    return {
        "status": "success",
        "result": res.to_dict()
    }


def vlm_batch_audit_layer_tool(
    gpkg_path: str,
    layer_name: str,
    ortho_path: str,
    max_buildings: Optional[int] = 50,
    ndsm_tif_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Runs VLM audit across building footprints in a GeoPackage layer.
    Classifies ANCPI typology (1CC/2CC) and flags false positives.
    """
    if not os.path.exists(gpkg_path):
        return {"status": "error", "message": f"GeoPackage not found: {gpkg_path}"}
    if not os.path.exists(ortho_path):
        return {"status": "error", "message": f"Orthophoto not found: {ortho_path}"}

    verifier = VLMVerifier()
    summary = verifier.batch_verify_footprints(
        gpkg_path=gpkg_path,
        layer_name=layer_name,
        ortho_path=ortho_path,
        max_buildings=max_buildings,
        ndsm_tif_path=ndsm_tif_path
    )
    return summary


def vlm_filter_false_positives_tool(
    input_gpkg: str,
    input_layer: str,
    output_gpkg: str,
    output_layer: str,
    ortho_path: str,
    max_buildings: Optional[int] = None
) -> Dict[str, Any]:
    """
    Filters out false positive features using VLM verification and saves
    the approved and review-needed buildings to a new layer with ANCPI attributes.
    """
    import geopandas as gpd

    if not os.path.exists(input_gpkg):
        return {"status": "error", "message": f"Input file not found: {input_gpkg}"}

    gdf = gpd.read_file(input_gpkg, layer=input_layer)
    if max_buildings:
        gdf = gdf.iloc[:max_buildings]

    verifier = VLMVerifier()
    verdicts = []
    codes = []
    confs = []
    reasons = []

    for idx, row in gdf.iterrows():
        b_id = f"bldg_{row.get('fid', idx)}"
        v_res = verifier.verify_building(
            polygon=row.geometry,
            ortho_path=ortho_path,
            building_id=b_id
        )
        verdicts.append(v_res.verdict)
        codes.append(v_res.ancpi_code)
        confs.append(v_res.confidence)
        reasons.append(v_res.reasoning)

    gdf["vlm_verdict"] = verdicts
    gdf["vlm_ancpi"] = codes
    gdf["vlm_conf"] = confs
    gdf["vlm_reason"] = reasons

    # Filter out rejected
    filtered = gdf[gdf["vlm_verdict"] != "REJECTED"].copy()

    filtered.to_file(output_gpkg, layer=output_layer, driver="GPKG")

    return {
        "status": "success",
        "input_count": len(gdf),
        "output_count": len(filtered),
        "rejected_count": len(gdf) - len(filtered),
        "output_path": output_gpkg,
        "output_layer": output_layer
    }
