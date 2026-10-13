# -*- coding: utf-8 -*-
"""
StratumRO: Complete Hybrid Sensor Fusion Pipeline (LiDAR + Orthophoto + ANCPI Cadastre v3)
Processes Cluj USAMV study area (8 MrSID tiles, 4.62M LiDAR points).
Integrates:
  - Canonical 4-vertex orthogonal building regularization (90° right angles)
  - Eave retraction offset (-0.40m) for ANCPI ground footprints (CLADIRI_SOL_ANCPI)
  - Clean Cadastral Sector boundary (LIMITA_SECTOR_CADASTRAL) cutting NoData ragged stairs
  - Multi-class land use extraction (DR, HR, VN, CIMITIR, A)
  - Continuous 100% planar partition without gaps or overlaps (UNCLASSIFIED)
  - Rigorous tree filtering excluding roads, vineyards, cemeteries, and roofs
  - Standardized GeoPackage (cladiri_stereo70.gpkg) and AutoCAD DXF (cadastru_ancpi.dxf) export
"""

import os
import sys
import time
from typing import Tuple, Dict, Any, List

sys.path.insert(0, os.path.abspath("."))

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import math
import numpy as np
import rasterio
from scipy.ndimage import label, find_objects, distance_transform_edt, maximum_filter
from shapely.geometry import shape, box, Polygon
from shapely.ops import unary_union
from rasterio.features import shapes

from stratum_ro.lidar_processor import LidarProcessor
from stratum_ro.ortho_extractor import OrthoExtractor
from stratum_ro.sam2_engine import SAM2BuildingSegmenter, _extract_largest_polygon
from stratum_ro.vectorizer import CadastralVectorizer
from stratum_ro.cad_exporter import CadastralDxfExporter
from stratum_ro.landuse_ancpi import get_ancpi_landuse
from stratum_ro.sensor_review import review_candidates
from stratum_ro.building_proposals import building_proposals
from stratum_ro.roof_body_recovery import recover_roof_bodies
from stratum_ro.roof_candidate_routing import prioritize_roof_candidates


