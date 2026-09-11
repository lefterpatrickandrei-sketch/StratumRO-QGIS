# -*- coding: utf-8 -*-
"""
StratumRO — Utilitare de Geometrie și Topologie Semantică
==========================================================
Rezolvă problema deformărilor topologice provocate de `_extract_largest_polygon`:
1. `resolve_multipart_geometry`: înlocuiește amputarea oarbă a aripilor de clădire.
   Păstrează componentele semnificative structural (corpuri principale, pavilioane,
   atriumuri, verande) și filtrează micro-zgomotul perimetral (< 8 mp).
2. `split_at_calcan`: detectează și separă corpurile de clădire distincte alipite la
   zid comun (calcan) pe baza concavităților arhitecturale și a profilului de înălțime.
"""

import math
import numpy as np
from typing import List, Optional, Tuple, Union, Any, Callable
from shapely.geometry import Polygon, MultiPolygon, box, LineString, Point
from shapely.ops import unary_union
from shapely.validation import make_valid


def resolve_multipart_geometry(
    geom,
    min_component_area_m2: float = 8.0,
    bridge_max_distance_m: float = 1.8,
    relative_area_threshold: float = 0.12,
    absolute_wing_min_m2: float = 20.0
) -> Optional[Union[Polygon, MultiPolygon]]:
    """
    Rezolvă semantic geometriile compuse (MultiPolygon) fără amputarea aripilor secundare.

    Strategie:
      1. Curăță micro-zgomotul raster / consolele parazite (< min_component_area_m2).
      2. Identifică masa construită principală (A_max).
      3. Păstrează toate aripile și corpurile semnificative structural
         (arie >= 12% din A_max SAU arie >= 20 mp).
      4. În cazul aripilor despărțite de rosturi de dilatație sau curți interioare înguste
         (distanță <= bridge_max_distance_m), aplică închidere morfologică (buffer bridge).
      5. Returnează un Polygon unificat sau un MultiPolygon validat.
    """
    if geom is None or geom.is_empty:
        return None

    geom = make_valid(geom)
    if isinstance(geom, Polygon):
        return geom if geom.area >= min_component_area_m2 else None

    # Colectăm toate poligoanele individuale
    candidates: List[Polygon] = []
    if isinstance(geom, MultiPolygon):
        candidates = list(geom.geoms)
    elif hasattr(geom, "geoms"):
        for g in geom.geoms:
            if isinstance(g, Polygon):
                candidates.append(g)
            elif isinstance(g, MultiPolygon):
                candidates.extend(list(g.geoms))

    # Filtrare zgomot sub 8 mp
    valid_parts = [p for p in candidates if p.is_valid and p.area >= min_component_area_m2]
    if not valid_parts:
        return None
    if len(valid_parts) == 1:
        return valid_parts[0]

    # Sortare după arie descrescătoare
    valid_parts.sort(key=lambda p: p.area, reverse=True)
    primary = valid_parts[0]
    max_area = primary.area

    # Păstrăm componentele semnificative structural
    significant_parts = [primary]
    for p in valid_parts[1:]:
        if (p.area / max_area >= relative_area_threshold) or (p.area >= absolute_wing_min_m2):
            significant_parts.append(p)

    if len(significant_parts) == 1:
        return significant_parts[0]

    # Punte structurală între aripi adiacente (rost dilatație / coridor)
    combined = unary_union(significant_parts)
    if bridge_max_distance_m > 0:
        half_bridge = bridge_max_distance_m / 2.0
        bridged = combined.buffer(half_bridge, join_style=2).buffer(-half_bridge, join_style=2)
        bridged = make_valid(bridged)
        if isinstance(bridged, Polygon) and bridged.area >= min_component_area_m2:
            return bridged
        if isinstance(bridged, MultiPolygon):
            return bridged

    return combined


def extract_largest_polygon_fallback(geom) -> Optional[Polygon]:
    """
    Funcție de compatibilitate retroactivă pentru codul existent.
    Apelează mai întâi `resolve_multipart_geometry`. Dacă rezultatul rămâne MultiPolygon,
    selectează componenta dominantă pentru contextele CAD strict simple.
    """
    resolved = resolve_multipart_geometry(geom)
    if resolved is None or resolved.is_empty:
        return None
    if isinstance(resolved, Polygon):
        return resolved
    if isinstance(resolved, MultiPolygon) and resolved.geoms:
        return max(resolved.geoms, key=lambda g: g.area)
    return None


