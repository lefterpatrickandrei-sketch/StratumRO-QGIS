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

sys.path.insert(0, os.path.abspath("."))

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import numpy as np
import rasterio
from scipy.ndimage import label, find_objects
from shapely.geometry import shape, box, Polygon
from shapely.ops import unary_union
from rasterio.features import shapes

from stratum_ro.lidar_processor import LidarProcessor
from stratum_ro.ortho_extractor import OrthoExtractor
from stratum_ro.sam2_engine import SAM2BuildingSegmenter, _extract_largest_polygon
from stratum_ro.vectorizer import CadastralVectorizer
from stratum_ro.cad_exporter import CadastralDxfExporter
from stratum_ro.landuse_ancpi import get_ancpi_landuse


def main():
    print("=================================================================")
    print("  STRATUM-RO: PIPELINE DE FUZIUNE HIBRIDA COMPLETA LIDAR + SAM 2 ")
    print("  Zona: Cluj USAMV (8 Tile-uri MrSID, 4.62M Puncte LiDAR)         ")
    print("  Standard Cadastral: Stereo 70 (EPSG:3844) / ANCPI v3           ")
    print("=================================================================\n")

    laz_path = r"C:\Users\lefpa\Desktop\date\Z_VladP\Comparatie\LAZ\NorPuncte_St70_S42.laz"
    dtm_path = r"C:\Users\lefpa\Desktop\date\Z_VladP\Comparatie\DTM3m\DTM3m.tif"
    ndsm_out = r"workspace\output\ndsm_stereo70.tif"

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
    total_confirmed_hibrid = 0
    total_lidar_direct = 0
    total_rejected = 0

    vectorizer = CadastralVectorizer(crs="EPSG:3844")
    t_start_fusion = time.time()

    for t_idx, tile in enumerate(tiles, start=1):
        t_name = tile["name"]
        t_xmin, t_xmax = tile["xmin"], tile["xmax"]
        t_ymin, t_ymax = tile["ymin"], tile["ymax"]

        crop_file = f"workspace/output/cache_tile_{t_name}.tif"
        crop_res = extractor.crop_aoi(t_xmin, t_ymin, t_xmax, t_ymax, crop_file, target_res=0.15)
        img_rgb = crop_res["image"]
        tr_img = crop_res["transform"]

        enc_t = segmenter.set_image(img_rgb, tr_img)

        tile_b_count = 0
        tile_hibrid = 0

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

            # Verificăm dacă clădirea cade în tile-ul curent
            if b_right < t_xmin or b_left > t_xmax or b_top < t_ymin or b_bottom > t_ymax:
                continue

            tile_b_count += 1
            comp_h = ndsm[sl][comp_mask]
            mean_h = float(np.mean(comp_h)) if len(comp_h) > 0 else 0.0
            max_h = float(np.max(comp_h)) if len(comp_h) > 0 else 0.0

            rr, cc = np.where(comp_mask)
            idx_med = int(len(rr) * 0.5)
            pt_x = tr_ndsm.c + (c_start + cc[idx_med]) * tr_ndsm.a
            pt_y = tr_ndsm.f + (r_start + rr[idx_med]) * tr_ndsm.e
            internal_pts = [(pt_x, pt_y)]

            res = segmenter.segment_candidate(
                b_xmin=b_left, b_ymin=b_bottom,
                b_xmax=b_right, b_ymax=b_top,
                mean_h=mean_h,
                max_h=max_h,
                lidar_area=float(area_m2),
                internal_pts_geo=internal_pts,
                score_threshold=0.60,
                height_min_threshold=2.5
            )

            if res["status"] == "CONFIRMAT_HIBRID":
                total_confirmed_hibrid += 1
                tile_hibrid += 1
                all_hybrid_buildings.append(res)
            elif res["status"] == "LIDAR_DIRECT":
                total_lidar_direct += 1
                sub_tr = tr_ndsm * rasterio.Affine.translation(c_start, r_start)
                lidar_polys = []
                for geom_dict, val in shapes(comp_mask.astype(np.uint8), mask=comp_mask, transform=sub_tr):
                    if val == 1:
                        p = shape(geom_dict)
                        if p.is_valid and p.area >= 8.0:
                            lidar_polys.append(p)
                if lidar_polys:
                    chosen_p = max(lidar_polys, key=lambda x: x.area)
                    res["geometry"] = _extract_largest_polygon(chosen_p)
                    all_hybrid_buildings.append(res)
            else:
                total_rejected += 1

        print(f"   Tile [{t_idx}/8] {t_name}: {tile_b_count} cladiri procesate ({tile_hibrid} confirmate dublu optic+LiDAR, enc: {enc_t:.2f}s)")

    fusion_time = time.time() - t_start_fusion
    print(f"\nFuziune Hibrida finalizata in {fusion_time:.2f} secunde!")
    print(f"Total Cladiri Evaluate: {total_confirmed_hibrid + total_lidar_direct + total_rejected}")
    print(f"  [+] Confirmate DUBLU (Meta SAM 2 + LiDAR): {total_confirmed_hibrid}")
    print(f"  [~] Completate cu Geometrie LiDAR Direct: {total_lidar_direct}")
    print(f"  [-] Respinse (fara inaltime / zgomot sol): {total_rejected}")

    # 4. Regularizare CAD (Ortogonalizare 90 grade, simplificare noduri)
    print("\nEtapa 4: Regularizare CAD si simplificare geometrii (Stereo 70 EPSG:3844)...")

    # 4.1 Extragere LIMITA_SECTOR_CADASTRAL din ortofotoplanul valid
    vrt_orto = "workspace/output/ortofoto_cluj_usamv_rgb.vrt"
    sector_boundary = vectorizer.extract_sector_boundary(vrt_orto, tolerance=10.0)
    print(f"   [Limita Sector] Calculat LIMITA_SECTOR_CADASTRAL: {sector_boundary.area:.1f} m2 (elimina treptele NoData)")

    cad_main = vectorizer.format_hybrid_buildings(all_hybrid_buildings, tolerance=0.5, eave_offset_m=0.40)
    if sector_boundary and not sector_boundary.is_empty:
        cad_main = [b for b in cad_main if b.get("geometry") and sector_boundary.intersects(b["geometry"])]

    print(f"   Poligoane finale cladiri principale (validate in sector): {len(cad_main)}")

    cad_outb = vectorizer.vectorize_mask(lidar_data["outbuildings_grid"], tr_ndsm, min_area_m2=8.0, category="ANEXA_GOSPODAREASCA") or []
    if sector_boundary and not sector_boundary.is_empty:
        cad_outb = [b for b in cad_outb if b.get("geometry") and sector_boundary.intersects(b["geometry"])]

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
    if sector_boundary and not sector_boundary.is_empty:
        trees_gdf = [t for t in trees_gdf if sector_boundary.contains(t["geometry"])]
        poles_gdf = [p for p in poles_raw if sector_boundary.contains(p["geometry"])]
    else:
        poles_gdf = poles_raw

    print(f"   Arbori solitari validați: {len(trees_gdf)} (eliminați {len(trees_raw) - len(trees_gdf)} arbori falși din vii, cimitir, drumuri și acoperișuri)")
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
    print(f"     - Dreptunghiuri perfecte de 4 noduri (90°): {rect_count} ({rect_count/len(cad_main)*100:.1f}%)")

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
        "CLADIRI_HIBRID": cad_main,
        "ANEXE_GOSPODARESTI": cad_outb,
        "DR": to_feature_list(landuse["DR"], "CAI_COMUNICATII_RUTIERE"),
        "HR": to_feature_list(landuse["HR"], "APE_CURGATOARE"),
        "VN": to_feature_list(landuse["VN"], "VII_PLANTAȚII"),
        "CIMITIR": to_feature_list(landuse["CIMITIR"], "CIMITIR_TDS"),
        "A": to_feature_list(landuse["A"], "TEREN_ARABIL"),
        "UNCLASSIFIED": to_feature_list(unclassified_poly, "TEREN_NECLASIFICAT"),
        "ARBORI": trees_gdf,
        "STALPI_TURNURI": poles_gdf
    }

    final_gpkg = r"workspace\output\cladiri_stereo70.gpkg"
    final_dxf = r"workspace\output\cadastru_ancpi.dxf"

    vectorizer.save_multicategory_geopackage(multicategory_dict, final_gpkg)
    print(f"   [OK] GeoPackage Multi-Layer Complet: {final_gpkg}")

    dxf_exporter = CadastralDxfExporter(dxf_version="R2010")
    dxf_exporter.export_multicategory_to_dxf(multicategory_dict, final_dxf, include_labels=True)
    print(f"   [OK] AutoCAD DXF ANCPI: {final_dxf}")

    print("\n=================================================================")
    print("  PROCESARE COMPLETATA CU SUCCES! REZULTATE PREGATITE PENTRU QGIS")
    print("=================================================================")


if __name__ == "__main__":
    main()
