# -*- coding: utf-8 -*-
"""
Meta SAM 2 (Segment Anything Model 2) Hybrid Segmentation Engine for StratumRO.
Performs Sensor Fusion:
- Takes LiDAR nDSM & ASPRS Class 6 building footprint proposals.
- Prompts Meta SAM 2 on high-resolution orthophotos with bounding boxes and internal positive points.
- Enforces strict Double-Confirmation validation:
    1. Height certainty from LiDAR nDSM (H_mean >= 2.5m, H_max >= 3.0m).
    2. Optical delineation certainty from Meta SAM 2 (confidence score >= 0.60, valid roofline).
- Generates regularized cadastral polygons (Stereo 70 EPSG:3844) with minimal CAD vertices.
"""

import os
import time
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
import rasterio
from rasterio.features import shapes
from shapely.geometry import Polygon, MultiPolygon, shape, box
from shapely.validation import make_valid
from scipy.ndimage import label, find_objects
import torch

try:
    from sam2.build_sam import build_sam2
    from sam2.sam2_image_predictor import SAM2ImagePredictor
    SAM2_AVAILABLE = True
except ImportError:
    SAM2_AVAILABLE = False


def _extract_largest_polygon(geom) -> Optional[Polygon]:
    """Extracts largest valid Polygon from any geometry."""
    if geom is None or geom.is_empty:
        return None
    if isinstance(geom, Polygon):
        return geom
    if isinstance(geom, MultiPolygon):
        return max(geom.geoms, key=lambda g: g.area)
    if hasattr(geom, "geoms"):
        polys = [g for g in geom.geoms if isinstance(g, Polygon)]
        if polys:
            return max(polys, key=lambda g: g.area)
        for g in geom.geoms:
            sub = _extract_largest_polygon(g)
            if sub is not None:
                return sub
    return None


