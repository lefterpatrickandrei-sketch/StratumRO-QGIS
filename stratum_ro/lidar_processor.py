# -*- coding: utf-8 -*-
"""
Multi-Category LiDAR & nDSM Processing Engine for StratumRO.
Reads real Stereo 70 (.laz/.las) point clouds and DTM rasters,
separates categories based on ASPRS classes & geometric morphology:
  1. Main Buildings (Polygons)
  2. Secondary Outbuildings / Garages (Polygons)
  3. Trees / High Vegetation (Points)
  4. Towers / Utility Poles (Points)
Discards transient ground noise and vehicles.
Features:
  - 3D Structural Feature Tensors (planarity, sphericity, linearity via cKDTree)
  - Vertical Datum Normalization (TransDatRO geoid offset / WGS84 ellipsoid to MN75 normal height)
"""

import os
from typing import Optional, Dict, Any, List, Tuple
import numpy as np
import rasterio
from rasterio.transform import from_origin
from scipy.ndimage import label, find_objects, map_coordinates, maximum_filter
from scipy.spatial import cKDTree
import laspy
from shapely.geometry import Point, Polygon


def compute_3d_structural_features(
    points_xyz: np.ndarray,
    radius_m: float = 1.5,
    min_neighbors: int = 5,
    subsample_max: Optional[int] = None
) -> Dict[str, np.ndarray]:
    """
    Calculează planaritatea, sfericitatea și liniaritatea din tensorul de covarianță geometrică locală.
    Implementat cu scipy.spatial.cKDTree și descompunere spectrală optimizată.

    Indicatori geometrici:
      - Planaritate (c_p): (lambda_2 - lambda_3) / lambda_1 (specifică acoperișurilor plane/în 2 ape > 0.60)
      - Sfericitate (c_s): lambda_3 / lambda_1 (specifică coroanelor de arbori/volumelor 3D difuze > 0.25)
      - Liniaritate (c_l): (lambda_1 - lambda_2) / lambda_1 (specifică cablurilor LEA și stâlpilor zvelți > 0.75)
    """
    n = len(points_xyz)
    if n == 0:
        return {
            "planarity": np.zeros(0, dtype=np.float32),
            "sphericity": np.zeros(0, dtype=np.float32),
            "linearity": np.zeros(0, dtype=np.float32)
        }

    tree = cKDTree(points_xyz)

    # Dacă numărul de puncte depășește subsample_max, procesăm pe un subset de eșantioane
    query_indices = np.arange(n)
    if subsample_max is not None and n > subsample_max:
        query_indices = np.linspace(0, n - 1, subsample_max, dtype=int)
        query_points = points_xyz[query_indices]
    else:
        query_points = points_xyz

    neighbors = tree.query_ball_point(query_points, r=radius_m)

    m = len(query_points)
    planarity = np.zeros(m, dtype=np.float32)
    sphericity = np.zeros(m, dtype=np.float32)
    linearity = np.zeros(m, dtype=np.float32)

    for i, idxs in enumerate(neighbors):
        if len(idxs) < min_neighbors:
            continue
        cluster = points_xyz[idxs]
        centered = cluster - np.mean(cluster, axis=0)
        cov = np.dot(centered.T, centered) / len(idxs)
        evals = np.linalg.eigvalsh(cov)  # Sortat crescător: evals[0] <= evals[1] <= evals[2]

        l3, l2, l1 = evals[0], evals[1], evals[2]
        if l1 > 1e-6:
            planarity[i] = max(0.0, float((l2 - l3) / l1))
            sphericity[i] = max(0.0, float(l3 / l1))
            linearity[i] = max(0.0, float((l1 - l2) / l1))

    # Dacă a fost subsample, împrăștiem rezultatele pe întregul vector de dimensiune n
    if subsample_max is not None and n > subsample_max:
        full_planarity = np.zeros(n, dtype=np.float32)
        full_sphericity = np.zeros(n, dtype=np.float32)
        full_linearity = np.zeros(n, dtype=np.float32)
        full_planarity[query_indices] = planarity
        full_sphericity[query_indices] = sphericity
        full_linearity[query_indices] = linearity
        return {
            "planarity": full_planarity,
            "sphericity": full_sphericity,
            "linearity": full_linearity
        }

    return {
        "planarity": planarity,
        "sphericity": sphericity,
        "linearity": linearity
    }


