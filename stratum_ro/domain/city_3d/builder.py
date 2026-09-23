# -*- coding: utf-8 -*-
"""
3D Volumetric Extrusion (LoD1) & Roof Geometry Reconstruction (LoD2) for StratumRO.
Converts 2D cadastral building footprints into true 3D watertight geometries:
  - GeoPackage 3D MultiPolygonZ (natively rendered in QGIS 3D Map View)
  - CityJSON v1.1 OGC open standard export
  - RANSAC 3D planar fitting for roof ridge & slope estimation
"""

import os
import json
import math
from typing import List, Dict, Any, Tuple, Optional
import numpy as np
from shapely.geometry import Polygon, MultiPolygon


def _extract_polygons(geom) -> List[Polygon]:
    """Extracts all individual 2D Polygon instances from geometry."""
    if geom is None or geom.is_empty:
        return []
    if isinstance(geom, Polygon):
        return [geom]
    if isinstance(geom, MultiPolygon):
        return list(geom.geoms)
    if hasattr(geom, "geoms"):
        res = []
        for g in geom.geoms:
            res.extend(_extract_polygons(g))
        return res
    return []


class Volumetric3DBuilder:
    """Builds true 3D (PolygonZ / MultiPolygonZ) building models from 2D footprints & LiDAR heights."""

    def __init__(self, default_ground_z: float = 345.0):
        self.default_ground_z = default_ground_z

    def extrude_lod1_solid(
        self,
        poly_2d: Polygon,
        height_m: float,
        ground_z: Optional[float] = None
    ) -> Optional[MultiPolygon]:
        """
        Extrudes a 2D Polygon into a complete 3D watertight solid shell (MultiPolygonZ).
        Consists of:
          1. Floor polygon at Z = ground_z
          2. Roof polygon at Z = ground_z + height_m
          3. Vertical wall polygons connecting each exterior coordinate
        """
        if poly_2d is None or poly_2d.is_empty or poly_2d.area < 2.0:
            return None

        z_base = float(self.default_ground_z if ground_z is None else ground_z)
        z_roof = z_base + max(float(height_m), 1.5)

        coords_2d = list(poly_2d.exterior.coords)
        if len(coords_2d) < 4:
            return None

        # Clean non-duplicate base coordinates
        base_pts = coords_2d[:-1]
        n = len(base_pts)

        faces: List[Polygon] = []

        # 1. Podea (Floor face at z_base)
        floor_3d = [(p[0], p[1], z_base) for p in coords_2d]
        faces.append(Polygon(floor_3d))

        # 2. Tavan / Acoperiș (Roof face at z_roof)
        roof_3d = [(p[0], p[1], z_roof) for p in coords_2d]
        faces.append(Polygon(roof_3d))

        # 3. Pereți verticali (Vertical wall quadrilateral faces)
        for i in range(n):
            p1 = base_pts[i]
            p2 = base_pts[(i + 1) % n]

            wall_coords = [
                (p1[0], p1[1], z_base),
                (p2[0], p2[1], z_base),
                (p2[0], p2[1], z_roof),
                (p1[0], p1[1], z_roof),
                (p1[0], p1[1], z_base)
            ]
            faces.append(Polygon(wall_coords))

        return MultiPolygon(faces)

    def create_lod1_roof_surface(
        self,
        poly_2d: Polygon,
        height_m: float,
        ground_z: Optional[float] = None
    ) -> Optional[Polygon]:
        """Creates a horizontal 3D roof plane (PolygonZ) at Z = ground_z + height_m."""
        if poly_2d is None or poly_2d.is_empty:
            return None
        z_roof = (self.default_ground_z if ground_z is None else ground_z) + max(float(height_m), 1.5)
        coords_3d = [(p[0], p[1], z_roof) for p in poly_2d.exterior.coords]
        return Polygon(coords_3d)

    def estimate_lod2_roof_planes(
        self,
        roof_points_xyz: np.ndarray,
        ransac_threshold: float = 0.25,
        max_iterations: int = 150
    ) -> Dict[str, Any]:
        """
        Estimates roof plane orientation using RANSAC 3D plane fitting.
        Ax + By + Cz + D = 0 -> normal vector (A, B, C).
        Returns roof typology, slope in degrees, and ridge elevation.
        """
        if roof_points_xyz is None or len(roof_points_xyz) < 6:
            return {
                "tip_acoperis": "TERASA_LOD1",
                "panta_grade": 0.0,
                "z_coama": float(np.mean(roof_points_xyz[:, 2])) if roof_points_xyz is not None and len(roof_points_xyz) > 0 else 0.0
            }

        pts = roof_points_xyz[:, :3]
        n_pts = len(pts)
        best_inliers = 0
        best_plane = None

        np.random.seed(42)
        for _ in range(max_iterations):
            idx = np.random.choice(n_pts, 3, replace=False)
            p1, p2, p3 = pts[idx[0]], pts[idx[1]], pts[idx[2]]

            v1 = p2 - p1
            v2 = p3 - p1
            normal = np.cross(v1, v2)
            norm_len = np.linalg.norm(normal)
            if norm_len < 1e-6:
                continue
            normal = normal / norm_len
            d = -np.dot(normal, p1)

            # Distanțe de la toate punctele la plan
            dists = np.abs(np.dot(pts, normal) + d)
            inliers = int(np.sum(dists < ransac_threshold))

            if inliers > best_inliers:
                best_inliers = inliers
                best_plane = (normal, d)

        if best_plane is not None:
            norm, d = best_plane
            # Asigurăm că normala este orientată în sus
            if norm[2] < 0:
                norm = -norm
            # Unghiul cu planul orizontal (axa Z)
            cos_tilt = np.clip(norm[2], -1.0, 1.0)
            tilt_deg = float(np.degrees(np.arccos(cos_tilt)))

            max_z = float(np.max(pts[:, 2]))

            tip = "TERASA" if tilt_deg < 8.0 else ("DOUA_APE" if tilt_deg < 45.0 else "MANSARDA_INCLINATA")
            return {
                "tip_acoperis": tip,
                "panta_grade": round(tilt_deg, 1),
                "z_coama": round(max_z, 2),
                "inliers_ratio": round(best_inliers / n_pts, 2)
            }

        return {
            "tip_acoperis": "TERASA_LOD1",
            "panta_grade": 0.0,
            "z_coama": round(float(np.max(pts[:, 2])), 2)
        }

    def export_cityjson(
        self,
        buildings_lod1: List[Dict[str, Any]],
        output_cityjson_path: str,
        epsg_code: int = 3844
    ) -> str:
        """
        Exports 3D LoD1 buildings to standard OGC CityJSON v1.1 format.
        Compatible with 3DBAG viewers, cjio CLI, and Cesium.
        """
        os.makedirs(os.path.dirname(os.path.abspath(output_cityjson_path)), exist_ok=True)

        vertices: List[List[float]] = []
        vertex_lookup: Dict[Tuple[float, float, float], int] = {}

        def get_v_idx(x: float, y: float, z: float) -> int:
            key = (round(x, 3), round(y, 3), round(z, 3))
            if key not in vertex_lookup:
                idx = len(vertices)
                vertices.append([key[0], key[1], key[2]])
                vertex_lookup[key] = idx
            return vertex_lookup[key]

        city_objects: Dict[str, Any] = {}

        for b_idx, b in enumerate(buildings_lod1, start=1):
            bldg_id = b.get("cod_cladire", f"BLDG_{b_idx:04d}")
            geom = b.get("geometry")
            polys = _extract_polygons(geom)
            if not polys:
                continue

            poly = polys[0]
            h_cornisa = float(b.get("h_cornisa_m", 5.0))
            z_ground = float(b.get("z_sol_m", self.default_ground_z))
            z_roof = z_ground + h_cornisa

            coords_2d = list(poly.exterior.coords)[:-1]
            n = len(coords_2d)
            boundaries: List[List[List[int]]] = []

            # Podea
            floor_v = [get_v_idx(p[0], p[1], z_ground) for p in coords_2d[::-1]]
            boundaries.append([floor_v])

            # Acoperiș
            roof_v = [get_v_idx(p[0], p[1], z_roof) for p in coords_2d]
            boundaries.append([roof_v])

            # Pereți
            for i in range(n):
                p1 = coords_2d[i]
                p2 = coords_2d[(i + 1) % n]
                wall_v = [
                    get_v_idx(p1[0], p1[1], z_ground),
                    get_v_idx(p2[0], p2[1], z_ground),
                    get_v_idx(p2[0], p2[1], z_roof),
                    get_v_idx(p1[0], p1[1], z_roof)
                ]
                boundaries.append([wall_v])

            city_objects[bldg_id] = {
                "type": "Building",
                "attributes": {
                    "measuredHeight": round(h_cornisa, 1),
                    "elevationGround": round(z_ground, 1),
                    "groundArea_m2": round(float(poly.area), 2),
                    "regim_inaltime": b.get("regim_inaltime", "P+1E")
                },
                "geometry": [{
                    "type": "Solid",
                    "lod": "1.2",
                    "boundaries": [boundaries]
                }]
            }

        cityjson_data = {
            "type": "CityJSON",
            "version": "1.1",
            "metadata": {
                "referenceSystem": f"https://www.opengis.net/def/crs/EPSG/0/{epsg_code}",
                "title": "StratumRO 3D Cadastral City Model (Stereo 70)",
                "datasetProvider": "StratumRO MLOps Geomatics Engine"
            },
            "CityObjects": city_objects,
            "vertices": vertices
        }

        with open(output_cityjson_path, "w", encoding="utf-8") as f:
            json.dump(cityjson_data, f, indent=2)

        return output_cityjson_path
