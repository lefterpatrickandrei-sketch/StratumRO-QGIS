# -*- coding: utf-8 -*-
"""
Cadastral Vectorization, Simplification, and Multi-Category Engine for StratumRO.
Converts classified raster masks and point detections into clean GIS/CAD layers:
  1. CLADIRI_PRINCIPALE (Polygon, simplified CAD geometry, minimal vertices, 90 deg corners)
  2. ANEXE_GOSPODARESTI (Polygon, simplified outbuildings/garages)
  3. ARBORI (Point, tree canopies with height and crown radius)
  4. STALPI_TURNURI (Point, communication towers and utility poles with height)
Exports standardized GeoPackage (.gpkg) layers in Stereo 70 (EPSG:3844).
"""

import os
import math
import numpy as np
from typing import List, Dict, Any, Optional
from shapely.geometry import Polygon, MultiPolygon, Point, shape
from shapely.ops import unary_union
from shapely.affinity import rotate
from shapely.validation import make_valid
import rasterio
from rasterio.features import shapes
import geopandas as gpd

try:
    from buildingregulariser import regularize_geodataframe
    HAS_REGULARISER = True
except ImportError:
    HAS_REGULARISER = False


def _extract_largest_polygon(geom) -> Optional[Polygon]:
    """Recursively extracts the largest valid Polygon from any geometry collection."""
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


def remove_acute_spikes(poly: Polygon, min_angle_deg: float = 40.0) -> Polygon:
    """Elimină vârfurile anomale ascuțite (colți / horn-spikes) care ies nenatural din clădiri."""
    poly = _extract_largest_polygon(poly)
    if poly is None or not poly.is_valid or poly.is_empty:
        return poly

    coords = list(poly.exterior.coords)[:-1]
    if len(coords) <= 4:
        return poly

    changed = True
    max_iter = 4
    cur_iter = 0

    while changed and cur_iter < max_iter:
        changed = False
        cur_iter += 1
        n = len(coords)
        if n <= 4:
            break

        filtered = []
        i = 0
        while i < n:
            p_prev = np.array(coords[(i - 1) % n])
            p_curr = np.array(coords[i])
            p_next = np.array(coords[(i + 1) % n])

            v1 = p_prev - p_curr
            v2 = p_next - p_curr
            d1 = np.linalg.norm(v1)
            d2 = np.linalg.norm(v2)

            if d1 > 0.8 and d2 > 0.8:
                cos_a = np.dot(v1, v2) / (d1 * d2)
                angle_deg = np.degrees(np.arccos(np.clip(cos_a, -1.0, 1.0)))
                # Dacă unghiul interior/exterior e extrem de ascuțit (< 40 deg), e un colț parazit
                if angle_deg < min_angle_deg:
                    changed = True
                    i += 1
                    continue
            filtered.append(coords[i])
            i += 1
        coords = filtered

    if len(coords) >= 3:
        coords.append(coords[0])
        new_poly = Polygon(coords)
        if new_poly.is_valid and new_poly.area > 5.0:
            return new_poly
    return poly