class LidarProcessor:
    """Extracts categorized features (buildings, trees, poles) from LiDAR and DTM."""

    def __init__(self, laz_path: str, dtm_path: str = None):
        if not os.path.exists(laz_path):
            raise FileNotFoundError(f"LiDAR file not found: {laz_path}")
        self.laz_path = laz_path
        self.dtm_path = dtm_path

    def compute_structural_features(
        self,
        points_xyz: Optional[np.ndarray] = None,
        radius_m: float = 1.5,
        min_neighbors: int = 5,
        subsample_max: Optional[int] = None
    ) -> Dict[str, np.ndarray]:
        """Calculează tensorii structurali 3D (planaritate, sfericitate, liniaritate)."""
        if points_xyz is None:
            las = laspy.read(self.laz_path)
            points_xyz = np.vstack([las.x, las.y, las.z]).T
        return compute_3d_structural_features(points_xyz, radius_m=radius_m, min_neighbors=min_neighbors, subsample_max=subsample_max)

    def process_multicategory(
        self,
        output_ndsm_path: str = None,
        resolution: float = 1.0,
        geoid_offset_m: Optional[float] = None,
        auto_datum_adjust: bool = True
    ) -> dict:
        """
        Executes multi-category extraction from LiDAR.
        Returns separated structures: main buildings, outbuildings, trees, poles.
        Handles vertical datum normalization (TransDatRO) between ellipsoidal heights and MN75 normal heights.
        """
        las = laspy.read(self.laz_path)
        x_all = np.array(las.x)
        y_all = np.array(las.y)
        z_all = np.array(las.z)
        cls_all = np.array(las.classification)

        x_min, x_max = float(las.header.x_min), float(las.header.x_max)
        y_min, y_max = float(las.header.y_min), float(las.header.y_max)

        cols = int(np.ceil((x_max - x_min) / resolution))
        rows = int(np.ceil((y_max - y_min) / resolution))
        transform = from_origin(x_min, y_max, resolution, resolution)

        # Map coordinates to grid indices
        col_indices = np.clip(((x_all - x_min) / resolution).astype(int), 0, cols - 1)
        row_indices = np.clip(((y_max - y_all) / resolution).astype(int), 0, rows - 1)

        # 1. Compute DTM (Terrain)
        dtm = np.zeros((rows, cols), dtype=np.float32)
        if self.dtm_path and os.path.exists(self.dtm_path):
            with rasterio.open(self.dtm_path) as src_dtm:
                dtm_data = src_dtm.read(1).astype(np.float32)
                inv_dtm_transform = ~src_dtm.transform
                c_mesh, r_mesh = np.meshgrid(np.arange(cols), np.arange(rows))
                x_mesh = x_min + (c_mesh + 0.5) * resolution
                y_mesh = y_max - (r_mesh + 0.5) * resolution
                dtm_cols = inv_dtm_transform.a * x_mesh + inv_dtm_transform.b * y_mesh + inv_dtm_transform.c
                dtm_rows = inv_dtm_transform.d * x_mesh + inv_dtm_transform.e * y_mesh + inv_dtm_transform.f
                coords = np.array([dtm_rows.ravel(), dtm_cols.ravel()])
                dtm = map_coordinates(dtm_data, coords, order=1, mode='nearest').reshape((rows, cols))
        else:
            ground_mask = (cls_all == 2)
            if np.any(ground_mask):
                dtm[:] = float(np.percentile(z_all[ground_mask], 5))
            else:
                dtm[:] = float(np.percentile(z_all, 5))

        # 1.1 Verificare și normalizare datum vertical (TransDatRO / Elipsoid WGS84 vs MN75)
        detected_datum_offset = 0.0
        if geoid_offset_m is not None:
            detected_datum_offset = float(geoid_offset_m)
            z_all = z_all - detected_datum_offset
        elif auto_datum_adjust and self.dtm_path and os.path.exists(self.dtm_path):
            ground_mask = (cls_all == 2)
            if not np.any(ground_mask):
                ground_mask = np.ones(len(z_all), dtype=bool)
            sampled_dtm = dtm[row_indices[ground_mask], col_indices[ground_mask]]
            valid = (sampled_dtm > -9000)
            if np.sum(valid) > 20:
                med_diff = float(np.median(z_all[ground_mask][valid] - sampled_dtm[valid]))
                # Dacă diferența este în plaja tipică elipsoid-geoid pentru România (> 15m), aplicăm corecția
                if abs(med_diff) > 15.0:
                    detected_datum_offset = med_diff
                    z_all = z_all - detected_datum_offset
                    print(f"[LidarProcessor] Corectie datum vertical aplicata (TransDatRO offset: {detected_datum_offset:.2f} m).")

        # 2. Extract Complete nDSM (for raster preview)
        flat_indices = row_indices * cols + col_indices
        unique_indices, inv_indices = np.unique(flat_indices, return_inverse=True)
        max_z = np.full(len(unique_indices), -9999.0, dtype=np.float32)
        np.maximum.at(max_z, inv_indices, z_all)
        dsm = np.full((rows, cols), fill_value=np.nan, dtype=np.float32)
        dsm_flat = dsm.ravel()
        dsm_flat[unique_indices] = max_z
        dsm = dsm_flat.reshape((rows, cols))
        mask_nan = np.isnan(dsm)
        if np.any(mask_nan):
            dsm[mask_nan] = dtm[mask_nan]
        ndsm = np.clip(dsm - dtm, 0.0, None)

        # 3. CATEGORIA 1 & 2: CLĂDIRI (Principale vs Anexe) din Clasa 6
        # Dacă clasa 6 este prezentă în fișier, o folosim exclusiv
        has_class_6 = np.any(cls_all == 6)
        if has_class_6:
            building_pts_mask = (cls_all == 6)
        else:
            # Fallback: non-ground cu înălțime > 2.5m excluzând vegetația și solul
            pts_h = z_all - dtm[row_indices, col_indices]
            building_pts_mask = (pts_h >= 2.5) & (~np.isin(cls_all, [2, 3, 4, 5]))

        b_grid = np.zeros((rows, cols), dtype=np.uint8)
        b_c = col_indices[building_pts_mask]
        b_r = row_indices[building_pts_mask]
        b_grid[b_r, b_c] = 1

        lbl_b, num_b = label(b_grid)
        objs_b = find_objects(lbl_b)

        main_buildings_grid = np.zeros((rows, cols), dtype=np.uint8)
        outbuildings_grid = np.zeros((rows, cols), dtype=np.uint8)

        main_count = 0
        outb_count = 0

        for i, sl in enumerate(objs_b, start=1):
            if sl is None:
                continue
            comp_mask = (lbl_b[sl] == i)
            pixel_count = int(np.sum(comp_mask))
            area_m2 = pixel_count * resolution * resolution

            if area_m2 < 8.0:
                continue  # Zgomot parazit / mașină / tomberon

            max_h = float(np.max(ndsm[sl][comp_mask])) if np.any(comp_mask) else 0.0

            # Criteriu separare Cladire Principala vs Anexa gospodareasca
            if area_m2 >= 45.0 or max_h >= 4.5:
                main_buildings_grid[sl][comp_mask] = 1
                main_count += 1
            else:
                outbuildings_grid[sl][comp_mask] = 1
                outb_count += 1

        # Mască globală combinată a clădirilor (inițializată necondiționat pentru arbori și stâlpi)
        building_mask = (main_buildings_grid > 0) | (outbuildings_grid > 0) | (b_grid > 0)

        # 4. CATEGORIA 3: ARBORI (Puncte din Clasa 5 / Vegetatie Inalta)
        tree_pts_mask = np.isin(cls_all, [4, 5])
        tree_points = []

        if np.any(tree_pts_mask):
            tree_grid = np.zeros((rows, cols), dtype=np.float32)
            t_c = col_indices[tree_pts_mask]
            t_r = row_indices[tree_pts_mask]
            t_z = z_all[tree_pts_mask] - dtm[t_r, t_c]
            # Max height per tree grid cell
            flat_t = t_r * cols + t_c
            u_t, inv_t = np.unique(flat_t, return_inverse=True)
            max_tz = np.full(len(u_t), 0.0, dtype=np.float32)
            np.maximum.at(max_tz, inv_t, t_z)
            tree_grid.ravel()[u_t] = max_tz

            # Excludem strict amprenta clădirilor și un tampon de 1 metru pentru a elimina copacii falși pe acoperișuri
            from scipy.ndimage import binary_dilation
            building_exclusion = binary_dilation(building_mask, iterations=1)
            tree_grid[building_exclusion] = 0.0

            # Local maxima filter for distinct tree peaks (fereastra 7x7 metri - diametru coronament standard)
            local_max = (maximum_filter(tree_grid, size=7) == tree_grid) & (tree_grid >= 3.5)
            peak_rows, peak_cols = np.where(local_max)

            for pr, pc in zip(peak_rows, peak_cols):
                h = float(tree_grid[pr, pc])
                if h > 45.0:
                    continue  # Filtrare zgomot altimetric / turnuri / cabluri electrice (>45m)
                gx = float(round(x_min + (pc + 0.5) * resolution, 2))
                gy = float(round(y_max - (pr + 0.5) * resolution, 2))
                r_crown = round(min(max(h * 0.3, 1.5), 6.0), 1)
                tree_points.append({
                    "x": gx,
                    "y": gy,
                    "height_m": round(h, 1),
                    "crown_radius_m": r_crown,
                    "type": "Arbore"
                })

        tree_canopies = []
        for tp in tree_points:
            r_cr = tp["crown_radius_m"]
            poly_crown = Point(tp["x"], tp["y"]).buffer(r_cr, resolution=4)
            tree_canopies.append({
                "x": tp["x"],
                "y": tp["y"],
                "height_m": tp["height_m"],
                "crown_radius_m": r_cr,
                "crown_area_m2": round(float(poly_crown.area), 2),
                "geometry": poly_crown,
                "type": "Coronament_Arbore"
            })

        # 5. CATEGORIA 4: STALPI & TURNURI (Structuri inalte si zvelte)
        pole_pts_mask = (cls_all == 0) | (cls_all == 7)
        pole_points = []
        if np.any(pole_pts_mask):
            pole_r = row_indices[pole_pts_mask]
            pole_c = col_indices[pole_pts_mask]
            pole_h = z_all[pole_pts_mask] - dtm[pole_r, pole_c]
            high_pole = (pole_h >= 8.0)
            if np.any(high_pole):
                for pr, pc, ph in zip(pole_r[high_pole], pole_c[high_pole], pole_h[high_pole]):
                    if building_mask[pr, pc] == 1:
                        continue
                    gx = float(round(x_min + (pc + 0.5) * resolution, 2))
                    gy = float(round(y_max - (pr + 0.5) * resolution, 2))
                    # Evitam duplicate apropiate (< 5m)
                    if not any(abs(gx - p["x"]) < 5.0 and abs(gy - p["y"]) < 5.0 for p in pole_points):
                        pole_points.append({
                            "x": gx,
                            "y": gy,
                            "height_m": round(float(ph), 1),
                            "type": "Turn_Comunicatii" if ph > 18.0 else "Stalp_Inalt"
                        })

        # 6. Salvare nDSM GeoTIFF dacă s-a specificat
        if output_ndsm_path:
            try:
                os.makedirs(os.path.dirname(os.path.abspath(output_ndsm_path)), exist_ok=True)
                with rasterio.open(
                    output_ndsm_path,
                    "w",
                    driver="GTiff",
                    height=rows,
                    width=cols,
                    count=1,
                    dtype=ndsm.dtype,
                    crs="EPSG:3844",
                    transform=transform
                ) as dst:
                    dst.write(ndsm, 1)
            except Exception as e_tif:
                print(f"[LidarProcessor] Nota: nDSM GeoTIFF nu a putut fi suprascris (posibil deschis in QGIS: {e_tif}). Continuam procesarea.")

        return {
            "ndsm": ndsm,
            "transform": transform,
            "crs": "EPSG:3844",
            "resolution": resolution,
            "main_buildings_grid": main_buildings_grid,
            "outbuildings_grid": outbuildings_grid,
            "tree_points": tree_points,
            "tree_canopies": tree_canopies,
            "pole_points": pole_points,
            "detected_datum_offset": detected_datum_offset,
            "counts": {
                "main_buildings": main_count,
                "outbuildings": outb_count,
                "trees": len(tree_points),
                "poles": len(pole_points)
            }
        }