def _get_reflex_vertices(poly: Polygon) -> List[Tuple[float, float]]:
    """Identifică nodurile concave / reflexe (unghi intern > 180°) dintr-un poligon."""
    coords = list(poly.exterior.coords)[:-1]
    n = len(coords)
    if n < 4:
        return []
    reflex = []
    for i in range(n):
        p_prev = np.array(coords[(i - 1) % n])
        p_curr = np.array(coords[i])
        p_next = np.array(coords[(i + 1) % n])
        v1 = p_curr - p_prev
        v2 = p_next - p_curr
        # Produs vectorial 2D (în sens antiorar, viraj la dreapta = unghi reflex)
        cross = v1[0] * v2[1] - v1[1] * v2[0]
        if cross < -1e-3:
            reflex.append((float(coords[i][0]), float(coords[i][1])))
    return reflex


def split_at_calcan(
    geom: Union[Polygon, MultiPolygon],
    ndsm_path: Optional[str] = "workspace/output/ndsm_stereo70.tif",
    ndsm_callable: Optional[Any] = None,
    min_split_area_m2: float = 350.0,
    min_core_area_m2: float = 50.0,
    min_height_step_m: float = 1.5
) -> List[Polygon]:
    """
    Detectează și separă corpurile de clădire distincte alipite la zid comun (calcan)
    pe baza concavităților arhitecturale, a îngustărilor structurale (gâturi) și a
    profilului altimetric nDSM (trepte de înălțime între corpuri).

    Etape:
      1. Filtrare de arie (clădirile compacte sub min_split_area_m2 nu sunt alterate).
      2. Separare pe gâturi/rosturi de dilatație prin eroziune morfologică (nuclee de clădire).
      3. Separare pe muchie de calcan/treaptă nDSM/rosturi arhitecturale prin identificarea
         liniilor de partaj altimetric sau de îngustare structurală la noduri reflexe.
    """
    import os
    from shapely.ops import split

    if geom is None or geom.is_empty:
        return []

    geom = make_valid(geom)
    if geom.geom_type == 'MultiPolygon':
        res = []
        for g in geom.geoms:
            res.extend(split_at_calcan(g, ndsm_path, ndsm_callable, min_split_area_m2, min_core_area_m2, min_height_step_m))
        return [p for p in res if p.is_valid and p.area >= 25.0]

    if not isinstance(geom, Polygon) or geom.area < min_split_area_m2:
        return [geom] if geom.is_valid and geom.area >= 25.0 else []

    # 1. Detecție gâturi morfologice / rosturi structurale înguste (istm între corpuri mari)
    eroded = geom.buffer(-3.2, join_style=2)
    cores: List[Polygon] = []
    if eroded.geom_type == 'MultiPolygon':
        cores = [c for c in eroded.geoms if c.area >= min_core_area_m2]

    wings: List[Polygon] = []
    if len(cores) >= 2:
        cores.sort(key=lambda c: c.centroid.x)
        div_x = (cores[0].bounds[2] + cores[1].bounds[0]) / 2.0
        cut_line = LineString([(div_x, geom.bounds[1] - 10.0), (div_x, geom.bounds[3] + 10.0)])
        sp = split(geom, cut_line)
        for g in sp.geoms:
            if g.is_valid and g.area >= min_core_area_m2:
                wings.append(g)
    else:
        wings = [geom]

    # Pregătire acces nDSM (fie din fișier raster, fie din funcție apelabilă)
    src = None
    ndsm_data = None
    if ndsm_callable is None and ndsm_path and os.path.exists(ndsm_path):
        try:
            import rasterio
            src = rasterio.open(ndsm_path)
            ndsm_data = src.read(1)
        except Exception:
            src = None
            ndsm_data = None

    def sample_height(x: float, y: float) -> float:
        if ndsm_callable is not None:
            try:
                return float(ndsm_callable(x, y))
            except Exception:
                return 0.0
        if src is not None and ndsm_data is not None:
            try:
                r, c = src.index(x, y)
                if 0 <= r < ndsm_data.shape[0] and 0 <= c < ndsm_data.shape[1]:
                    return float(ndsm_data[r, c])
            except Exception:
                pass
        return 0.0

    has_height_info = (ndsm_callable is not None) or (src is not None)

    # 2. Căutare muchii calcan / notch pe fiecare aripă
    final_bodies: List[Polygon] = []

    for w in wings:
        if w.area < min_split_area_m2 / 1.5:
            final_bodies.append(w)
            continue

        minx, miny, maxx, maxy = w.bounds
        reflex_pts = _get_reflex_vertices(w)
        min_sub_area = max(w.area * 0.15, 60.0)

        # Căutăm tăieturi optime atât pe axa Y (orizontală) cât și pe axa X (verticală)
        # Scanăm coordonatele nodurilor reflexe + eșantioane regulate
        split_found = False

        # --- Axa Y (tăiere orizontală) ---
        y_scan = set([round(pt[1], 1) for pt in reflex_pts if miny + 6.0 <= pt[1] <= maxy - 6.0])
        for y_reg in np.linspace(miny + 8.0, maxy - 8.0, 45):
            y_scan.add(round(y_reg, 1))

        y_evals = []
        for y_cut in sorted(list(y_scan)):
            s_poly = w.intersection(box(minx - 1.0, miny - 1.0, maxx + 1.0, y_cut))
            n_poly = w.intersection(box(minx - 1.0, y_cut, maxx + 1.0, maxy + 1.0))
            if s_poly.area < min_sub_area or n_poly.area < min_sub_area:
                continue

            h_line = LineString([(minx - 5.0, y_cut), (maxx + 5.0, y_cut)])
            inter = w.intersection(h_line)
            w_cut = inter.length if inter and not inter.is_empty else 1.0

            line_s = LineString([(minx - 5.0, y_cut - 3.0), (maxx + 5.0, y_cut - 3.0)])
            line_n = LineString([(minx - 5.0, y_cut + 3.0), (maxx + 5.0, y_cut + 3.0)])
            inter_s = w.intersection(line_s)
            inter_n = w.intersection(line_n)
            w_s = inter_s.length if inter_s and not inter_s.is_empty else w_cut
            w_n = inter_n.length if inter_n and not inter_n.is_empty else w_cut

            narrowing = (w_s + w_n) / (2.0 * max(w_cut, 1.0))

            h_diff = 0.0
            if has_height_info and inter and not inter.is_empty:
                xs = np.linspace(inter.bounds[0], inter.bounds[2], 12)
                hs = [sample_height(x, y_cut - 1.2) for x in xs if w.contains(Point(x, y_cut - 1.2))]
                hn = [sample_height(x, y_cut + 1.2) for x in xs if w.contains(Point(x, y_cut + 1.2))]
                hs = [v for v in hs if v >= 1.5]
                hn = [v for v in hn if v >= 1.5]
                if hs and hn:
                    h_diff = abs(np.mean(hn) - np.mean(hs))

            score = 0.0
            if narrowing > 1.10:
                score += (narrowing - 1.0) * 3.0
            if h_diff >= min_height_step_m:
                score += h_diff * 1.5

            if score > 0.8 or h_diff >= min_height_step_m:
                y_evals.append((y_cut, score))

        best_cut_y = None
        best_score_y = -1.0
        if y_evals:
            max_sy = max(s for _, s in y_evals)
            top_y = [y for y, s in y_evals if s >= max_sy * 0.98]
            best_cut_y = float(np.median(top_y))
            best_score_y = max_sy

        # --- Axa X (tăiere verticală) pentru calcan orientat N-S ---
        x_scan = set([round(pt[0], 1) for pt in reflex_pts if minx + 6.0 <= pt[0] <= maxx - 6.0])
        for x_reg in np.linspace(minx + 8.0, maxx - 8.0, 45):
            x_scan.add(round(x_reg, 1))

        x_evals = []
        for x_cut in sorted(list(x_scan)):
            w_poly = w.intersection(box(minx - 1.0, miny - 1.0, x_cut, maxy + 1.0))
            e_poly = w.intersection(box(x_cut, miny - 1.0, maxx + 1.0, maxy + 1.0))
            if w_poly.area < min_sub_area or e_poly.area < min_sub_area:
                continue

            v_line = LineString([(x_cut, miny - 5.0), (x_cut, maxy + 5.0)])
            inter = w.intersection(v_line)
            l_cut = inter.length if inter and not inter.is_empty else 1.0

            line_w = LineString([(x_cut - 3.0, miny - 5.0), (x_cut - 3.0, maxy + 5.0)])
            line_e = LineString([(x_cut + 3.0, miny - 5.0), (x_cut + 3.0, maxy + 5.0)])
            inter_w = w.intersection(line_w)
            inter_e = w.intersection(line_e)
            l_w = inter_w.length if inter_w and not inter_w.is_empty else l_cut
            l_e = inter_e.length if inter_e and not inter_e.is_empty else l_cut

            narrowing = (l_w + l_e) / (2.0 * max(l_cut, 1.0))

            h_diff = 0.0
            if has_height_info and inter and not inter.is_empty:
                ys = np.linspace(inter.bounds[1], inter.bounds[3], 12)
                hw = [sample_height(x_cut - 1.2, y) for y in ys if w.contains(Point(x_cut - 1.2, y))]
                he = [sample_height(x_cut + 1.2, y) for y in ys if w.contains(Point(x_cut + 1.2, y))]
                hw = [v for v in hw if v >= 1.5]
                he = [v for v in he if v >= 1.5]
                if hw and he:
                    h_diff = abs(np.mean(he) - np.mean(hw))

            score = 0.0
            if narrowing > 1.10:
                score += (narrowing - 1.0) * 3.0
            if h_diff >= min_height_step_m:
                score += h_diff * 1.5

            if score > 0.8 or h_diff >= min_height_step_m:
                x_evals.append((x_cut, score))

        best_cut_x = None
        best_score_x = -1.0
        if x_evals:
            max_sx = max(s for _, s in x_evals)
            top_x = [x for x, s in x_evals if s >= max_sx * 0.98]
            best_cut_x = float(np.median(top_x))
            best_score_x = max_sx

        # Aplicăm cea mai dominantă tăietură dacă este semnificativă
        if best_score_y >= best_score_x and best_cut_y is not None and best_score_y > 0.8:
            cut_h = LineString([(minx - 10.0, best_cut_y), (maxx + 10.0, best_cut_y)])
            sp_h = split(w, cut_h)
            part_s = unary_union([gh for gh in sp_h.geoms if gh.centroid.y < best_cut_y])
            part_n = unary_union([gh for gh in sp_h.geoms if gh.centroid.y >= best_cut_y])
            for p_sub in [part_s, part_n]:
                if p_sub and not p_sub.is_empty and p_sub.area >= 25.0:
                    if p_sub.geom_type == 'MultiPolygon':
                        final_bodies.extend([g for g in p_sub.geoms if g.area >= 25.0])
                    else:
                        final_bodies.append(p_sub)
            split_found = True
        elif best_score_x > best_score_y and best_cut_x is not None and best_score_x > 0.8:
            cut_v = LineString([(best_cut_x, miny - 10.0), (best_cut_x, maxy + 10.0)])
            sp_v = split(w, cut_v)
            part_w = unary_union([gh for gh in sp_v.geoms if gh.centroid.x < best_cut_x])
            part_e = unary_union([gh for gh in sp_v.geoms if gh.centroid.x >= best_cut_x])
            for p_sub in [part_w, part_e]:
                if p_sub and not p_sub.is_empty and p_sub.area >= 25.0:
                    if p_sub.geom_type == 'MultiPolygon':
                        final_bodies.extend([g for g in p_sub.geoms if g.area >= 25.0])
                    else:
                        final_bodies.append(p_sub)
            split_found = True

        if not split_found:
            final_bodies.append(w)

    if src:
        src.close()

    return [b for b in final_bodies if b.is_valid and b.area >= 25.0]