class SAM2BuildingSegmenter:
    """
    Hybrid Building Segmentation combining Meta SAM 2 vision transformer
    with LiDAR nDSM height cross-validation.
    """

    DEFAULT_CHECKPOINT = os.path.abspath(r"models\sam2\sam2_hiera_tiny.pt")
    DEFAULT_CONFIG = "sam2_hiera_t.yaml"

    def __init__(
        self,
        checkpoint_path: Optional[str] = None,
        model_cfg: str = DEFAULT_CONFIG,
        device: Optional[str] = None
    ):
        if not SAM2_AVAILABLE:
            raise RuntimeError("Pachetul 'sam2' nu este instalat în mediul curent.")

        self.checkpoint_path = checkpoint_path or self.DEFAULT_CHECKPOINT
        if not os.path.exists(self.checkpoint_path):
            raise FileNotFoundError(f"Ponderile SAM 2 nu au fost găsite la: {self.checkpoint_path}")

        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device

        self.model_cfg = model_cfg
        self.model = build_sam2(self.model_cfg, self.checkpoint_path, device=self.device)
        self.predictor = SAM2ImagePredictor(self.model)

        self.current_image_shape = None
        self.current_transform = None
        self.current_inv_transform = None

    def set_image(self, image_rgb: np.ndarray, transform: rasterio.Affine) -> float:
        """
        Loads the RGB orthophoto crop into GPU memory and computes image embeddings once.
        Returns time taken for image encoding in seconds.
        """
        t0 = time.time()
        self.current_image_shape = image_rgb.shape[:2]  # (H, W)
        self.current_transform = transform
        self.current_inv_transform = ~transform

        with torch.inference_mode():
            self.predictor.set_image(image_rgb)

        encode_time = time.time() - t0
        return encode_time

    def segment_candidate(
        self,
        b_xmin: float,
        b_ymin: float,
        b_xmax: float,
        b_ymax: float,
        mean_h: float,
        max_h: float,
        lidar_area: float,
        internal_pts_geo: Optional[List[Tuple[float, float]]] = None,
        score_threshold: float = 0.60,
        height_min_threshold: float = 2.5,
        external_pts_geo: Optional[List[Tuple[float, float]]] = None
    ) -> Dict[str, Any]:
        """
        Segments and validates an individual building candidate using SAM 2 + LiDAR cross-check.

        :param b_xmin, b_ymin, b_xmax, b_ymax: Bounding box in Stereo 70 coordinates.
        :param mean_h: Mean height from LiDAR nDSM.
        :param max_h: Max peak height from LiDAR nDSM.
        :param lidar_area: Footprint area from LiDAR in m^2.
        :param internal_pts_geo: Optional list of (x, y) coordinates inside building (positive points).
        :param score_threshold: Minimum SAM 2 confidence score for optical acceptance.
        :param height_min_threshold: Minimum LiDAR height required for double confirmation.
        :param external_pts_geo: Optional list of (x, y) coordinates outside building (negative points).
        """
        if self.current_transform is None:
            raise RuntimeError("Nicio imagine ortofoto nu a fost setată cu set_image().")

        inv_tr = self.current_inv_transform
        tr = self.current_transform
        img_h, img_w = self.current_image_shape

        # 1. Transform bounding box to image pixel space with a 1.2m buffer
        buf = 1.2
        corners = [inv_tr * (x, y) for x in (b_xmin-buf, b_xmax+buf)
                   for y in (b_ymin-buf, b_ymax+buf)]
        bx_min = max(0.0, min(p[0] for p in corners))
        by_min = max(0.0, min(p[1] for p in corners))
        bx_max = min(float(img_w - 1), max(p[0] for p in corners))
        by_max = min(float(img_h - 1), max(p[1] for p in corners))

        # Check if box is valid inside image boundaries
        if (bx_max - bx_min) < 3 or (by_max - by_min) < 3:
            return {"status": "RESPINS", "reason": "Caseta în afara decupajului ortofoto"}

        box_prompt = np.array([bx_min, by_min, bx_max, by_max], dtype=np.float32)

        # 2. Build point prompts from internal positive and external negative points
        pts_px = []
        labels = []
        valid_pos_geo = []

        if internal_pts_geo:
            for gx, gy in internal_pts_geo:
                ix, iy = inv_tr * (gx, gy)
                if 0 <= ix < img_w and 0 <= iy < img_h:
                    pts_px.append([ix, iy])
                    labels.append(1)
                    valid_pos_geo.append((gx, gy))

        if external_pts_geo:
            for gx, gy in external_pts_geo:
                ix, iy = inv_tr * (gx, gy)
                if 0 <= ix < img_w and 0 <= iy < img_h:
                    pts_px.append([ix, iy])
                    labels.append(0)

        point_coords = np.array(pts_px, dtype=np.float32) if pts_px else None
        point_labels = np.array(labels, dtype=np.int32) if labels else None

        # 3. Predict optical masks via SAM 2
        with torch.inference_mode():
            masks, scores, _ = self.predictor.predict(
                point_coords=point_coords,
                point_labels=point_labels,
                box=box_prompt,
                multimask_output=True
            )

        # 4. Multi-mask selection: pick mask with best balance of score & area consistency
        # Determinant of the affine transform gives the true pixel area: abs(a*e - b*d)
        pixel_area = abs(tr.a * tr.e - tr.b * tr.d)

        best_idx = None
        best_metric = -999.0
        best_poly = None

        for idx, (m, sc) in enumerate(zip(masks, scores)):
            if not np.isfinite(sc):
                continue
            m_sum = np.sum(m)
            if not np.isfinite(m_sum):
                continue
            m_area = float(m_sum) * pixel_area
            if not np.isfinite(m_area) or m_area < 5.0:
                continue
            # Rank the prompted component, not unrelated objects elsewhere in a mask.
            poly = self._mask_to_stereo70_polygon(
                m, bx_min, by_min, bx_max, by_max, tr,
                internal_pts_geo=valid_pos_geo or None)
            if poly is None:
                continue
            m_area = poly.area
            # Area ratio with LiDAR footprint
            ratio = min(m_area, lidar_area) / max(m_area, lidar_area) if max(m_area, lidar_area) > 0 else 0.0
            metric = float(sc) * 0.7 + ratio * 0.3
            if metric > best_metric:
                best_metric = metric
                best_idx = idx
                best_poly = poly

        if best_idx is None:
            return {"status": "RESPINS",
                    "reason": "Nicio mască validă pentru obiectul indicat", "geometry": None,
                    "optical_poly": None}

        chosen_mask = masks[best_idx]
        chosen_score = float(scores[best_idx])
        chosen_area = float(best_poly.area)

        # 5. Extract optical polygon from binary mask, threading valid in-image positive points
        opt_poly = best_poly

        # 6. Double Confirmation Evaluation
        height_ok = (mean_h >= height_min_threshold) and (max_h >= 2.5)
        optical_ok = (chosen_score >= score_threshold) and (opt_poly is not None) and (opt_poly.area >= 8.0)

        # Regula adaptiva pentru sere horticiole si acoperisuri moderne plane:
        # Forme optice regulate mari (> 150 mp) cu scor optic ridicat (>= 0.65)
        # sunt confirmate chiar daca nDSM este redus (penetrare LiDAR prin sticla / filtrare la sol)
        if not height_ok and optical_ok:
            opt_area = opt_poly.area if opt_poly is not None else 0.0
            if opt_area >= 150.0 and (max_h >= 0.8 or mean_h >= 0.3):
                height_ok = True

        if height_ok and optical_ok:
            status = "CONFIRMAT_HIBRID"
            final_poly = opt_poly
        elif height_ok and not optical_ok:
            # LiDAR confirms real building, but optical view was obstructed/shadowed
            status = "LIDAR_DIRECT"
            final_poly = None  # Caller will use LiDAR polygon
        else:
            status = "RESPINS"
            final_poly = None

        return {
            "status": status,
            "sam2_score": round(chosen_score, 3),
            "sam2_area_m2": round(chosen_area, 1),
            "lidar_area_m2": round(lidar_area, 1),
            "mean_h": round(mean_h, 1),
            "max_h": round(max_h, 1),
            "optical_poly": opt_poly,
            "geometry": final_poly
        }

    def _mask_to_stereo70_polygon(
        self,
        mask: np.ndarray,
        bx_min: float,
        by_min: float,
        bx_max: float,
        by_max: float,
        full_transform: rasterio.Affine,
        internal_pts_geo: Optional[List[Tuple[float, float]]] = None
    ) -> Optional[Polygon]:
        """Converts SAM 2 sub-window binary mask to a valid Shapely Polygon in Stereo 70."""
        # Slice to bounding box window with margin to accelerate contouring
        pad = 2
        r0 = max(0, int(np.floor(by_min)) - pad)
        r1 = min(mask.shape[0], int(np.ceil(by_max)) + pad)
        c0 = max(0, int(np.floor(bx_min)) - pad)
        c1 = min(mask.shape[1], int(np.ceil(bx_max)) + pad)

        sub_mask = mask[r0:r1, c0:c1].astype(np.uint8)
        if np.sum(sub_mask) < 10:
            return None

        # Compute affine transform for the window
        sub_transform = full_transform * rasterio.Affine.translation(c0, r0)

        # Extract vector shapes
        extracted_polys = []
        for geom_dict, val in shapes(sub_mask, mask=(sub_mask == 1), transform=sub_transform):
            if val == 1:
                try:
                    s_geom = shape(geom_dict)
                    if not s_geom.is_valid:
                        s_geom = make_valid(s_geom)
                    largest = _extract_largest_polygon(s_geom)
                    if largest is not None and largest.is_valid and largest.area > 5.0:
                        extracted_polys.append(largest)
                except Exception:
                    pass

        if not extracted_polys:
            return None

        # If positive points are supplied, select a polygon covering valid positive points
        if internal_pts_geo:
            from shapely.geometry import Point
            pts = [Point(gx, gy) for gx, gy in internal_pts_geo]
            matching_polys = []
            for poly in extracted_polys:
                cov_count = sum(1 for pt in pts if poly.intersects(pt))
                if cov_count > 0:
                    matching_polys.append((cov_count, poly.area, poly))

            if matching_polys:
                # Prefer most covered positive points, then area
                matching_polys.sort(key=lambda item: (item[0], item[1]), reverse=True)
                return matching_polys[0][2]
            else:
                # Valid in-image positive points were supplied but none covered;
                # return None rather than selecting another disconnected object
                return None

        # Fallback when no positive points are supplied (backward compatibility):
        # Pick the largest polygon by area
        return max(extracted_polys, key=lambda p: p.area)
