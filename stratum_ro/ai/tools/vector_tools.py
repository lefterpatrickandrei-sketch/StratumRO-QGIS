# -*- coding: utf-8 -*-
"""
Vectorization, Regularization & Partitioning Tool Wrappers for StratumRO AI.
Integrates CadastralVectorizer, 90° orthogonal regularization, eave retraction,
and ANCPI planar partitioning.
"""

from typing import Any, Dict, List
from shapely.geometry import Polygon, shape, mapping


def regularize_footprints(
    polygons: List[Dict[str, Any]],
    tolerance: float = 0.5,
    mrr_trigger: float = 0.70,
    **kwargs
) -> Dict[str, Any]:
    """
    Applies 90° canonical minimum rotated rectangle (MRR) or adaptive regularization.
    """
    from stratum_ro.vectorizer import CadastralVectorizer

    vectorizer = CadastralVectorizer(crs="EPSG:3844")
    regularized = []
    canonical_count = 0

    for item in polygons:
        geom = shape(item) if isinstance(item, dict) else item
        if not geom.is_valid or geom.is_empty:
            geom = geom.buffer(0)

        reg_geom = vectorizer.orthogonalize_polygon(geom, tolerance=tolerance)
        coords = list(reg_geom.exterior.coords)[:-1] if hasattr(reg_geom, "exterior") else []
        if len(coords) == 4:
            canonical_count += 1
        regularized.append(mapping(reg_geom))

    return {
        "status": "success",
        "total_polygons": len(polygons),
        "canonical_rectangles_count": canonical_count,
        "polygons": regularized
    }


def apply_eave_offset(
    polygons: List[Dict[str, Any]],
    offset_m: float = -0.40
) -> Dict[str, Any]:
    """
    Applies eave retraction offset (default -0.40m) to convert roofline polygons
    to ANCPI ground footprints (CLADIRI_SOL_ANCPI).
    """
    offsetted = []
    for item in polygons:
        geom = shape(item) if isinstance(item, dict) else item
        buffered = geom.buffer(offset_m, join_style=2)  # MITRE join style
        if not buffered.is_empty:
            offsetted.append(mapping(buffered))
        else:
            offsetted.append(mapping(geom))

    return {
        "status": "success",
        "offset_applied_m": offset_m,
        "total_processed": len(polygons),
        "polygons": offsetted
    }


def create_planar_partition(
    buildings: List[Dict[str, Any]],
    sector_boundary: Dict[str, Any],
    simplification_m: float = 12.0
) -> Dict[str, Any]:
    """
    Calculates a continuous 100% planar partition without gaps or overlaps.
    """
    from shapely.ops import unary_union

    b_geoms = [shape(b) for b in buildings if not shape(b).is_empty]
    b_union = unary_union(b_geoms) if b_geoms else Polygon()
    boundary_geom = shape(sector_boundary)

    unclassified_land = boundary_geom.difference(b_union)

    return {
        "status": "success",
        "buildings_area_m2": round(b_union.area, 2),
        "unclassified_area_m2": round(unclassified_land.area, 2),
        "total_sector_area_m2": round(boundary_geom.area, 2),
        "unclassified_geometry": mapping(unclassified_land) if not unclassified_land.is_empty else None
    }


def export_gpkg_layer(
    output_gpkg_path: str,
    polygons: List[Dict[str, Any]],
    layer_name: str = "CLADIRI_SOL_ANCPI",
    crs: str = "EPSG:3844"
) -> Dict[str, Any]:
    """
    Exports building polygons to an official OGC GeoPackage (.gpkg) layer in Stereo 70 (EPSG:3844).
    """
    from .security import resolve_sandboxed_path
    import geopandas as gpd

    dst_p = resolve_sandboxed_path(output_gpkg_path)
    geoms = [shape(p) if isinstance(p, dict) else p for p in polygons if not shape(p).is_empty]

    gdf = gpd.GeoDataFrame({
        "id": list(range(1, len(geoms) + 1)),
        "area_m2": [round(g.area, 2) for g in geoms],
        "category": ["1CC" if g.area >= 45.0 else "2CC" for g in geoms],
        "geometry": geoms
    }, crs=crs)

    gdf.to_file(dst_p, driver="GPKG", layer=layer_name)

    return {
        "status": "success",
        "output_gpkg_path": str(dst_p),
        "layer_name": layer_name,
        "features_written": len(geoms),
        "crs": crs
    }


def export_cityjson_lod1(
    output_cityjson_path: str,
    buildings: List[Dict[str, Any]],
    default_ground_z: float = 345.0,
    epsg_code: int = 3844
) -> Dict[str, Any]:
    """
    Exports 3D LoD1 solid building shells to OGC CityJSON v1.1.
    """
    from .security import resolve_sandboxed_path
    from stratum_ro.volumetric_3d import Volumetric3DBuilder

    dst_p = resolve_sandboxed_path(output_cityjson_path)
    builder = Volumetric3DBuilder(default_ground_z=default_ground_z)

    # Format buildings for CityJSON
    lod1_input = []
    for idx, b in enumerate(buildings):
        geom = shape(b) if isinstance(b, dict) else b
        lod1_input.append({
            "id": f"building_{idx + 1}",
            "geometry": geom,
            "ground_z": default_ground_z,
            "height_m": 6.5,
            "roof_z": default_ground_z + 6.5,
            "category": "1CC"
        })

    out_path = builder.export_cityjson(lod1_input, str(dst_p), epsg_code=epsg_code)

    return {
        "status": "success",
        "output_cityjson_path": out_path,
        "buildings_count": len(lod1_input),
        "epsg": epsg_code
    }

