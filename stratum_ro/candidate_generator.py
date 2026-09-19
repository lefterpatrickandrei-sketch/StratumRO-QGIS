# -*- coding: utf-8 -*-
"""
StratumRO Candidate Generator
============================
Deterministic building candidate discovery from LiDAR nDSM and optical rasters.
Conforms to ANCPI / geodetic guidelines (Stereo 70 EPSG:3844).

Features:
- Configurable height thresholding
- Morphological operations (opening, closing, hole-filling)
- Area filtering [min_area, max_area]
- Statistical height descriptors (mean, max, std dev / surface roughness)
- Conversion to pixel bounding boxes and geographic polygons
"""

import numpy as np
from scipy.ndimage import label, find_objects, binary_closing, binary_opening, binary_fill_holes
from shapely.geometry import shape, box, MultiPolygon, Polygon
from shapely.validation import make_valid
import rasterio
from rasterio.features import shapes
import geopandas as gpd


class CandidateGenerator:
    """
    Generates building candidate envelopes from Normalized Digital Surface Models (nDSM).
    """

    def __init__(
        self,
        height_threshold: float = 2.5,
        min_area_m2: float = 25.0,
        max_area_m2: float = 8000.0,
        morphology: str = "none",
        fill_holes: bool = False,
        pixel_size_m: float = 0.20
    ):
        self.height_threshold = height_threshold
        self.min_area_m2 = min_area_m2
        self.max_area_m2 = max_area_m2
        self.morphology = morphology
        self.fill_holes = fill_holes
        self.pixel_size_m = pixel_size_m
        self.pixel_area_m2 = pixel_size_m * pixel_size_m

    def generate_candidates(self, ndsm: np.ndarray, transform=None, crs="EPSG:3844"):
        """
        Extracts candidate components from an nDSM array.

        Parameters
        ----------
        ndsm : np.ndarray
            2D array of relative heights in meters.
        transform : rasterio.Affine, optional
            Affine transform mapping pixel coords to geographic coords.
        crs : str, optional
            CRS identifier, default "EPSG:3844".

        Returns
        -------
        list of dict
            List of detected candidate objects with attributes and geometries.
        """
        # 1. Height thresholding
        binary_mask = (ndsm >= self.height_threshold).astype(bool)

        # 2. Morphological filtering
        if self.morphology == "closing_3x3":
            binary_mask = binary_closing(binary_mask, structure=np.ones((3, 3)))
        elif self.morphology == "closing_5x5":
            binary_mask = binary_closing(binary_mask, structure=np.ones((5, 5)))
        elif self.morphology == "open3_close5":
            opened = binary_opening(binary_mask, structure=np.ones((3, 3)))
            binary_mask = binary_closing(opened, structure=np.ones((5, 5)))
        elif self.morphology == "open5_close5":
            opened = binary_opening(binary_mask, structure=np.ones((5, 5)))
            binary_mask = binary_closing(opened, structure=np.ones((5, 5)))

        if self.fill_holes:
            binary_mask = binary_fill_holes(binary_mask)

        # 3. Connected-component labeling (8-connectivity)
        structure_8 = np.ones((3, 3), dtype=int)
        labeled_blobs, num_blobs = label(binary_mask, structure=structure_8)

        min_pixels = int(self.min_area_m2 / self.pixel_area_m2)
        max_pixels = int(self.max_area_m2 / self.pixel_area_m2) if self.max_area_m2 else None

        slices = find_objects(labeled_blobs)
        candidates = []

        for idx, slc in enumerate(slices):
            if slc is None:
                continue

            blob_mask = (labeled_blobs[slc] == (idx + 1))
            pixel_count = int(np.sum(blob_mask))

            # Area bounds
            if pixel_count < min_pixels:
                continue
            if max_pixels is not None and pixel_count > max_pixels:
                continue

            ymin, ymax = slc[0].start, slc[0].stop
            xmin, xmax = slc[1].start, slc[1].stop

            # Centroid in pixel coordinates
            y_indices, x_indices = np.where(blob_mask)
            cy = int(ymin + np.mean(y_indices))
            cx = int(xmin + np.mean(x_indices))

            # Height statistics
            blob_heights = ndsm[slc][blob_mask]
            mean_h = float(np.mean(blob_heights))
            max_h = float(np.max(blob_heights))
            std_h = float(np.std(blob_heights))

            cand_dict = {
                "cand_id": f"CAND_{len(candidates) + 1:03d}",
                "bbox_px": [xmin, ymin, xmax, ymax],
                "center_px": [cx, cy],
                "area_m2": float(pixel_count * self.pixel_area_m2),
                "pixel_count": pixel_count,
                "mean_h": mean_h,
                "max_h": max_h,
                "std_h": std_h,
                "slice": (slc[0], slc[1])
            }

            if transform is not None:
                # Convert bbox to geo coordinates
                wx_min, wy_max = transform * (xmin, ymin)
                wx_max, wy_min = transform * (xmax, ymax)
                cand_dict["bbox_geo"] = [min(wx_min, wx_max), min(wy_min, wy_max), max(wx_min, wx_max), max(wy_min, wy_max)]
                cand_dict["geometry"] = box(cand_dict["bbox_geo"][0], cand_dict["bbox_geo"][1], cand_dict["bbox_geo"][2], cand_dict["bbox_geo"][3])

            candidates.append(cand_dict)

        return candidates

    def to_geodataframe(self, candidates: list, crs="EPSG:3844"):
        """Converts candidates to a GeoPandas GeoDataFrame."""
        records = []
        for c in candidates:
            rec = {k: v for k, v in c.items() if k not in ("slice", "geometry")}
            rec["geometry"] = c.get("geometry", None)
            records.append(rec)
        return gpd.GeoDataFrame(records, crs=crs)
