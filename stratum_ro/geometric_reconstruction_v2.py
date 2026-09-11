# -*- coding: utf-8 -*-
"""
StratumRO — Building Extraction Quality V2: Geometric Reconstruction Engine
===========================================================================
Replaces naive Douglas-Peucker simplification with a mathematically sound,
adaptive support-line reconstruction pipeline:
  1. GSD-dependent morphological cleanup (closing interior voids, opening fringes).
  2. Contour decomposition into coherent facade segments.
  3. Total Least Squares (TLS / SVD) support-line fitting on facade points.
  4. Circular Kernel Density / Manhattan Frame clustering (modulo 90 deg).
  5. Adjacent support-line intersection for subpixel-exact, sharp 90 deg corners.
  6. Adaptive 4-tier non-destructive shape classifier:
     - Class A: Canonical OBB Rectangle (4 vertices, 90 deg)
     - Class B: Manhattan Orthogonal L, U, T with re-entrant notches (5-8 vertices)
     - Class C: Multi-wing large complex (>8 vertices, area > 300 m2)
     - Class D: Non-orthogonal / oblique / curved (preserves genuine angles without force-rotating).
"""

import math
import numpy as np
from typing import List, Tuple, Dict, Any, Optional
from shapely.geometry import Polygon, Point, LineString, box
from shapely.affinity import rotate
from shapely.ops import unary_union
from scipy.ndimage import binary_closing, binary_opening, binary_fill_holes, generate_binary_structure


