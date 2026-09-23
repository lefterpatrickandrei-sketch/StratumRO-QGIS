# -*- coding: utf-8 -*-
"""
StratumRO — LiDAR 3D Quality Gate & Multi-Factor Confidence Scoring
===================================================================
Elevates LiDAR from a passive input filter to an active 3D arbitrator:
  1. Transversal facade height step verification (wall drop ΔZ >= 1.8m).
  2. Roof elevation consistency and planar dispersion (sigma_roof).
  3. Overhanging tree canopy detection on roof edges.
  4. Composite 5-factor confidence score (0.0 to 1.0) with operational traffic-light thresholds:
     - 🟢 VERDE (>= 0.85): Automatically approved for pre-cadastre.
     - 🟡 GALBEN (0.65 - 0.85): Inspection required by surveyor (calcan, complex roof).
     - 🔴 ROSU (< 0.65): Rejected artifact (vehicle, noise, transient ground object).
"""

import math
import numpy as np
from typing import Dict, Any, Optional, Tuple, List
from shapely.geometry import Polygon, Point, LineString
import rasterio
from rasterio.features import rasterize


class LidarQualityGate:
    """
    Active 3D quality auditor that cross-examines 2D optical footprints
    against continuous altimetric LiDAR nDSM elevation models.
    """

    def __init__(
        self,
        min_wall_drop_m: float = 1.8,
        min_bldg_height_m: float = 2.5
    ):
        self.min_wall_drop = float(min_wall_drop_m)
        self.min_bldg_height = float(min_bldg_height_m)

    @staticmethod
    def _sample_raster(array: np.ndarray, transform: rasterio.Affine, x: float, y: float) -> Optional[float]:
        """Samples a single float value from raster at world coordinates (x, y)."""
        inv_tr = ~transform
        col, row = inv_tr * (x, y)
        c, r = int(round(col)), int(round(row))
        if 0 <= r < array.shape[0] and 0 <= c < array.shape[1]:
            val = float(array[r, c])
            return val if not np.isnan(val) else 0.0
        return None

    def evaluate_facade_height_steps(
        self,
        poly: Polygon,
        ndsm_array: np.ndarray,
        transform: rasterio.Affine,
        sample_step_m: float = 0.50
    ) -> Dict[str, Any]:
        """
        Samples elevation perpendicularly across each facade edge:
        interior point (+0.5m inside) vs. exterior point (-0.5m outside).
        A physical building wall exhibits a sharp altitude drop (ΔZ >= 1.8m).
        """
        if poly is None or not poly.is_valid or poly.is_empty:
            return {"step_valid_ratio": 0.0, "mean_step_m": 0.0, "total_sampled_edges": 0}

        coords = list(poly.exterior.coords)[:-1]
        n = len(coords)
        if n < 3:
            return {"step_valid_ratio": 0.0, "mean_step_m": 0.0, "total_sampled_edges": 0}

        valid_edge_len = 0.0
        total_edge_len = 0.0
        sampled_steps = []

        for i in range(n):
            p1 = np.array(coords[i])
            p2 = np.array(coords[(i + 1) % n])
            edge_vec = p2 - p1
            edge_len = float(np.linalg.norm(edge_vec))
            if edge_len < 0.4:
                continue

            total_edge_len += edge_len
            # Normal pointing outward (for counter-clockwise polygon)
            # vector (dx, dy) -> outward normal (dy, -dx)
            norm_vec = np.array([edge_vec[1], -edge_vec[0]]) / edge_len

            # Midpoint of edge
            mid_pt = (p1 + p2) * 0.5

            # Sample internal (+0.5m) and external (-0.5m) points
            # For counter-clockwise orientation, normal points outward (+norm = outside, -norm = inside)
            pt_out = mid_pt + norm_vec * sample_step_m
            pt_in = mid_pt - norm_vec * sample_step_m

            # Verify that pt_in is genuinely inside the polygon
            if not poly.contains(Point(pt_in[0], pt_in[1])):
                # Try flipped orientation
                pt_out, pt_in = pt_in, pt_out

            z_in = self._sample_raster(ndsm_array, transform, pt_in[0], pt_in[1])
            z_out = self._sample_raster(ndsm_array, transform, pt_out[0], pt_out[1])

            if z_in is not None and z_out is not None:
                step = z_in - z_out
                sampled_steps.append(step)
                if step >= self.min_wall_drop:
                    valid_edge_len += edge_len

        ratio = float(valid_edge_len / total_edge_len) if total_edge_len > 0 else 0.0
        mean_step = float(np.mean(sampled_steps)) if sampled_steps else 0.0

        return {
            "step_valid_ratio": round(ratio, 3),
            "mean_step_m": round(mean_step, 2),
            "total_sampled_edges": len(sampled_steps)
        }

    def evaluate_roof_coplanarity(
        self,
        poly: Polygon,
        ndsm_array: np.ndarray,
        transform: rasterio.Affine
    ) -> Dict[str, Any]:
        """
        Extracts all nDSM pixel heights inside the footprint to assess roof
        planarity, average height, and presence of tree canopy roughness.
        """
        if poly is None or not poly.is_valid or poly.is_empty or poly.area < 4.0:
            return {"mean_h": 0.0, "max_h": 0.0, "std_roof": 0.0, "h_coverage_ratio": 0.0}

        minx, miny, maxx, maxy = poly.bounds
        inv_tr = ~transform
        c_min, r_max = inv_tr * (minx, miny)
        c_max, r_min = inv_tr * (maxx, maxy)

        r0 = max(0, int(np.floor(min(r_min, r_max))) - 1)
        r1 = min(ndsm_array.shape[0], int(np.ceil(max(r_min, r_max))) + 2)
        c0 = max(0, int(np.floor(min(c_min, c_max))) - 1)
        c1 = min(ndsm_array.shape[1], int(np.ceil(max(c_min, c_max))) + 2)

        if r1 <= r0 or c1 <= c0:
            return {"mean_h": 0.0, "max_h": 0.0, "std_roof": 0.0, "h_coverage_ratio": 0.0}

        sub_ndsm = ndsm_array[r0:r1, c0:c1]
        sub_transform = transform * rasterio.Affine.translation(c0, r0)

        # Rasterize polygon to sub-window
        mask = rasterize(
            [(poly, 1)],
            out_shape=sub_ndsm.shape,
            transform=sub_transform,
            fill=0,
            dtype=np.uint8
        )

        bldg_pixels = sub_ndsm[mask == 1]
        if len(bldg_pixels) == 0:
            return {"mean_h": 0.0, "max_h": 0.0, "std_roof": 0.0, "h_coverage_ratio": 0.0}

        mean_h = float(np.mean(bldg_pixels))
        max_h = float(np.max(bldg_pixels))
        std_roof = float(np.std(bldg_pixels))
        h_coverage = float(np.sum(bldg_pixels >= self.min_bldg_height) / len(bldg_pixels))

        return {
            "mean_h": round(mean_h, 2),
            "max_h": round(max_h, 2),
            "std_roof": round(std_roof, 2),
            "h_coverage_ratio": round(h_coverage, 3)
        }

    def compute_composite_confidence(
        self,
        poly: Polygon,
        sam2_score: float,
        ndsm_array: Optional[np.ndarray] = None,
        transform: Optional[rasterio.Affine] = None,
        ortho_contrast: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Calculates the multi-factor cadastral confidence score C_final:
          C_final = 0.20*C_SAM + 0.30*C_LiDAR + 0.20*C_Ortho + 0.15*C_Geom + 0.15*C_Bound
        """
        if poly is None or not poly.is_valid or poly.is_empty:
            return {
                "conf_final": 0.0,
                "action_code": "ROSU_RESPINS_ARTEFACT",
                "c_sam": 0.0,
                "c_lidar": 0.0,
                "c_ortho": 0.0,
                "c_geom": 0.0,
                "c_bound": 0.0,
                "step_valid_pct": 0.0,
                "std_acoperis": 0.0
            }

        # 1. C_SAM: Optical prediction confidence from neural network
        c_sam = float(np.clip(sam2_score, 0.0, 1.0))

        # 2. C_LiDAR and C_Bound from 3D elevation model
        if ndsm_array is not None and transform is not None:
            roof_stats = self.evaluate_roof_coplanarity(poly, ndsm_array, transform)
            step_stats = self.evaluate_facade_height_steps(poly, ndsm_array, transform)

            h_cov = roof_stats["h_coverage_ratio"]
            std_r = roof_stats["std_roof"]
            step_ratio = step_stats["step_valid_ratio"]

            # Height certainty: coverage >= 2.5m penalized by high roof variance (overhanging trees)
            c_lidar = float(np.clip(h_cov * max(0.0, 1.0 - min(std_r / 2.5, 0.8)), 0.0, 1.0))
            # Boundary certainty: fraction of perimeter with physical wall drop
            c_bound = float(np.clip(step_ratio, 0.0, 1.0))
            std_acoperis = roof_stats["std_roof"]
            step_valid_pct = round(step_ratio * 100.0, 1)
        else:
            c_lidar = 0.80
            c_bound = 0.75
            std_acoperis = 0.35
            step_valid_pct = 75.0

        # 3. C_Ortho: Spectral edge contrast
        if ortho_contrast is not None:
            c_ortho = float(np.clip(ortho_contrast / 50.0, 0.1, 1.0))
        else:
            # Fallback based on optical score
            c_ortho = float(np.clip(0.5 + 0.5 * c_sam, 0.0, 1.0))

        # 4. C_Geom: Geometric regularness, compactness, reasonable vertex count
        ch = poly.convex_hull
        solidity = float(poly.area / (ch.area + 1e-6))
        num_v = len(poly.exterior.coords) - 1
        vertex_penalty = 1.0 if num_v <= 8 else max(0.70, 1.0 - (num_v - 8) * 0.02)
        c_geom = float(np.clip(solidity * vertex_penalty, 0.0, 1.0))

        # 5. Composite Weighted Score
        w_sam, w_lidar, w_ortho, w_geom, w_bound = 0.20, 0.30, 0.20, 0.15, 0.15
        c_final = (
            w_sam * c_sam +
            w_lidar * c_lidar +
            w_ortho * c_ortho +
            w_geom * c_geom +
            w_bound * c_bound
        )
        c_final = round(float(np.clip(c_final, 0.0, 1.0)), 3)

        # 6. Operational Traffic-Light Decision
        if c_final >= 0.85:
            action_code = "VERDE_ACCEPTAT_AUTOMAT"
        elif c_final >= 0.65:
            action_code = "GALBEN_INSPECTIE_GEODEZ"
        else:
            action_code = "ROSU_RESPINS_ARTEFACT"

        return {
            "conf_final": c_final,
            "action_code": action_code,
            "c_sam": round(c_sam, 3),
            "c_lidar": round(c_lidar, 3),
            "c_ortho": round(c_ortho, 3),
            "c_geom": round(c_geom, 3),
            "c_bound": round(c_bound, 3),
            "step_valid_pct": step_valid_pct,
            "std_acoperis": round(std_acoperis, 2)
        }
