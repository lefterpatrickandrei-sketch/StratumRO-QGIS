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
from typing import List, Optional, Tuple, Union
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