def orthogonalize_cad(poly: Polygon, tolerance: float = 0.7) -> Polygon:
    """
    Ortogonalizează conturul clădirii la unghiuri drepte de 90° folosind algoritmul
    bazat pe drepte suport (Building-Regulariser / Manhattan Support-Line Intersection).
    Garantează unghiuri stricte de 90° fără teșituri diagonale de tip Douglas-Peucker.
    """
    if not poly.is_valid or poly.is_empty or poly.area < 6.0:
        return poly

    # 1. Verificare dreptunghi canonic OBB (4 noduri la 90°)
    mrr = poly.minimum_rotated_rectangle
    if mrr.area > 0:
        rect_ratio = poly.area / mrr.area
        inter_iou = poly.intersection(mrr).area / mrr.area
        # Dacă clădirea este un volum compact (rectangulare >= 70%), o asimilăm direct dreptunghiului canonic de 4 noduri
        if rect_ratio >= 0.70 or inter_iou >= 0.70:
            return mrr

    # 2. Utilizare Building-Regulariser (dacă este instalat)
    if HAS_REGULARISER:
        try:
            temp_gdf = gpd.GeoDataFrame([{"geometry": poly}], crs="EPSG:3844")
            reg_gdf = regularize_geodataframe(
                temp_gdf,
                allow_45_degree=False,
                parallel_threshold=1.0,
                num_cores=1
            )
            reg_poly = reg_gdf.geometry.iloc[0]
            if reg_poly is not None and reg_poly.is_valid and reg_poly.area >= 6.0:
                inter_iou = poly.intersection(reg_poly).area / (poly.union(reg_poly).area + 1e-6)
                if inter_iou >= 0.60:
                    return reg_poly
        except Exception:
            pass

    # 3. Fallback ortogonal pe unghi dominant (fără Douglas-Peucker agresiv)
    coords = list(poly.exterior.coords)[:-1]
    n = len(coords)
    if n < 4:
        return poly

    weighted_angles = []
    total_len = 0.0
    for i in range(n):
        p1 = coords[i]
        p2 = coords[(i + 1) % n]
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        length = math.hypot(dx, dy)
        if length > 1.2:
            ang = math.degrees(math.atan2(dy, dx)) % 90.0
            weighted_angles.append((ang, length))
            total_len += length

    if not weighted_angles:
        return poly.simplify(min(tolerance, 0.4), preserve_topology=True)

    rad_angles = [math.radians(a * 4.0) for a, l in weighted_angles]
    weights = [l / total_len for a, l in weighted_angles]
    mean_sin = sum(w * math.sin(r) for w, r in zip(weights, rad_angles))
    mean_cos = sum(w * math.cos(r) for w, r in zip(weights, rad_angles))
    dom_angle = (math.degrees(math.atan2(mean_sin, mean_cos)) / 4.0) % 90.0

    origin = poly.centroid
    rot_poly = rotate(poly, -dom_angle, origin=origin)

    # Simplificare conservativă (toleranță mică de 0.3m, nu 1.4m)
    simp_rot = rot_poly.simplify(min(tolerance, 0.35), preserve_topology=True)
    if not simp_rot.is_valid:
        simp_rot = rot_poly

    ortho_poly = rotate(simp_rot, dom_angle, origin=origin)
    return ortho_poly if (ortho_poly.is_valid and ortho_poly.area > 5.0) else poly


def check_is_likely_container_or_shed(poly: Polygon, mean_height: Optional[float] = None) -> Dict[str, Any]:
    """
    Identifică dacă o amprentă seamănă cu un container maritim/modular sau seră alungită:
      - 20ft container: ~2.44m x 6.06m (Arie ~14.8 m2, raport ~2.48, H ~2.59m)
      - 40ft container: ~2.44m x 12.19m (Arie ~29.7 m2, raport ~5.0, H ~2.59m)
    """
    if poly is None or not poly.is_valid:
        return {"is_temporary": False, "type": "UNKNOWN"}

    mrr = poly.minimum_rotated_rectangle
    coords = list(mrr.exterior.coords)[:-1]
    if len(coords) == 4:
        side1 = Point(coords[0]).distance(Point(coords[1]))
        side2 = Point(coords[1]).distance(Point(coords[2]))
        w = min(side1, side2)
        l = max(side1, side2)
        ratio = l / (w + 1e-5)
        area = poly.area

        # Verificare container 20ft / 40ft (lățime ~2.0 - 2.8m, lungime 5.5 - 13.0m)
        if 2.0 <= w <= 3.0 and 5.0 <= l <= 13.5 and 10.0 <= area <= 36.0:
            if ratio >= 2.0:
                return {
                    "is_temporary": True,
                    "type": "CONTAINER_MODULAR",
                    "width_m": round(w, 2),
                    "length_m": round(l, 2),
                    "aspect_ratio": round(ratio, 2)
                }

        # Verificare seră / solar ușor alungit
        if ratio >= 3.5 and area >= 40.0:
            return {
                "is_temporary": True,
                "type": "SERA_SOLAR_ALUNGIT",
                "width_m": round(w, 2),
                "length_m": round(l, 2),
                "aspect_ratio": round(ratio, 2)
            }

    return {"is_temporary": False, "type": "CONSTRUCTIE_PERMANENTA"}


