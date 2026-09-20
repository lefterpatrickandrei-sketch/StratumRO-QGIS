# -*- coding: utf-8 -*-
"""
Geometric and Sensor Perturbation Engine for StratumRO.
Allows controlled stress-testing of regularizers, candidate generators, and vectorizers
by applying parameterized transformations (translation, rotation, scaling, jitter)
to evaluate boundary robustness and failure thresholds without altering ground truth.
"""

import copy
import math
import random
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class PerturbationConfig:
    shift_x: float = 0.0          # Horizontal translation (meters)
    shift_y: float = 0.0          # Vertical translation (meters)
    rotation_deg: float = 0.0     # Rotation around centroid (degrees)
    scale: float = 1.0            # Uniform scaling factor
    vertex_jitter_sigma: float = 0.0  # Gaussian noise added to vertex coordinates (meters)
    seed: Optional[int] = None    # Random seed for reproducible experiments


class PerturbationEngine:
    """
    Applies deterministic and stochastic perturbations to 2D polygon geometries.
    """

    def __init__(self, seed: Optional[int] = None):
        self.rng = random.Random(seed)

    def perturb_ring(
        self,
        coords: List[Tuple[float, float]],
        config: PerturbationConfig,
    ) -> List[Tuple[float, float]]:
        """
        Perturbs a single closed linear ring of coordinates.
        """
        if not coords or len(coords) < 3:
            return coords

        if config.seed is not None:
            self.rng = random.Random(config.seed)

        is_closed = (coords[0][0] == coords[-1][0] and coords[0][1] == coords[-1][1])
        pts_to_process = coords[:-1] if is_closed else coords

        # 1. Compute centroid from unique vertices
        xs = [pt[0] for pt in pts_to_process]
        ys = [pt[1] for pt in pts_to_process]
        cx = sum(xs) / len(xs)
        cy = sum(ys) / len(ys)

        rad = math.radians(config.rotation_deg)
        cos_theta = math.cos(rad)
        sin_theta = math.sin(rad)

        perturbed = []

        for x, y in pts_to_process:
            # Center around centroid
            dx = x - cx
            dy = y - cy

            # Scale
            dx *= config.scale
            dy *= config.scale

            # Rotate
            rx = dx * cos_theta - dy * sin_theta
            ry = dx * sin_theta + dy * cos_theta

            # Re-translate + shift
            nx = cx + rx + config.shift_x
            ny = cy + ry + config.shift_y

            # Vertex jitter
            if config.vertex_jitter_sigma > 0.0:
                nx += self.rng.gauss(0.0, config.vertex_jitter_sigma)
                ny += self.rng.gauss(0.0, config.vertex_jitter_sigma)

            perturbed.append((round(nx, 4), round(ny, 4)))

        # Close ring if original was closed
        if is_closed and perturbed:
            perturbed.append(perturbed[0])

        return perturbed

    def perturb_geojson(
        self,
        geojson_dict: Dict[str, Any],
        config: PerturbationConfig,
    ) -> Dict[str, Any]:
        """
        Applies perturbation to all Polygon/MultiPolygon features in a GeoJSON dict.
        """
        result = copy.deepcopy(geojson_dict)
        features = result.get("features", [])

        for feat in features:
            geom = feat.get("geometry") or {}
            geom_type = geom.get("type")
            coords = geom.get("coordinates")

            if not coords:
                continue

            if geom_type == "Polygon":
                new_rings = []
                for ring in coords:
                    tuple_ring = [(c[0], c[1]) for c in ring]
                    perturbed_ring = self.perturb_ring(tuple_ring, config)
                    new_rings.append([[p[0], p[1]] for p in perturbed_ring])
                geom["coordinates"] = new_rings

            elif geom_type == "MultiPolygon":
                new_polys = []
                for poly in coords:
                    new_rings = []
                    for ring in poly:
                        tuple_ring = [(c[0], c[1]) for c in ring]
                        perturbed_ring = self.perturb_ring(tuple_ring, config)
                        new_rings.append([[p[0], p[1]] for p in perturbed_ring])
                    new_polys.append(new_rings)
                geom["coordinates"] = new_polys

            # Attach simulation metadata to feature properties
            props = feat.setdefault("properties", {})
            props["_simulated_perturbation"] = {
                "shift_x": config.shift_x,
                "shift_y": config.shift_y,
                "rotation_deg": config.rotation_deg,
                "scale": config.scale,
                "vertex_jitter_sigma": config.vertex_jitter_sigma,
            }

        return result
