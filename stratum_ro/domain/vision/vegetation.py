# -*- coding: utf-8 -*-
"""
StratumRO Multimodal Vegetation Filter
=====================================
Deterministic building vs vegetation discriminator combining RGB optical texture
and LiDAR point cloud attributes (ASPRS classes 3/4/5 vs 6, surface roughness).

Designed for standard RGB aerial photography without NIR dependency.
"""

import numpy as np


class MultimodalVegetationFilter:
    """
    Discriminates between genuine building envelopes and vegetation canopies.
    """

    def __init__(
        self,
        exg_threshold: float = 0.06,
        veg_ratio_threshold: float = 0.80,
        bldg_ratio_min: float = 0.05,
        roughness_threshold_m: float = 2.0
    ):
        self.exg_threshold = exg_threshold
        self.veg_ratio_threshold = veg_ratio_threshold
        self.bldg_ratio_min = bldg_ratio_min
        self.roughness_threshold_m = roughness_threshold_m

    @staticmethod
    def compute_exg(rgb_img: np.ndarray) -> np.ndarray:
        """
        Computes Excess Green Index: ExG = 2G - R - B.

        Parameters
        ----------
        rgb_img : np.ndarray
            (3, H, W) or (H, W, 3) uint8 or float32 RGB image.

        Returns
        -------
        np.ndarray
            (H, W) float32 ExG array.
        """
        if rgb_img.shape[0] == 3:
            r = rgb_img[0].astype(np.float32) / 255.0
            g = rgb_img[1].astype(np.float32) / 255.0
            b = rgb_img[2].astype(np.float32) / 255.0
        else:
            r = rgb_img[:, :, 0].astype(np.float32) / 255.0
            g = rgb_img[:, :, 1].astype(np.float32) / 255.0
            b = rgb_img[:, :, 2].astype(np.float32) / 255.0

        return 2.0 * g - r - b

    @staticmethod
    def compute_gli(rgb_img: np.ndarray) -> np.ndarray:
        """
        Computes Green Leaf Index: GLI = (2G - R - B) / (2G + R + B + eps).
        """
        if rgb_img.shape[0] == 3:
            r = rgb_img[0].astype(np.float32) / 255.0
            g = rgb_img[1].astype(np.float32) / 255.0
            b = rgb_img[2].astype(np.float32) / 255.0
        else:
            r = rgb_img[:, :, 0].astype(np.float32) / 255.0
            g = rgb_img[:, :, 1].astype(np.float32) / 255.0
            b = rgb_img[:, :, 2].astype(np.float32) / 255.0

        denom = 2.0 * g + r + b + 1e-6
        return (2.0 * g - r - b) / denom

    def evaluate_candidate(
        self,
        cand: dict,
        rgb_img: np.ndarray,
        ndsm: np.ndarray,
        lidar_bldg_grid: np.ndarray = None,
        lidar_veg_grid: np.ndarray = None
    ) -> dict:
        """
        Evaluates a single candidate blob against multimodal vegetation indicators.

        Returns
        -------
        dict
            Assessment containing is_vegetation, veg_score, rejection_reason, and evidence.
        """
        slc = cand.get("slice")
        if slc is None:
            # Fallback to bbox
            xmin, ymin, xmax, ymax = cand["bbox_px"]
            slc = (slice(ymin, ymax), slice(xmin, xmax))

        # Optical feature extraction
        if rgb_img.shape[0] == 3:
            r = rgb_img[0, slc[0], slc[1]].astype(np.float32) / 255.0
            g = rgb_img[1, slc[0], slc[1]].astype(np.float32) / 255.0
            b = rgb_img[2, slc[0], slc[1]].astype(np.float32) / 255.0
        else:
            r = rgb_img[slc[0], slc[1], 0].astype(np.float32) / 255.0
            g = rgb_img[slc[0], slc[1], 1].astype(np.float32) / 255.0
            b = rgb_img[slc[0], slc[1], 2].astype(np.float32) / 255.0

        exg_patch = 2.0 * g - r - b
        mean_exg = float(np.mean(exg_patch))
        std_exg = float(np.std(exg_patch))

        # Height roughness (std dev)
        std_h = cand.get("std_h", float(np.std(ndsm[slc])))

        # LiDAR class evidence
        bldg_pts = 0
        veg_pts = 0
        bldg_ratio = 0.0
        veg_ratio = 0.0

        if lidar_bldg_grid is not None and lidar_veg_grid is not None:
            # If grids are at different resolution, map slice
            # Assuming grids match ndsm shape or can be indexed
            gh, gw = lidar_bldg_grid.shape
            nh, nw = ndsm.shape
            sy = gh / nh
            sx = gw / nw
            r_slc = (slice(int(slc[0].start * sy), int(slc[0].stop * sy)), slice(int(slc[1].start * sx), int(slc[1].stop * sx)))

            bldg_pts = int(np.sum(lidar_bldg_grid[r_slc]))
            veg_pts = int(np.sum(lidar_veg_grid[r_slc]))
            total_classified = bldg_pts + veg_pts
            if total_classified > 0:
                bldg_ratio = float(bldg_pts / total_classified)
                veg_ratio = float(veg_pts / total_classified)

        # Decision logic
        is_veg = False
        reasons = []

        # Rule 1: High LiDAR vegetation ratio + zero building points + positive optical ExG
        if veg_ratio >= self.veg_ratio_threshold and bldg_pts == 0 and mean_exg > 0.0:
            is_veg = True
            reasons.append(f"Pure LiDAR vegetation ({veg_ratio*100:.1f}%, 0 bldg pts) with green canopy (ExG={mean_exg:.3f})")

        # Rule 2: Overwhelming LiDAR vegetation regardless of optical (e.g. shadowed trees)
        elif veg_ratio >= 0.92 and bldg_pts == 0 and veg_pts > 20:
            is_veg = True
            reasons.append(f"Dominant LiDAR vegetation returns ({veg_ratio*100:.1f}%, veg_pts={veg_pts}, 0 bldg pts)")

        # Rule 3: High optical greenness + high height roughness + low building points
        elif mean_exg >= self.exg_threshold and std_h >= self.roughness_threshold_m and bldg_ratio < self.bldg_ratio_min:
            is_veg = True
            reasons.append(f"Optical foliage texture (ExG={mean_exg:.3f}) and rough canopy (sigma_Z={std_h:.2f}m)")

        veg_score = 1.0 if is_veg else float(max(0.0, veg_ratio * 0.7 + max(0.0, mean_exg) * 0.3))

        return {
            "is_vegetation": is_veg,
            "veg_score": veg_score,
            "rejection_reason": "; ".join(reasons) if is_veg else "Passed (Building Candidate)",
            "evidence": {
                "mean_exg": mean_exg,
                "std_exg": std_exg,
                "std_h_roughness": std_h,
                "lidar_bldg_pts": bldg_pts,
                "lidar_veg_pts": veg_pts,
                "bldg_ratio": bldg_ratio,
                "veg_ratio": veg_ratio
            }
        }

    def filter_candidates(
        self,
        candidates: list,
        rgb_img: np.ndarray,
        ndsm: np.ndarray,
        lidar_bldg_grid: np.ndarray = None,
        lidar_veg_grid: np.ndarray = None
    ) -> tuple:
        """
        Filters a list of candidate dictionaries.

        Returns
        -------
        tuple
            (accepted_candidates, rejected_candidates)
        """
        accepted = []
        rejected = []

        for cand in candidates:
            eval_res = self.evaluate_candidate(cand, rgb_img, ndsm, lidar_bldg_grid, lidar_veg_grid)
            cand_copy = dict(cand)
            cand_copy["vegetation_eval"] = eval_res

            if eval_res["is_vegetation"]:
                rejected.append(cand_copy)
            else:
                accepted.append(cand_copy)

        return accepted, rejected