class AdaptiveContourReconstructor:
    """
    Cadastral-grade geometric contour reconstructor using support-line
    fitting and adaptive classification.
    """

    def __init__(self, gsd_m: float = 0.15):
        self.gsd = max(0.02, float(gsd_m))

    def clean_binary_mask(self, mask: np.ndarray, close_m: float = 0.35, open_m: float = 0.20) -> np.ndarray:
        """
        Applies GSD-scaled morphological cleanup to eliminate pixel jitter,
        fill internal skylight/chimney holes, and detach thin vegetation fringes.
        """
        if mask is None or np.sum(mask) == 0:
            return mask

        close_radius_px = max(1, int(round(close_m / self.gsd)))
        open_radius_px = max(1, int(round(open_m / self.gsd)))

        # Create disk-approximated structuring element
        y, x = np.ogrid[-close_radius_px:close_radius_px + 1, -close_radius_px:close_radius_px + 1]
        struct_close = (x * x + y * y) <= (close_radius_px * close_radius_px)

        y_o, x_o = np.ogrid[-open_radius_px:open_radius_px + 1, -open_radius_px:open_radius_px + 1]
        struct_open = (x_o * x_o + y_o * y_o) <= (open_radius_px * open_radius_px)

        # 1. Fill small interior holes
        filled = binary_fill_holes(mask > 0)

        # 2. Opening first (removes tiny exterior spikes / overhanging antenna leaves)
        opened = binary_opening(filled, structure=struct_open)

        # 3. Closing (smooths borders and bridges small facade notches)
        closed = binary_closing(opened, structure=struct_close)
        return closed.astype(np.uint8)

    @staticmethod
    def fit_line_tls(points: np.ndarray) -> Optional[Tuple[float, float, float]]:
        """
        Fits a 2D line A*x + B*y + C = 0 using Total Least Squares (SVD / PCA).
        Normalized such that A^2 + B^2 = 1.
        """
        if points is None or len(points) < 2:
            return None

        centroid = np.mean(points, axis=0)
        centered = points - centroid

        # Covariance / SVD
        cov = np.dot(centered.T, centered)
        evals, evecs = np.linalg.eigh(cov)

        # Normal vector is the eigenvector corresponding to smallest eigenvalue
        normal = evecs[:, 0]
        norm = np.linalg.norm(normal)
        if norm < 1e-7:
            return None

        A = float(normal[0] / norm)
        B = float(normal[1] / norm)
        C = float(-(A * centroid[0] + B * centroid[1]))
        return A, B, C

    @staticmethod
    def intersect_lines(l1: Tuple[float, float, float], l2: Tuple[float, float, float]) -> Optional[Tuple[float, float]]:
        """Computes the exact mathematical intersection (x, y) of two support lines."""
        A1, B1, C1 = l1
        A2, B2, C2 = l2
        det = A1 * B2 - A2 * B1
        if abs(det) < 1e-6:  # Parallel lines
            return None
        x = (B1 * C2 - B2 * C1) / det
        y = (A2 * C1 - A1 * C2) / det
        return float(x), float(y)

    def extract_facade_segments(
        self,
        coords: List[Tuple[float, float]],
        corner_tol_m: float = 0.35,
        min_seg_len_m: float = 0.8
    ) -> List[np.ndarray]:
        """
        Decomposes a continuous polygon contour into coherent linear facade point clusters.
        """
        if len(coords) < 4:
            return [np.array(coords)]

        # Ensure no trailing duplicate
        pts = np.array(coords[:-1] if coords[0] == coords[-1] else coords)
        n = len(pts)
        if n < 4:
            return [pts]

        # Identify corner vertices using Douglas-Peucker / Ramer-Douglas-Peucker on closed ring
        poly_temp = Polygon(pts)
        simp = poly_temp.simplify(corner_tol_m, preserve_topology=True)
        corner_coords = list(simp.exterior.coords)[:-1]

        if len(corner_coords) < 3:
            return [pts]

        # Find indices of corner vertices in dense points
        corner_indices = []
        for c in corner_coords:
            dists = np.hypot(pts[:, 0] - c[0], pts[:, 1] - c[1])
            corner_indices.append(int(np.argmin(dists)))

        corner_indices = sorted(list(set(corner_indices)))
        if len(corner_indices) < 3:
            return [pts]

        segments = []
        num_corners = len(corner_indices)
        for i in range(num_corners):
            idx_start = corner_indices[i]
            idx_end = corner_indices[(i + 1) % num_corners]

            if idx_end > idx_start:
                seg = pts[idx_start:idx_end + 1]
            else:
                seg = np.vstack([pts[idx_start:], pts[:idx_end + 1]])

            # Measure segment length
            seg_len = np.hypot(seg[-1, 0] - seg[0, 0], seg[-1, 1] - seg[0, 1])
            if seg_len >= min_seg_len_m or len(segments) < 3:
                segments.append(seg)

        return segments if len(segments) >= 3 else [pts]

    def compute_dominant_frame(self, lines: List[Tuple[float, float, float]], lengths: List[float]) -> float:
        """
        Estimates the primary dominant building orientation theta in [0, 90) degrees
        using length-weighted circular mean modulo 90 degrees.
        """
        if not lines or not lengths:
            return 0.0

        angles = []
        weights = []
        for (A, B, C), l in zip(lines, lengths):
            # Normal angle to line angle: theta = atan2(-A, B)
            ang = math.atan2(-A, B) % (math.pi / 2.0)
            angles.append(ang)
            weights.append(max(0.1, l))

        total_w = sum(weights)
        if total_w == 0:
            return 0.0

        # Circular mean on 4*theta to wrap every 90 degrees (pi/2 radians)
        sin_sum = sum(w * math.sin(4.0 * a) for w, a in zip(weights, angles))
        cos_sum = sum(w * math.cos(4.0 * a) for w, a in zip(weights, angles))

        dominant_rad = (math.atan2(sin_sum, cos_sum) / 4.0) % (math.pi / 2.0)
        return float(math.degrees(dominant_rad))

    def reconstruct_from_support_lines(
        self,
        poly: Polygon,
        max_angular_dev_deg: float = 14.0
    ) -> Optional[Polygon]:
        """
        Fits support lines to facade segments, snaps compatible edges to the dominant frame,
        and reconstructs exact corner vertices via line intersections.
        """
        coords = list(poly.exterior.coords)
        segments = self.extract_facade_segments(coords)
        if len(segments) < 3:
            return None

        lines = []
        lengths = []
        centroids = []

        for seg in segments:
            line_fit = self.fit_line_tls(seg)
            if line_fit is not None:
                lines.append(line_fit)
                l = float(np.hypot(seg[-1, 0] - seg[0, 0], seg[-1, 1] - seg[0, 1]))
                lengths.append(l)
                centroids.append(np.mean(seg, axis=0))

        if len(lines) < 3:
            return None

        dom_angle_deg = self.compute_dominant_frame(lines, lengths)
        dom_rad = math.radians(dom_angle_deg)

        # Align lines that are close to dominant orientation (modulo 90 deg)
        aligned_lines = []
        for (A, B, C), (cx, cy) in zip(lines, centroids):
            theta = math.atan2(-A, B)
            # Find nearest multiple of 90 deg relative to dominant angle
            delta = (theta - dom_rad + math.pi / 4.0) % (math.pi / 2.0) - (math.pi / 4.0)
            delta_deg = abs(math.degrees(delta))

            if delta_deg <= max_angular_dev_deg:
                # Snap angle to nearest 90 deg multiple
                snapped_theta = theta - delta
                snapped_A = -math.sin(snapped_theta)
                snapped_B = math.cos(snapped_theta)
                snapped_C = -(snapped_A * cx + snapped_B * cy)
                aligned_lines.append((snapped_A, snapped_B, snapped_C))
            else:
                # Keep original orientation (genuine non-orthogonal / oblique facade)
                aligned_lines.append((A, B, C))

        # Intersect consecutive support lines to reconstruct vertices
        m = len(aligned_lines)
        new_vertices = []
        for i in range(m):
            l_curr = aligned_lines[i]
            l_next = aligned_lines[(i + 1) % m]
            pt = self.intersect_lines(l_curr, l_next)
            if pt is not None:
                new_vertices.append(pt)

        if len(new_vertices) >= 3:
            new_poly = Polygon(new_vertices)
            if new_poly.is_valid and new_poly.area >= 6.0:
                # Sanity check: IoU with original polygon must be reasonable (>= 0.55)
                iou = poly.intersection(new_poly).area / (poly.union(new_poly).area + 1e-6)
                if iou >= 0.55:
                    return new_poly

        return None

    def classify_and_reconstruct(self, poly: Polygon) -> Dict[str, Any]:
        """
        Adaptive 4-tier non-destructive shape classifier and reconstructor:
          - Class A: OBB Rectangle (R >= 0.88, S >= 0.89, N <= 8)
          - Class B: Manhattan Orthogonal L, U, T (5-8 vertices, Ortho >= 0.75)
          - Class C: Multi-wing large complex (>8 vertices, Area > 300 m2)
          - Class D: Non-orthogonal / oblique / curved (conserves authentic geometry)
        """
        if poly is None or not poly.is_valid or poly.is_empty or poly.area < 6.0:
            return {
                "geometry": poly,
                "clasa_forma": "INVALID",
                "rect_ratio": 0.0,
                "solidity": 0.0,
                "ortho_ratio": 0.0,
                "num_vertices": 0
            }

        mrr = poly.minimum_rotated_rectangle
        rect_ratio = float(poly.area / (mrr.area + 1e-6))
        ch = poly.convex_hull
        solidity = float(poly.area / (ch.area + 1e-6))
        coords = list(poly.exterior.coords)[:-1]
        num_v = len(coords)

        # Compute internal angle orthogonality
        right_angles = 0
        n = len(coords)
        for i in range(n):
            p0 = np.array(coords[i - 1])
            p1 = np.array(coords[i])
            p2 = np.array(coords[(i + 1) % n])
            v1 = p0 - p1
            v2 = p2 - p1
            d1, d2 = np.linalg.norm(v1), np.linalg.norm(v2)
            if d1 > 0.4 and d2 > 0.4:
                cos_a = np.clip(np.dot(v1, v2) / (d1 * d2), -1.0, 1.0)
                deg = np.degrees(np.arccos(cos_a))
                if abs(deg - 90.0) <= 15.0:
                    right_angles += 1
        ortho_ratio = float(right_angles / max(n, 1))

        # -------------------------------------------------------------
        # 1. CLASA A: Dreptunghi Canonic Simplu (OBB - 4 noduri la 90°)
        # -------------------------------------------------------------
        if solidity >= 0.89 and rect_ratio >= 0.86 and num_v <= 8:
            return {
                "geometry": mrr,
                "clasa_forma": "DREPTUNGHI_OBB",
                "rect_ratio": round(rect_ratio, 3),
                "solidity": round(solidity, 3),
                "ortho_ratio": 1.0,
                "num_vertices": 4
            }

        # -------------------------------------------------------------
        # 2. CLASA B: Forme Ortogonale L, U, T, Decroșuri (5 - 8 Noduri)
        # -------------------------------------------------------------
        if (5 <= num_v <= 12 and ortho_ratio >= 0.70) or (solidity >= 0.65 and ortho_ratio >= 0.75):
            # Attempt exact support-line intersection reconstruction
            rec_poly = self.reconstruct_from_support_lines(poly)
            if rec_poly is not None:
                final_poly = rec_poly
            else:
                # Conservative Manhattan simplification
                final_poly = poly.simplify(0.35, preserve_topology=True)

            return {
                "geometry": final_poly if (final_poly.is_valid and final_poly.area >= 6.0) else poly,
                "clasa_forma": "MANHATTAN_LUT",
                "rect_ratio": round(rect_ratio, 3),
                "solidity": round(solidity, 3),
                "ortho_ratio": round(ortho_ratio, 3),
                "num_vertices": len(final_poly.exterior.coords) - 1
            }

        # -------------------------------------------------------------
        # 3. CLASA C: Clădiri Mari Complexe / Pavilioane (>8 Noduri, >250 m2)
        # -------------------------------------------------------------
        if poly.area >= 250.0 and num_v >= 8 and ortho_ratio >= 0.65:
            rec_poly = self.reconstruct_from_support_lines(poly, max_angular_dev_deg=10.0)
            if rec_poly is not None:
                final_poly = rec_poly
            else:
                final_poly = poly.simplify(0.40, preserve_topology=True)

            return {
                "geometry": final_poly if (final_poly.is_valid and final_poly.area >= 6.0) else poly,
                "clasa_forma": "COMPLEX_MULTI",
                "rect_ratio": round(rect_ratio, 3),
                "solidity": round(solidity, 3),
                "ortho_ratio": round(ortho_ratio, 3),
                "num_vertices": len(final_poly.exterior.coords) - 1
            }

        # -------------------------------------------------------------
        # 4. CLASA D: Forme Atipice / Oblice / Curbate (Non-destructive)
        # -------------------------------------------------------------
        # Non-orthogonal genuine architecture: DO NOT force 90 deg angles!
        smooth_poly = poly.simplify(0.18, preserve_topology=True)
        return {
            "geometry": smooth_poly if (smooth_poly.is_valid and smooth_poly.area >= 6.0) else poly,
            "clasa_forma": "ATIPIC_OBLIC",
            "rect_ratio": round(rect_ratio, 3),
            "solidity": round(solidity, 3),
            "ortho_ratio": round(ortho_ratio, 3),
            "num_vertices": len(smooth_poly.exterior.coords) - 1
        }