def compute_safe_ortho_boundary(vrt_path: str, margin_m: float = -5.0, min_patch_area: float = 5000.0) -> Tuple[Polygon, Polygon]:
    """
    Extrage amprenta strictă a pixelilor optici valizi din ortofotoplan (eliminând NoData negru 0,0,0)
    și aplică o retragere de siguranță (buffer negativ cu racordare rotundă) spre interiorul zonei fotografiate.
    Garantează zero geometrii generate în spațiul negru fără imagine foto vizibilă.
    """
    with rasterio.open(vrt_path) as src:
        scale = 10
        data = src.read(out_shape=(src.count, src.height // scale, src.width // scale))
        mask = (np.sum(data, axis=0) > 15).astype(np.uint8)
        aff = src.transform * src.transform.scale(scale, scale)
        geoms = [
            shape(gd)
            for gd, val in shapes(mask, transform=aff)
            if val == 1 and shape(gd).area > min_patch_area
        ]
    raw = unary_union(geoms)
    if raw.geom_type == "MultiPolygon":
        raw = max(raw.geoms, key=lambda p: p.area)
    simplified = raw.simplify(2.0, preserve_topology=True)
    filled = Polygon(simplified.exterior) if simplified.geom_type == "Polygon" else simplified
    safe_boundary = filled.buffer(margin_m, join_style=1)
    return filled, safe_boundary


def main():
    import argparse
    parser = argparse.ArgumentParser(description='StratumRO local hybrid pipeline')
    parser.add_argument('--proposal-policy', choices=['legacy','focused_class6','roof_bodies'], default='legacy',
                        help='Experimental focused_class6 or RGB roof_bodies inspection layers')
    parser.add_argument('--output-dir', default=r'workspace\output',
                        help='Destination for generated deliverables and tile cache')
    parser.add_argument('--simple-roof-edges', action='store_true',
                        help='Opt-in RGB/LiDAR trimming and supported simple roof shapes; requires roof_bodies')
    args = parser.parse_args()
    if args.simple_roof_edges and args.proposal_policy != 'roof_bodies':
        parser.error('--simple-roof-edges requires --proposal-policy roof_bodies')
    os.makedirs(args.output_dir, exist_ok=True)
    print("=================================================================")
    print("  STRATUM-RO: PIPELINE DE FUZIUNE HIBRIDA COMPLETA LIDAR + SAM 2 ")
    print("  Zona: Cluj USAMV (8 Tile-uri MrSID, 4.62M Puncte LiDAR)         ")
    print("  Standard Cadastral: Stereo 70 (EPSG:3844) / ANCPI v3           ")
    print("=================================================================\n")

    laz_path = r"C:\Users\lefpa\Desktop\date\Z_VladP\Comparatie\LAZ\NorPuncte_St70_S42.laz"
    dtm_path = r"C:\Users\lefpa\Desktop\date\Z_VladP\Comparatie\DTM3m\DTM3m.tif"
    ndsm_out = os.path.join(args.output_dir, 'ndsm_stereo70.tif')

    # 1. Extragere LiDAR & nDSM
    t0 = time.time()
    print("Etapa 1: Ingestie si clasificare multi-categorie nor de puncte LiDAR...")
    lidar_proc = LidarProcessor(laz_path, dtm_path)
    
    try:
        lidar_data = lidar_proc.process_multicategory(output_ndsm_path=ndsm_out, resolution=1.0)
    except Exception as e:
        print(f"   [Nota] Fisierul ndsm e blocat de un proces extern ({e}). Continuam in memorie.")
        lidar_data = lidar_proc.process_multicategory(output_ndsm_path=None, resolution=1.0)

    ndsm = lidar_data["ndsm"]
    tr_ndsm = lidar_data["transform"]
    tree_pts = lidar_data["tree_points"]
    pole_pts = lidar_data["pole_points"]

    lbl_main, num_main = label(lidar_data["main_buildings_grid"])
    objs_main = find_objects(lbl_main)

    lbl_outb, num_outb = label(lidar_data["outbuildings_grid"])
    objs_outb = find_objects(lbl_outb)

    print(f"   Extragere LiDAR finalizata in {time.time()-t0:.2f}s:")
    print(f"   - Candidati cladiri principale: {num_main}")
    print(f"   - Candidati anexe gospodaresti: {num_outb}")
    print(f"   - Arbori identificati (varfuri): {len(tree_pts)}")
    print(f"   - Stalpi & turnuri inalte: {len(pole_pts)}")

    # 2. Initializare OrthoExtractor & SAM 2 pe GPU RTX 4050
    print("\nEtapa 2: Initializare Meta SAM 2 Hiera pe GPU NVIDIA RTX 4050...")
    extractor = OrthoExtractor()
    segmenter = SAM2BuildingSegmenter()
    print(f"   Model SAM 2 incarcat cu succes pe GPU ({segmenter.device})!")

    # Definim lista celor 8 tile-uri MrSID Cluj USAMV
    tiles = [
        {"name": "Cluj-0-0", "xmin": 390529.4, "xmax": 390878.9, "ymin": 585536.8, "ymax": 585886.3},
        {"name": "Cluj-0-1", "xmin": 390529.4, "xmax": 390878.9, "ymin": 585187.3, "ymax": 585536.8},
        {"name": "Cluj-0-2", "xmin": 390529.4, "xmax": 390878.9, "ymin": 584837.7, "ymax": 585187.3},
        {"name": "Cluj-1-0", "xmin": 390878.9, "xmax": 391228.4, "ymin": 585536.8, "ymax": 585886.3},
        {"name": "Cluj-1-1", "xmin": 390878.9, "xmax": 391228.4, "ymin": 585187.3, "ymax": 585536.8},
        {"name": "Cluj-1-2", "xmin": 390878.9, "xmax": 391228.4, "ymin": 584837.7, "ymax": 585187.3},
        {"name": "Cluj-2-0", "xmin": 391228.4, "xmax": 391578.0, "ymin": 585536.8, "ymax": 585886.3},
        {"name": "Cluj-2-1", "xmin": 391228.4, "xmax": 391578.0, "ymin": 585187.3, "ymax": 585536.8},
    ]

    # 3. Procesare Hibrida Tile cu Tile
    print("\nEtapa 3: Executie Fuziune Senzoriala Hibrida (Ortofoto + LiDAR)...")
    all_hybrid_buildings = []
    focused_hybrid_buildings = []
    body_candidates = []
    body_raw = []
    total_confirmed_hibrid = 0
    total_lidar_direct = 0
    total_rejected = 0

    vectorizer = CadastralVectorizer(crs="EPSG:3844")
    t_start_fusion = time.time()

    # 2.1 Pre-generare Prompturi Candidate (cu divizare clustere gigant pe pavilioane individuale)
    print("\nEtapa 2.1: Generare si divizare prompturi candidate pe baza densitatii LiDAR...")
    all_candidate_prompts = []
    if args.proposal_policy == 'focused_class6':
        for proposal in building_proposals(lidar_data):
            if proposal['source'] != 'CLASS_6':
                continue  # Existing context prompts below preserve unsupported roofs.
            poly, sl, comp_mask = proposal['geometry'], proposal['slice'], proposal['mask']
            dist = distance_transform_edt(np.pad(comp_mask, 1))[1:-1,1:-1]
            rr, cc = np.unravel_index(np.argmax(dist), dist.shape)
            pt_x, pt_y = tr_ndsm * (sl[1].start+cc+.5, sl[0].start+rr+.5)
            comp_h = ndsm[sl][comp_mask]
            left, bottom, right, top = poly.bounds
            all_candidate_prompts.append({
                'center_x': (left+right)/2, 'center_y': (bottom+top)/2,
                'b_left': left, 'b_right': right, 'b_bottom': bottom, 'b_top': top,
                'internal_pts': [(pt_x,pt_y)], 'lidar_area': proposal['area_m2'],
                'mean_h': float(np.mean(comp_h)), 'max_h': float(np.max(comp_h)),
                'is_subprompt': False, 'comp_mask': comp_mask,
                'c_start': sl[1].start, 'r_start': sl[0].start,
                'proposal_source': 'CLASS_6'})
    for b_idx in range(1, num_main + 1):
        sl = objs_main[b_idx - 1]
        if sl is None:
            continue

        comp_mask = (lbl_main[sl] == b_idx)
        area_m2 = np.sum(comp_mask)
        if area_m2 < 12:
            continue

        r_start, r_stop = sl[0].start, sl[0].stop
        c_start, c_stop = sl[1].start, sl[1].stop

        b_xmin = tr_ndsm.c + c_start * tr_ndsm.a
        b_xmax = tr_ndsm.c + c_stop * tr_ndsm.a
        b_ymax = tr_ndsm.f + r_start * tr_ndsm.e
        b_ymin = tr_ndsm.f + r_stop * tr_ndsm.e

        b_left, b_right = min(b_xmin, b_xmax), max(b_xmin, b_xmax)
        b_bottom, b_top = min(b_ymin, b_ymax), max(b_ymin, b_ymax)

        comp_h = ndsm[sl][comp_mask]
        mean_h = float(np.mean(comp_h)) if len(comp_h) > 0 else 0.0
        max_h = float(np.max(comp_h)) if len(comp_h) > 0 else 0.0

        rr, cc = np.where(comp_mask)
        idx_med = int(len(rr) * 0.5)
        pt_x = tr_ndsm.c + (c_start + cc[idx_med]) * tr_ndsm.a
        pt_y = tr_ndsm.f + (r_start + rr[idx_med]) * tr_ndsm.e

        cluster_w = b_right - b_left
        cluster_h = b_top - b_bottom
        is_oversized = (cluster_w > 48.0) or (cluster_h > 48.0) or (area_m2 > 700.0)

        if is_oversized:
            dist = distance_transform_edt(comp_mask)
            local_peaks = (maximum_filter(dist, size=21) == dist) & (dist >= 3.5) & comp_mask
            pr_list, pc_list = np.where(local_peaks)

            distinct_peaks = []
            for pr, pc in zip(pr_list, pc_list):
                gx = tr_ndsm.c + (c_start + pc) * tr_ndsm.a
                gy = tr_ndsm.f + (r_start + pr) * tr_ndsm.e
                if not any(math.hypot(gx - px, gy - py) < 18.0 for px, py in distinct_peaks):
                    distinct_peaks.append((gx, gy))

            if len(distinct_peaks) > 1:
                for px, py in distinct_peaks:
                    all_candidate_prompts.append({
                        "center_x": px,
                        "center_y": py,
                        "b_left": px - 32.0,
                        "b_right": px + 32.0,
                        "b_bottom": py - 32.0,
                        "b_top": py + 32.0,
                        "internal_pts": [(px, py)],
                        "lidar_area": min(float(area_m2), 1200.0),
                        "mean_h": mean_h,
                        "max_h": max_h,
                        "is_subprompt": True,
                        "comp_mask": comp_mask,
                        "c_start": c_start,
                        "r_start": r_start
                    })
                continue

        all_candidate_prompts.append({
            "center_x": 0.5 * (b_left + b_right),
            "center_y": 0.5 * (b_bottom + b_top),
            "b_left": b_left,
            "b_right": b_right,
            "b_bottom": b_bottom,
            "b_top": b_top,
            "internal_pts": [(pt_x, pt_y)],
            "lidar_area": float(area_m2),
            "mean_h": mean_h,
            "max_h": max_h,
            "is_subprompt": False,
            "comp_mask": comp_mask,
            "c_start": c_start,
            "r_start": r_start
        })

    print(f"   Generat {len(all_candidate_prompts)} prompturi optice unice din cele {num_main} clustere LiDAR.")

    halo = 25.0  # 25m halo buffer perimetral pentru context complet și eliminarea feliării la graniță
    for t_idx, tile in enumerate(tiles, start=1):
        t_name = tile["name"]
        t_xmin, t_xmax = tile["xmin"], tile["xmax"]
        t_ymin, t_ymax = tile["ymin"], tile["ymax"]

        crop_xmin = t_xmin - halo
        crop_ymin = t_ymin - halo
        crop_xmax = t_xmax + halo
        crop_ymax = t_ymax + halo

        crop_file = os.path.join(args.output_dir, f"cache_tile_{t_name}_halo.tif")
        crop_res = extractor.crop_aoi(crop_xmin, crop_ymin, crop_xmax, crop_ymax, crop_file, target_res=0.15)
        img_rgb = crop_res["image"]
        tr_img = crop_res["transform"]

        enc_t = segmenter.set_image(img_rgb, tr_img)

        if args.proposal_policy == 'roof_bodies':
            recovered = recover_roof_bodies(lidar_data,img_rgb,tr_img,segmenter,
                roi_bounds=(t_xmin,t_ymin,t_xmax,t_ymax),simple_edges=args.simple_roof_edges)
            for item in recovered['candidates']:
                # A halo provides context, but only one tile owns each candidate.
                centroid = item['geometry'].centroid
                if t_xmin <= centroid.x < t_xmax and t_ymin <= centroid.y < t_ymax:
                    item = dict(item, id=f"{t_name}:{item['id']}",raw_id=f"{t_name}:{item['raw_id']}")
                    body_candidates.append(item)
            body_raw.extend(dict(item,id=f"{t_name}:{item['id']}") for item in recovered['raw'])

        tile_b_count = 0
        tile_hibrid = 0

        for p_info in all_candidate_prompts:
            px = p_info["center_x"]
            py = p_info["center_y"]
            if not (t_xmin <= px < t_xmax and t_ymin <= py < t_ymax):
                continue

            tile_b_count += 1
            destination = (focused_hybrid_buildings if p_info.get('proposal_source') == 'CLASS_6'
                           else all_hybrid_buildings)
            res = segmenter.segment_candidate(
                b_xmin=p_info["b_left"], b_ymin=p_info["b_bottom"],
                b_xmax=p_info["b_right"], b_ymax=p_info["b_top"],
                mean_h=p_info["mean_h"],
                max_h=p_info["max_h"],
                lidar_area=p_info["lidar_area"],
                internal_pts_geo=p_info["internal_pts"],
                score_threshold=0.60,
                height_min_threshold=2.0
            )

            if res["status"] == "CONFIRMAT_HIBRID":
                total_confirmed_hibrid += 1
                tile_hibrid += 1
                destination.append(res)
            elif res["status"] == "LIDAR_DIRECT":
                # NICIODATĂ nu adăugăm un cluster brut uriaș (>2500m2) direct în cadastru
                if not p_info["is_subprompt"] and p_info["lidar_area"] <= 2500.0:
                    total_lidar_direct += 1
                    sub_tr = tr_ndsm * rasterio.Affine.translation(p_info["c_start"], p_info["r_start"])
                    lidar_polys = []
                    c_mask = p_info["comp_mask"]
                    for geom_dict, val in shapes(c_mask.astype(np.uint8), mask=c_mask, transform=sub_tr):
                        if val == 1:
                            p = shape(geom_dict)
                            if p.is_valid and p.area >= 8.0:
                                lidar_polys.append(p)
                    if lidar_polys:
                        chosen_p = max(lidar_polys, key=lambda x: x.area)
                        res["geometry"] = _extract_largest_polygon(chosen_p)
                        destination.append(res)
                else:
                    total_rejected += 1
            else:
                total_rejected += 1

        print(f"   Tile [{t_idx}/8] {t_name}: {tile_b_count} cladiri procesate ({tile_hibrid} confirmate dublu optic+LiDAR, enc: {enc_t:.2f}s)")
        sys.stdout.flush()

    fusion_time = time.time() - t_start_fusion
    print(f"\nFuziune Hibrida finalizata in {fusion_time:.2f} secunde!")
    print(f"Total Cladiri Evaluate: {total_confirmed_hibrid + total_lidar_direct + total_rejected}")
    print(f"  [+] Confirmate DUBLU (Meta SAM 2 + LiDAR): {total_confirmed_hibrid}")
    print(f"  [~] Completate cu Geometrie LiDAR Direct: {total_lidar_direct}")
    print(f"  [-] Respinse (fara inaltime / zgomot sol): {total_rejected}")

    # 4. Regularizare CAD (Ortogonalizare 90 grade, simplificare noduri)
    print("\nEtapa 4: Regularizare CAD si simplificare geometrii (Stereo 70 EPSG:3844)...")

    # 4.1 Extragere LIMITA_SECTOR_CADASTRAL și Bandă de Siguranță Ortofoto
    vrt_orto = "workspace/output/ortofoto_cluj_usamv_rgb.vrt"
    ortho_footprint, safe_ortho_boundary = compute_safe_ortho_boundary(vrt_orto, margin_m=-5.0)
    sector_boundary = safe_ortho_boundary
    print(f"   [Banda Siguranta] Calculat MARGINE_SIGURANTA_ORTOFOTO (-5.0m): {safe_ortho_boundary.area/1e4:.2f} ha (zero NoData)")

    cad_main = vectorizer.format_hybrid_buildings(
        all_hybrid_buildings,
        tolerance=0.5,
        eave_offset_m=0.40,
        use_quality_v2=True,
        ndsm_array=ndsm,
        ndsm_transform=tr_ndsm,
        record_intermediate_stages=True,
    )
    # Keep hypotheses separate: merging new prompts into old ones can degrade a
    # previously good footprint (observed for development case 5).
    cad_alternatives = CadastralVectorizer(crs='EPSG:3844').format_hybrid_buildings(
        focused_hybrid_buildings, tolerance=.5, eave_offset_m=.40,
        use_quality_v2=True, ndsm_array=ndsm, ndsm_transform=tr_ndsm) if focused_hybrid_buildings else []
    if safe_ortho_boundary and not safe_ortho_boundary.is_empty:
        cad_alternatives = [b for b in cad_alternatives
                            if safe_ortho_boundary.covers(b['geometry'])]

    # Filtrare strictă: păstrăm DOAR clădirile din banda de siguranță optică (elimină cele 26 din NoData)
    if safe_ortho_boundary and not safe_ortho_boundary.is_empty:
        cad_main = [
            b for b in cad_main 
            if b.get("geometry") 
            and safe_ortho_boundary.contains(b["geometry"].centroid) 
            and (safe_ortho_boundary.intersection(b["geometry"]).area / (b["geometry"].area + 1e-6) >= 0.75)
        ]

    # Deduplicare geometrică
    import hashlib
    seen_hashes = set()
    dedup_cad_main = []
    for b in cad_main:
        h = hashlib.sha256(b["geometry"].wkb).hexdigest()
        if h not in seen_hashes:
            seen_hashes.add(h)
            dedup_cad_main.append(b)
    cad_main = dedup_cad_main

    # 4.1.1 Aplicare Retragere Adaptivă a Streșinii cu Protecție la Calcan (Zid Comun)
    from stratum_ro.geometry_utils import apply_calcan_aware_eave_retraction
    all_bldg_polys = [b["geometry"] for b in cad_main if b.get("geometry")]
    calcan_count = 0
    for i, b in enumerate(cad_main):
        orig_poly = b["geometry"]
        orig_box = box(*orig_poly.bounds).buffer(5.0)
        adj_others = [p for j, p in enumerate(all_bldg_polys) if j != i and orig_box.intersects(p)]
        retracted_sol = apply_calcan_aware_eave_retraction(
            building_poly=orig_poly,
            property_boundary=sector_boundary,
            adjacent_buildings=adj_others,
            offset_eave_m=b.get("eave_offset_m", 0.40),
            calcan_tol_m=0.25
        )
        if retracted_sol is not None and retracted_sol.is_valid and not retracted_sol.is_empty:
            b["geometry_sol"] = retracted_sol
            b["area_sol_m2"] = round(float(retracted_sol.area), 2)
            # Verificăm dacă vreun perete a rămas pe calcan
            if abs(retracted_sol.area - orig_poly.buffer(-b.get("eave_offset_m", 0.40)).area) > 0.5:
                calcan_count += 1

    print(f"   [Calcan Protection] {calcan_count} corpuri de clădire protejate la zid comun/limită de sector (deplasare 0.00m pe calcan).")
    print(f"   Poligoane finale cladiri principale (validate in sector): {len(cad_main)}")

    cad_outb = vectorizer.vectorize_mask(lidar_data["outbuildings_grid"], tr_ndsm, min_area_m2=8.0, category="ANEXA_GOSPODAREASCA") or []
    if safe_ortho_boundary and not safe_ortho_boundary.is_empty:
        cad_outb = [b for b in cad_outb if b.get("geometry") and safe_ortho_boundary.contains(b["geometry"].centroid)]

    # Preserve glass roofs / sensor conflicts; route to review, never auto-approve.
    cad_main = review_candidates(cad_main, lidar_data['class_evidence'], tr_ndsm)
    cad_outb = review_candidates(cad_outb, lidar_data['class_evidence'], tr_ndsm)
    cad_alternatives = review_candidates(cad_alternatives, lidar_data['class_evidence'], tr_ndsm)
    for b in cad_alternatives:
        b['qa_status'] = 'NECESITA_VERIFICARE'
        b['qa_reasons'] += ';ALTERNATIVA_CLASA_6'
    review_queue = [dict(b, qa_source_layer=layer) for layer, items in
                    [('CLADIRI_CADASTRU_CLEAN', cad_main), ('ANEXE_GOSPODARESTI', cad_outb),
                     ('CLADIRI_ALTERNATIVE', cad_alternatives)]
                    for b in items if b['qa_status'] == 'NECESITA_VERIFICARE']
    body_candidates = prioritize_roof_candidates(body_candidates)
    selected_bodies = [b for b in body_candidates if b['route']=='INSPECTIE_PRIORITARA'
                       and safe_ortho_boundary.covers(b['geometry'])]

    # 4.2 Extragere Categorii de Folosință ANCPI (DR, HR, VN, CIMITIR, A)
    print("\nEtapa 4.2: Extragere Categorii de Folosință ANCPI (Ordinul 600/2023)...")
    if sector_boundary and not sector_boundary.is_empty:
        aoi_bounds = tuple(round(coord, 1) for coord in sector_boundary.bounds)
    else:
        aoi_bounds = (390529.4, 584837.7, 391578.0, 585886.3)
    landuse = get_ancpi_landuse(aoi_bounds, sector_boundary)
    for k, v in landuse.items():
        print(f"   - {k} ({v.geom_type}): {v.area:.1f} m2")

    # 4.3 Filtrare Riguroasă Vegetație (Arbori & Stâlpi)
    trees_raw = vectorizer.vectorize_points(tree_pts, category="ARBORE")
    poles_raw = vectorizer.vectorize_points(pole_pts, category="STALP_TURN")

    bldgs_union = unary_union([b["geometry"] for b in cad_main] + [b["geometry"] for b in cad_outb])
    tree_exclusions = [bldgs_union, landuse["DR"], landuse["VN"], landuse["CIMITIR"], landuse["HR"]]
    trees_gdf = vectorizer.filter_points_multi_exclusion(trees_raw, tree_exclusions, min_height=3.8)
    if safe_ortho_boundary and not safe_ortho_boundary.is_empty:
        trees_gdf = [t for t in trees_gdf if safe_ortho_boundary.contains(t["geometry"])]
        poles_gdf = [p for p in poles_raw if safe_ortho_boundary.contains(p["geometry"])]
    else:
        poles_gdf = poles_raw

    # Poligoane Coronament Arbori (proiecție coroană la sol)
    tree_canopies_raw = lidar_data.get("tree_canopies", [])
    tree_canopies_gdf = []
    for tc in tree_canopies_raw:
        g = tc["geometry"]
        if safe_ortho_boundary.contains(g.centroid) and not bldgs_union.intersects(g):
            if not any(ex.intersects(g) for ex in [landuse["DR"], landuse["VN"], landuse["CIMITIR"]]):
                tree_canopies_gdf.append({
                    "id": len(tree_canopies_gdf) + 1,
                    "geometry": g,
                    "category": "CORONAMENT_ARBORE",
                    "height_m": tc["height_m"],
                    "crown_radius_m": tc["crown_radius_m"],
                    "area_m2": tc["crown_area_m2"]
                })

    print(f"   Arbori solitari validați: {len(trees_gdf)} (puncte), Coronamente 2D: {len(tree_canopies_gdf)} (poligoane)")
    print(f"   Stâlpi & turnuri: {len(poles_gdf)} puncte validate")

    # 4.4 Construcție Partiție Planară Continuă 100% (Zero Gaps, Zero Overlaps)
    print("\nEtapa 4.3: Calcul Partiție Planară Topologică (Stratul UNCLASSIFIED)...")
    all_known_geoms = {
        "CLADIRI": bldgs_union,
        "DR": landuse["DR"],
        "HR": landuse["HR"],
        "VN": landuse["VN"],
        "CIMITIR": landuse["CIMITIR"],
        "A": landuse["A"]
    }
    unclassified_poly = vectorizer.build_planar_partition(sector_boundary, all_known_geoms)
    print(f"   Strat UNCLASSIFIED generat: {unclassified_poly.area:.1f} m2 (acoperire 100% fără goluri)")

    # Statistici noduri
    vertices_hist = [b["vertices"] for b in cad_main]
    avg_vertices = np.mean(vertices_hist) if vertices_hist else 0
    rect_count = sum(1 for v in vertices_hist if v == 4)
    print(f"   Statistica simplificare noduri CAD:")
    print(f"     - Medie noduri per cladire: {avg_vertices:.1f} noduri")
    print(f"     - Dreptunghiuri perfecte de 4 noduri (90°): {rect_count} ({rect_count/max(len(cad_main), 1)*100:.1f}%)")

    def to_feature_list(geom, category_name):
        if geom is None or geom.is_empty:
            return []
        if geom.geom_type == 'Polygon':
            polys = [geom]
        elif geom.geom_type == 'MultiPolygon':
            polys = list(geom.geoms)
        elif hasattr(geom, 'geoms'):
            polys = [g for g in geom.geoms if g.geom_type == 'Polygon']
        else:
            polys = []
        return [{"id": i, "geometry": p, "category": category_name, "area_m2": round(float(p.area), 2)} 
                for i, p in enumerate(polys, 1) if p.is_valid and p.area >= 2.0]

    # 5. Export GeoPackage & AutoCAD DXF
    print("\nEtapa 5: Salvare Livrabile Cadastrale Complete...")
    multicategory_dict = {
        "LIMITA_SECTOR_CADASTRAL": [{"id": 1, "geometry": sector_boundary, "category": "LIMITA_SECTOR"}],
        "MARGINE_SIGURANTA_ORTOFOTO": [{"id": 1, "geometry": safe_ortho_boundary, "category": "MARGINE_SIGURANTA_ORTOFOTO"}],
        "CLADIRI_CADASTRU_CLEAN": cad_main,
        "CLADIRI_HIBRID": cad_main,
        "CLADIRI_SOL_ANCPI": [
            {
                "id": b["id"],
                "geometry": b["geometry_sol"],
                "category": "CLADIRE_SOL_ANCPI",
                "clasa_forma": b.get("clasa_forma", "DREPTUNGHI_OBB"),
                "vertices": len(b["geometry_sol"].exterior.coords) - 1 if hasattr(b["geometry_sol"], "exterior") else b.get("vertices", 4),
                "area_m2": b.get("area_sol_m2", b["area_m2"]),
                "eave_offset_m": b.get("eave_offset_m", 0.40),
                "rev_status": b["qa_status"],
                "rev_issue": b["qa_reasons"]
            }
            for b in cad_main if b.get("geometry_sol")
        ],
        "ANEXE_GOSPODARESTI": cad_outb,
        "DR": to_feature_list(landuse["DR"], "CAI_COMUNICATII_RUTIERE"),
        "HR": to_feature_list(landuse["HR"], "APE_CURGATOARE"),
        "VN": to_feature_list(landuse["VN"], "VII_PLANTAȚII"),
        "CIMITIR": to_feature_list(landuse["CIMITIR"], "CIMITIR_TDS"),
        "A": to_feature_list(landuse["A"], "TEREN_ARABIL"),
        "UNCLASSIFIED": to_feature_list(unclassified_poly, "TEREN_NECLASIFICAT"),
        "ARBORI": trees_gdf,
        "ARBORI_CORONAMENT": tree_canopies_gdf,
        "CORONAMENT_ARBORI": tree_canopies_gdf,
        "STALPI_TURNURI": poles_gdf
    }

    final_gpkg = os.path.join(args.output_dir, 'cladiri_stereo70.gpkg')
    final_dxf = os.path.join(args.output_dir, 'cadastru_ancpi.dxf')

    # Review layer is GPKG-only so CAD output does not duplicate buildings.
    vectorizer.save_multicategory_geopackage(
        dict(multicategory_dict, REVIZUIRE_SENZORI=review_queue,
             CLADIRI_ALTERNATIVE=cad_alternatives,
             PROPUNERI_SELECTATE=selected_bodies, CORPURI_TOATE=body_candidates,
             CORPURI_MASTI_OPTICE=body_raw), final_gpkg)
    import geopandas as gpd
    for layer, items in [('REVIZUIRE_SENZORI',review_queue), ('CLADIRI_ALTERNATIVE',cad_alternatives),
                         ('PROPUNERI_SELECTATE',selected_bodies),('CORPURI_TOATE',body_candidates),
                         ('CORPURI_MASTI_OPTICE',body_raw)]:
        if not items and layer in gpd.list_layers(final_gpkg)['name'].tolist():
            gpd.GeoDataFrame({'geometry':[]}, geometry='geometry', crs='EPSG:3844').to_file(
                final_gpkg, layer=layer, driver='GPKG', mode='w')
    vectorizer.save_intermediate_stages_to_gpkg(final_gpkg)
    print(f"   [OK] GeoPackage Multi-Layer Complet: {final_gpkg}")
    print(f"   [OK] Straturi Inspectie Etape V2 (STAGE_1..5) salvate in: {final_gpkg}")

    dxf_exporter = CadastralDxfExporter(dxf_version="R2010")
    dxf_exporter.export_multicategory_to_dxf(multicategory_dict, final_dxf, include_labels=True)
    print(f"   [OK] AutoCAD DXF ANCPI: {final_dxf}")

    print("\n=================================================================")
    print("  PROCESARE COMPLETATA CU SUCCES! REZULTATE PREGATITE PENTRU QGIS")
    print("=================================================================")


if __name__ == "__main__":
    main()