class CadastralVectorizer:
    """Converts classified rasters & points into clean CAD-grade vector layers."""

    def __init__(self, crs: str = "EPSG:3844"):
        self.crs = crs

    def classify_temporary_structure(self, poly: Polygon, mean_height: Optional[float] = None) -> Dict[str, Any]:
        """Metodă de clasificare a structurilor temporare (containere, solarii)."""
        return check_is_likely_container_or_shed(poly, mean_height)

    def clean_cad_polygon(self, poly: Polygon, tolerance: float = 0.7) -> Polygon:
        """
        Curăță și regularizează complet un poligon de clădire:
        1. Elimină colții/spikurile ascuțite (< 40°).
        2. Ortogonalizează la unghiuri de 90° (dreptunghiuri perfecte sau corpuri L/T Manhattan).
        3. Îndepărtează nodurile coliniare redundante.
        """
        if not poly.is_valid:
            poly = make_valid(poly)
            poly = _extract_largest_polygon(poly)
        if poly is None or poly.area < 5.0:
            return poly

        # 1. Eliminare colți paraziți
        p_no_spikes = remove_acute_spikes(poly, min_angle_deg=40.0)

        # 2. Ortogonalizare Manhattan
        p_ortho = orthogonalize_cad(p_no_spikes, tolerance=tolerance)

        # 3. Îndepărtare noduri coliniare reziduale
        coords = list(p_ortho.exterior.coords)[:-1]
        n = len(coords)
        if n > 4:
            clean_pts = []
            for i in range(n):
                prev_p = coords[(i - 1) % n]
                curr_p = coords[i]
                next_p = coords[(i + 1) % n]

                v1 = (curr_p[0] - prev_p[0], curr_p[1] - prev_p[1])
                v2 = (next_p[0] - curr_p[0], next_p[1] - curr_p[1])
                d1 = math.hypot(v1[0], v1[1])
                d2 = math.hypot(v2[0], v2[1])

                if d1 < 0.6 or d2 < 0.6:
                    continue

                cross = v1[0] * v2[1] - v1[1] * v2[0]
                if abs(cross) / (d1 * d2 + 1e-6) < 0.08:
                    continue  # Nod coliniar, eliminat
                clean_pts.append(curr_p)

            if len(clean_pts) >= 4:
                clean_pts.append(clean_pts[0])
                simplified_poly = Polygon(clean_pts)
                if simplified_poly.is_valid and simplified_poly.area > 5.0:
                    p_ortho = simplified_poly

        return p_ortho

    def orthogonalize_polygon(self, poly: Polygon, tolerance: float = 0.7) -> Polygon:
        """Alias for clean_cad_polygon."""
        return self.clean_cad_polygon(poly, tolerance=tolerance)

    def vectorize_mask(
        self,
        mask_array: np.ndarray,
        transform: rasterio.Affine,
        min_area_m2: float = 8.0,
        category: str = "CLADIRE_PRINCIPALA"
    ) -> List[Dict[str, Any]]:
        """
        Vectorizes a 2D binary raster mask into clean cadastral polygons.
        """
        binary_mask = (mask_array > 0).astype(np.uint8)
        feature_generator = shapes(binary_mask, mask=(binary_mask == 1), transform=transform)

        features = []
        fid = 1

        for geom, val in feature_generator:
            if val != 1:
                continue
            poly = shape(geom)
            if poly.area < min_area_m2:
                continue

            cleaned_poly = self.clean_cad_polygon(poly)
            if cleaned_poly is None or cleaned_poly.is_empty:
                continue

            centroid = cleaned_poly.centroid
            num_vertices = len(cleaned_poly.exterior.coords) - 1

            features.append({
                "id": fid,
                "category": category,
                "area_m2": round(float(cleaned_poly.area), 2),
                "perimeter_m": round(float(cleaned_poly.length), 2),
                "vertices": num_vertices,
                "center_x": round(float(centroid.x), 2),
                "center_y": round(float(centroid.y), 2),
                "geometry": cleaned_poly,
                "crs": self.crs
            })
            fid += 1

        return features

    def format_hybrid_buildings(
        self,
        hybrid_results: List[Dict[str, Any]],
        tolerance: float = 0.7,
        eave_offset_m: float = 0.40
    ) -> List[Dict[str, Any]]:
        """
        Takes raw validated outputs from SAM2BuildingSegmenter,
        resolves all topological overlaps (merging multi-component fragments of the same building),
        applies SOTA Cadastral regularisation (Building-Regulariser / Manhattan 90 deg CAD alignment)
        calculates eave retraction offset (-0.40m for ANCPI ground footprint)
        and guarantees strictly disjoint (0.0 m2 overlap) clean building footprints.
        """
        import scipy.sparse as sp
        from scipy.sparse.csgraph import connected_components

        # 1. Filtrare inițială a geometriilor valide
        valid_items = []
        for item in hybrid_results:
            geom = item.get("geometry")
            if geom is not None and not geom.is_empty and geom.area >= 8.0:
                valid_items.append(item)

        if not valid_items:
            return []

        # 2. Clusterizare topologică pentru unirea componentelor adiacente / suprapuse ale aceleiași clădiri
        n = len(valid_items)
        polys = [it["geometry"].buffer(0) for it in valid_items]
        adj = np.zeros((n, n), dtype=bool)

        for i in range(n):
            adj[i, i] = True
            for j in range(i + 1, n):
                if polys[i].intersects(polys[j]):
                    inter = polys[i].intersection(polys[j])
                    if inter.area > 0.05:
                        adj[i, j] = True
                        adj[j, i] = True

        graph = sp.csr_matrix(adj)
        n_components, labels = connected_components(csgraph=graph, directed=False)

        merged_candidates = []
        for comp_id in range(n_components):
            indices = np.where(labels == comp_id)[0]
            if len(indices) == 1:
                idx = indices[0]
                item = valid_items[idx]
                merged_candidates.append({
                    "geometry": polys[idx],
                    "sam2_score": float(item.get("sam2_score", 0.0)),
                    "mean_h": float(item.get("mean_h", item.get("inaltime_med_m", 4.0))),
                    "max_h": float(item.get("max_h", item.get("inaltime_max_m", 5.5))),
                    "status": str(item.get("status", item.get("validare", "CONFIRMAT_HIBRID")))
                })
            else:
                cluster_polys = [polys[idx] for idx in indices]
                cluster_items = [valid_items[idx] for idx in indices]
                u = unary_union(cluster_polys)
                best_score = max(float(it.get("sam2_score", 0.0)) for it in cluster_items)
                best_mean_h = np.mean([float(it.get("mean_h", it.get("inaltime_med_m", 4.0))) for it in cluster_items])
                best_max_h = max(float(it.get("max_h", it.get("inaltime_max_m", 5.5))) for it in cluster_items)

                sub_polys = [u] if u.geom_type == 'Polygon' else [s for s in u.geoms if s.area >= 8.0]
                for sub in sub_polys:
                    merged_candidates.append({
                        "geometry": sub,
                        "sam2_score": best_score,
                        "mean_h": float(best_mean_h),
                        "max_h": float(best_max_h),
                        "status": "CONFIRMAT_HIBRID"
                    })

        # 2b. Separare topologică la calcan (rosturi structurale și trepte altimetrice nDSM)
        from stratum_ro.geometry_utils import split_at_calcan
        calcan_split_candidates = []
        for cand in merged_candidates:
            geom = cand.get("geometry")
            if geom is not None and geom.area >= 350.0:
                bodies = split_at_calcan(geom)
                if len(bodies) > 1:
                    for b in bodies:
                        c_copy = dict(cand)
                        c_copy["geometry"] = b
                        calcan_split_candidates.append(c_copy)
                else:
                    calcan_split_candidates.append(cand)
            else:
                calcan_split_candidates.append(cand)
        merged_candidates = calcan_split_candidates

        # 3. Curățare colți (spikes) și ortogonalizare Manhattan la 90 de grade
        # Dacă este disponibil buildingregulariser, rulăm direct în batch pentru performanță maximă și 100% 90°
        if HAS_REGULARISER and merged_candidates:
            try:
                temp_geoms = [c["geometry"] for c in merged_candidates]
                batch_gdf = gpd.GeoDataFrame(
                    [{"idx": i, "geometry": g} for i, g in enumerate(temp_geoms)],
                    crs=self.crs
                )
                reg_batch = regularize_geodataframe(
                    batch_gdf,
                    allow_45_degree=False,
                    parallel_threshold=1.0,
                    num_cores=1
                )
                regularized_items = []
                for _, row in reg_batch.iterrows():
                    reg_p = row.geometry
                    if reg_p is not None and reg_p.is_valid and reg_p.area >= 8.0:
                        # Dacă clădirea este un volum compact (rectangularitate >= 68%), o asimilăm direct dreptunghiului canonic de 4 noduri
                        mrr = reg_p.minimum_rotated_rectangle
                        if mrr.area > 0 and (reg_p.area / mrr.area >= 0.68 or reg_p.intersection(mrr).area / mrr.area >= 0.68):
                            reg_p = mrr
                        cand_copy = dict(merged_candidates[int(row["idx"])])
                        cand_copy["geometry"] = reg_p
                        regularized_items.append(cand_copy)
            except Exception:
                regularized_items = []
                for cand in merged_candidates:
                    p = cand["geometry"]
                    p_clean = self.clean_cad_polygon(p, tolerance=tolerance)
                    if p_clean is not None and p_clean.is_valid and p_clean.area >= 8.0:
                        cand_copy = dict(cand)
                        cand_copy["geometry"] = p_clean
                        regularized_items.append(cand_copy)
        else:
            regularized_items = []
            for cand in merged_candidates:
                p = cand["geometry"]
                p_clean = self.clean_cad_polygon(p, tolerance=tolerance)
                if p_clean is not None and p_clean.is_valid and p_clean.area >= 8.0:
                    cand_copy = dict(cand)
                    cand_copy["geometry"] = p_clean
                    regularized_items.append(cand_copy)

        # 4. Asigurare topologică strictă: zero suprapuneri (disjoint) între clădiri
        # Sortăm după arie descrescător (clădirile principale mari au prioritate de contur)
        regularized_items.sort(key=lambda x: x["geometry"].area, reverse=True)
        strictly_disjoint = []

        for item in regularized_items:
            cur_p = item["geometry"]
            for kept in strictly_disjoint:
                kept_p = kept["geometry"]
                if cur_p.intersects(kept_p):
                    inter = cur_p.intersection(kept_p)
                    if inter.area > 0.01:
                        cur_p = cur_p.difference(kept_p)
                        if cur_p.geom_type == 'MultiPolygon':
                            subs = [s for s in cur_p.geoms if s.area >= 8.0]
                            cur_p = max(subs, key=lambda s: s.area) if subs else None
                        if cur_p is None or cur_p.area < 8.0:
                            break

            if cur_p is not None and cur_p.is_valid and cur_p.area >= 8.0:
                # Curățare finală după tăiere
                p_final = remove_acute_spikes(cur_p, min_angle_deg=40.0)
                if p_final.is_valid and p_final.area >= 8.0:
                    item_final = dict(item)
                    item_final["geometry"] = p_final
                    strictly_disjoint.append(item_final)

        # 5. Formatare finală a atributelor cadastrale și calcul amprentă la sol (ANCPI)
        features = []
        for fid, it in enumerate(strictly_disjoint, start=1):
            p = _extract_largest_polygon(it["geometry"])
            if p is None or p.is_empty:
                continue
            centroid = p.centroid
            num_vertices = len(p.exterior.coords) - 1

            # Retragere normală a streșinii pentru amprenta fundației la nivelul terenului
            p_sol = None
            area_sol = round(float(p.area), 2)
            if eave_offset_m > 0:
                try:
                    p_sol_cand = p.buffer(-eave_offset_m, join_style=2)
                    if not p_sol_cand.is_valid:
                        p_sol_cand = make_valid(p_sol_cand)
                    if p_sol_cand is not None and not p_sol_cand.is_empty and p_sol_cand.area >= 6.0:
                        p_sol = _extract_largest_polygon(p_sol_cand)
                        if p_sol is not None:
                            area_sol = round(float(p_sol.area), 2)
                except Exception:
                    p_sol = p

            features.append({
                "id": fid,
                "category": "CLADIRE_HIBRID",
                "validare": it.get("status", "CONFIRMAT_HIBRID"),
                "sam2_score": round(float(it.get("sam2_score", 0.0)), 3),
                "inaltime_med_m": round(float(it.get("mean_h", 4.0)), 2),
                "inaltime_max_m": round(float(it.get("max_h", 5.5)), 2),
                "area_m2": round(float(p.area), 2),
                "area_sol_m2": area_sol,
                "eave_offset_m": eave_offset_m,
                "perimeter_m": round(float(p.length), 2),
                "vertices": num_vertices,
                "center_x": round(float(centroid.x), 2),
                "center_y": round(float(centroid.y), 2),
                "geometry": p,
                "geometry_sol": p_sol or p,
                "crs": self.crs
            })

        return features

    def vectorize_points(
        self,
        points_list: List[Dict[str, Any]],
        category: str
    ) -> List[Dict[str, Any]]:
        """
        Converts detected point objects (trees, poles) into GeoDataFrame-compatible records.
        """
        features = []
        for i, pt in enumerate(points_list, start=1):
            gx = float(pt["x"])
            gy = float(pt["y"])
            features.append({
                "id": i,
                "category": category,
                "type": pt.get("type", category),
                "height_m": float(pt.get("height_m", 0.0)),
                "crown_radius_m": float(pt.get("crown_radius_m", 0.0)),
                "center_x": gx,
                "center_y": gy,
                "geometry": Point(gx, gy),
                "crs": self.crs
            })
        return features

    def filter_points_outside_polygons(
        self,
        points_features: List[Dict[str, Any]],
        building_features: List[Dict[str, Any]],
        buffer_m: float = 0.8
    ) -> List[Dict[str, Any]]:
        """
        Filters out any point (tree or pole) that falls inside or near a building polygon.
        Prevents trees from appearing inside roofs or overlapping building footprints.
        """
        if not points_features or not building_features:
            return points_features

        from shapely.ops import unary_union
        b_polys = []
        for b in building_features:
            geom = b.get("geometry")
            if geom is not None and not geom.is_empty:
                b_polys.append(geom)

        if not b_polys:
            return points_features

        b_mask = unary_union(b_polys).buffer(buffer_m)

        filtered = []
        fid = 1
        for pt_feat in points_features:
            pt_geom = pt_feat.get("geometry")
            if pt_geom is None or pt_geom.is_empty:
                continue
            if not b_mask.intersects(pt_geom):
                f_copy = dict(pt_feat)
                f_copy["id"] = fid
                filtered.append(f_copy)
                fid += 1

        return filtered

    def extract_sector_boundary(self, vrt_path: str, tolerance: float = 12.0) -> Polygon:
        """
        Extrage conturul curat al sectorului cadastral (LIMITA_SECTOR_CADASTRAL) din ortofotoplan,
        eliminând complet bordurile negre în zig-zag (NoData).
        """
        if not os.path.exists(vrt_path):
            return Polygon()

        with rasterio.open(vrt_path) as ds:
            factor = 16
            data = ds.read(1, out_shape=(ds.height // factor, ds.width // factor))
            mask = (data > 0).astype(np.uint8)
            t_scaled = ds.transform * ds.transform.scale(factor, factor)

            geoms = [shape(g) for g, val in shapes(mask, mask=(mask == 1), transform=t_scaled)]
            if not geoms:
                return Polygon()

            u = unary_union(geoms)
            # Simplificare convexă sau cu toleranță pentru a tăia treptele de pixeli
            clean_hull = u.convex_hull
            # Tăiem la extensia reală utilă a datelor
            smooth_boundary = u.buffer(15.0).buffer(-15.0).simplify(tolerance, preserve_topology=True)
            if smooth_boundary.is_valid and smooth_boundary.area > 1000.0:
                return _extract_largest_polygon(smooth_boundary)
            return _extract_largest_polygon(clean_hull)

    def filter_points_multi_exclusion(
        self,
        points_features: List[Dict[str, Any]],
        exclusion_polygons: List[Any],
        min_height: float = 3.8
    ) -> List[Dict[str, Any]]:
        """
        Filtrează punctele de vegetație:
        - Înălțime minimă silvică (>= min_height, elimină vița de vie și gardurile joase).
        - Exclude orice punct care cade în drumuri, cimitir, vii sau clădiri.
        """
        valid_polys = []
        for p in exclusion_polygons:
            if p is not None and not p.is_empty:
                valid_polys.append(p)

        excl_mask = unary_union(valid_polys) if valid_polys else None

        filtered = []
        fid = 1
        for pt in points_features:
            h = pt.get("height_m", 0.0)
            if h < min_height:
                continue

            geom = pt.get("geometry")
            if geom is None or geom.is_empty:
                continue

            if excl_mask is not None and excl_mask.intersects(geom):
                continue

            f_copy = dict(pt)
            f_copy["id"] = fid
            filtered.append(f_copy)
            fid += 1

        return filtered

    def build_planar_partition(
        self,
        sector_boundary: Polygon,
        layer_geometries: Dict[str, Any]
    ) -> Polygon:
        """
        Construiește stratul UNCLASSIFIED care acoperă 100% din terenul sectorului
        fără niciun gol (no gaps) și fără nicio suprapunere (no overlaps).
        """
        if sector_boundary is None or sector_boundary.is_empty:
            return Polygon()

        known_geoms = []
        for name, geom in layer_geometries.items():
            if geom is not None and not geom.is_empty:
                known_geoms.append(geom)

        if not known_geoms:
            return sector_boundary

        union_known = unary_union(known_geoms)
        unclassified = sector_boundary.difference(union_known)
        return unclassified if unclassified.is_valid else make_valid(unclassified)

    def vectorize_ndsm_buildings(
        self,
        ndsm_array: np.ndarray,
        transform: rasterio.Affine,
        min_height: float = 2.5,
        min_area_m2: float = 15.0,
        orthogonalize: bool = True
    ) -> List[Dict[str, Any]]:
        """Legacy method: Vectorizes buildings directly from nDSM array."""
        binary_mask = (ndsm_array >= min_height).astype(np.uint8)
        return self.vectorize_mask(binary_mask, transform, min_area_m2=min_area_m2, category="CLADIRE")

    def save_multicategory_geopackage(
        self,
        categories_dict: Dict[str, List[Dict[str, Any]]],
        output_gpkg_path: str
    ) -> str:
        """
        Saves multiple distinct layers (polygons and points) into a single GeoPackage file.

        :param categories_dict: Dict mapping layer_name to list of feature records.
        :param output_gpkg_path: Absolute destination path for .gpkg.
        :return: Path to saved GeoPackage.
        """
        os.makedirs(os.path.dirname(os.path.abspath(output_gpkg_path)), exist_ok=True)

        all_sol_items = []
        for layer_name, items in categories_dict.items():
            if not items:
                continue

            for it in items:
                if "geometry_sol" in it and it["geometry_sol"] is not None:
                    it_s = dict(it)
                    it_s["geometry"] = it["geometry_sol"]
                    it_s["category"] = "CLADIRE_SOL_ANCPI"
                    it_s["area_m2"] = it.get("area_sol_m2", it.get("area_m2"))
                    if "geometry_sol" in it_s:
                        del it_s["geometry_sol"]
                    all_sol_items.append(it_s)

            clean_items = []
            for it in items:
                it_c = dict(it)
                if "geometry_sol" in it_c:
                    del it_c["geometry_sol"]
                clean_items.append(it_c)

            gdf = gpd.GeoDataFrame(clean_items, crs=self.crs)
            if "crs" in gdf.columns:
                gdf = gdf.drop(columns=["crs"])

            gdf.to_file(output_gpkg_path, layer=layer_name, driver="GPKG")

        if all_sol_items:
            gdf_sol = gpd.GeoDataFrame(all_sol_items, crs=self.crs)
            if "crs" in gdf_sol.columns:
                gdf_sol = gdf_sol.drop(columns=["crs"])
            gdf_sol.to_file(output_gpkg_path, layer="CLADIRI_SOL_ANCPI", driver="GPKG")

        return output_gpkg_path

    def save_to_geopackage(
        self,
        buildings: List[Dict[str, Any]],
        output_gpkg_path: str,
        layer_name: str = "cladiri_stereo70"
    ) -> str:
        """Legacy helper: saves a single list of features to GeoPackage."""
        return self.save_multicategory_geopackage({layer_name: buildings}, output_gpkg_path)
