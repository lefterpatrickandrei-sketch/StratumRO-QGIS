# -*- coding: utf-8 -*-
"""
StratumRO Mask Fusion & Vector Cleanup
======================================
Handles multi-wing building assembly, overlapping mask fusion, and raw vector cleanup.

Transforms:
RAW MASK -> RAW VECTOR -> CLEAN VECTOR
without obscuring AI delineation performance.
"""

import numpy as np
from shapely.geometry import Polygon, MultiPolygon
from shapely.ops import unary_union
from shapely.validation import make_valid
import geopandas as gpd


class MaskFusionEngine:
    """
    Fuses adjacent or overlapping building segments into cohesive physical building footprints.
    """

    def __init__(self, iou_merge_threshold: float = 0.25, snap_distance_m: float = 0.60):
        self.iou_merge_threshold = iou_merge_threshold
        self.snap_distance_m = snap_distance_m

    def clean_raw_vector(
        self,
        geom,
        min_area_m2: float = 15.0,
        simplify_tol_m: float = 0.25,
        remove_small_holes_m2: float = 12.0
    ):
        """
        Cleans raster staircase artifacts and sliver holes from a raw vectorized polygon.

        Parameters
        ----------
        geom : shapely.geometry.Polygon or MultiPolygon
            Raw vector geometry.
        min_area_m2 : float
            Minimum allowable area.
        simplify_tol_m : float
            Douglas-Peucker tolerance for raster step reduction (0.25m ~ 1-1.25 pixels).
        remove_small_holes_m2 : float
            Holes smaller than this threshold are filled.

        Returns
        -------
        Polygon or None
        """
        if geom is None or geom.is_empty:
            return None

        valid_geom = make_valid(geom)
        if isinstance(valid_geom, MultiPolygon):
            valid_geom = max(valid_geom.geoms, key=lambda p: p.area)

        if valid_geom.area < min_area_m2:
            return None

        # 1. Fill small artifact holes (e.g. 1-2 pixel voids from ventilation shafts/HVAC)
        cleaned_holes = []
        for interior in valid_geom.interiors:
            hole_poly = Polygon(interior)
            if hole_poly.area >= remove_small_holes_m2:
                cleaned_holes.append(interior)

        poly_filled = Polygon(valid_geom.exterior, cleaned_holes)

        # 2. Douglas-Peucker simplification to eliminate 0.2m raster staircase noise
        if simplify_tol_m > 0:
            simplified = poly_filled.simplify(simplify_tol_m, preserve_topology=True)
            if simplified.is_valid and not simplified.is_empty and simplified.area >= min_area_m2:
                poly_filled = simplified

        if isinstance(poly_filled, MultiPolygon):
            poly_filled = max(poly_filled.geoms, key=lambda p: p.area)

        return poly_filled

    def fuse_overlapping_predictions(self, pred_list: list, crs="EPSG:3844") -> list:
        """
        Merges overlapping building predictions (e.g., separate wings of the same facility).

        Parameters
        ----------
        pred_list : list of dict
            List of prediction dictionaries with 'geometry', 'pred_id', 'sam2_score', etc.

        Returns
        -------
        list of dict
            Fused prediction records.
        """
        if not pred_list:
            return []

        gdf = gpd.GeoDataFrame(pred_list, crs=crs)
        geoms = list(gdf.geometry)
        n = len(geoms)

        # Build adjacency graph
        merged_groups = []
        visited = set()

        for i in range(n):
            if i in visited:
                continue
            current_group = [i]
            visited.add(i)

            # Check overlaps with all remaining unvisited polygons
            for j in range(i + 1, n):
                if j in visited:
                    continue
                gi = geoms[i]
                gj = geoms[j]
                if gi.intersects(gj):
                    inter_area = gi.intersection(gj).area
                    union_area = gi.union(gj).area
                    iou = inter_area / union_area if union_area > 0 else 0
                    # Merge if significant overlap or adjacent touching
                    if iou >= self.iou_merge_threshold or inter_area > 20.0:
                        current_group.append(j)
                        visited.add(j)

            merged_groups.append(current_group)

        fused_records = []
        for g_idx, group in enumerate(merged_groups):
            if len(group) == 1:
                rec = dict(pred_list[group[0]])
                rec["pred_id"] = f"FUSED_{len(fused_records)+1:03d}"
                rec["fused_from_count"] = 1
                fused_records.append(rec)
            else:
                # Merge multiple polygons
                group_geoms = [geoms[idx] for idx in group]
                union_geom = unary_union(group_geoms)
                clean_geom = self.clean_raw_vector(union_geom)

                if clean_geom is not None and not clean_geom.is_empty:
                    base_rec = pred_list[group[0]]
                    scores = [pred_list[idx].get("sam2_score", 0.0) for idx in group]
                    fused_records.append({
                        "pred_id": f"FUSED_{len(fused_records)+1:03d}",
                        "cand_id": "+".join([pred_list[idx].get("cand_id", "") for idx in group]),
                        "sam2_score": float(np.mean(scores)),
                        "mean_height_m": float(np.mean([pred_list[idx].get("mean_height_m", 0.0) for idx in group])),
                        "max_height_m": float(np.max([pred_list[idx].get("max_height_m", 0.0) for idx in group])),
                        "raw_area_m2": float(clean_geom.area),
                        "raw_vertex_count": len(clean_geom.exterior.coords) - 1,
                        "fused_from_count": len(group),
                        "geometry": clean_geom
                    })

        return fused_records
