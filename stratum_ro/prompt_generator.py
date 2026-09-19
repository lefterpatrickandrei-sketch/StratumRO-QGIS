# -*- coding: utf-8 -*-
"""
StratumRO Prompt Generator
==========================
Deterministic prompt engineering for Meta SAM 2 segmentation.
Synthesizes positive point, multi-point interior grids, bounding boxes, and negative rejection anchors.

ZERO Ground Truth reference leakage: all prompts originate strictly from candidate geometry.
"""

import numpy as np
from scipy.ndimage import distance_transform_edt


class PromptGenerator:
    """
    Generates SAM 2 vision prompts from candidate components.
    """

    def __init__(self, strategy: str = "box_and_point"):
        self.strategy = strategy

    def generate_prompt(
        self,
        cand: dict,
        binary_mask_patch: np.ndarray = None,
        strategy: str = None
    ) -> dict:
        """
        Synthesizes prompt coordinates and labels for SAM 2 inference.

        Parameters
        ----------
        cand : dict
            Candidate object containing 'bbox_px', 'center_px', etc.
        binary_mask_patch : np.ndarray, optional
            Local binary mask for distance transform sampling.
        strategy : str, optional
            Override prompt strategy:
            - 'point_center': Single centroid positive point.
            - 'box_only': Bounding box alone [xmin, ymin, xmax, ymax].
            - 'box_and_center': Bounding box + single centroid point.
            - 'box_and_multipoint': Bounding box + 5 interior grid points.
            - 'box_pos_neg': Bounding box + interior positive + exterior negative points.

        Returns
        -------
        dict
            Dict with keys 'box', 'point_coords', 'point_labels'.
        """
        strat = strategy or self.strategy
        bx = np.array(cand["bbox_px"], dtype=np.float32)
        cx, cy = cand["center_px"]

        if strat == "point_center":
            return {
                "box": None,
                "point_coords": np.array([[cx, cy]], dtype=np.float32),
                "point_labels": np.array([1], dtype=np.int32)
            }

        elif strat == "box_only":
            return {
                "box": bx,
                "point_coords": None,
                "point_labels": None
            }

        elif strat == "box_and_center":
            return {
                "box": bx,
                "point_coords": np.array([[cx, cy]], dtype=np.float32),
                "point_labels": np.array([1], dtype=np.int32)
            }

        elif strat == "box_and_multipoint":
            # Multi-point interior sampling
            pts = []
            labels = []

            # Add center point
            pts.append([cx, cy])
            labels.append(1)

            # Sample 4 internal quadrants at 30% and 70% of box span
            xmin, ymin, xmax, ymax = bx
            dx = xmax - xmin
            dy = ymax - ymin

            for fx in (0.30, 0.70):
                for fy in (0.30, 0.70):
                    px = xmin + fx * dx
                    py = ymin + fy * dy
                    pts.append([px, py])
                    labels.append(1)

            return {
                "box": bx,
                "point_coords": np.array(pts, dtype=np.float32),
                "point_labels": np.array(labels, dtype=np.int32)
            }

        elif strat == "box_pos_neg":
            # Positive center point + negative exterior points around bounding box perimeter
            xmin, ymin, xmax, ymax = bx
            margin = 15.0  # 3 meters at 0.2m GSD

            pts = [
                [cx, cy],                                      # Positive center
                [max(0.0, xmin - margin), max(0.0, ymin - margin)],  # Neg Top-Left
                [xmax + margin, max(0.0, ymin - margin)],            # Neg Top-Right
                [max(0.0, xmin - margin), ymax + margin],            # Neg Bottom-Left
                [xmax + margin, ymax + margin]                       # Neg Bottom-Right
            ]
            labels = [1, 0, 0, 0, 0]

            return {
                "box": bx,
                "point_coords": np.array(pts, dtype=np.float32),
                "point_labels": np.array(labels, dtype=np.int32)
            }

        else:
            raise ValueError(f"Unknown prompt strategy: {strat}")
