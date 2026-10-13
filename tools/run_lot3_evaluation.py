# -*- coding: utf-8 -*-
"""
Deterministic reproducible runner for StratumRO Lot 3 (T11-T20).
Executes current pipeline on frozen selection, builds side-by-side visual panels,
contact sheet, GPKG layers, and JSON summary report.
"""
from pathlib import Path
import sys
import json
import time
import math
import argparse
import rasterio
import numpy as np
from rasterio.windows import from_bounds
import geopandas as gpd
import shapely
from shapely.geometry import box, Point, Polygon
from shapely.ops import unary_union
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from stratum_ro.roof_retry import retry_roof_geometry
from stratum_ro.sam2_engine import SAM2BuildingSegmenter
from stratum_ro.lidar_processor import LidarProcessor
from stratum_ro.evaluation_preflight import validate_selection, require_ready, sha256_file

OUT_DIR = ROOT / 'workspace/reviews/lot3_20261013'
TILE_DIR = ROOT / 'workspace/reviews/prompt_recovery_20261013/full_aoi'
LAZ_PATH = 'C:/Users/lefpa/Desktop/date/Z_VladP/Comparatie/LAZ/NorPuncte_St70_S42.laz'
DTM_PATH = 'C:/Users/lefpa/Desktop/date/Z_VladP/Comparatie/DTM3m/DTM3m.tif'


def draw_panel(ax, src, extent_box, geoms_info, title):
    """Render ortho crop and vector layers on matplotlib axis."""
    minx, miny, maxx, maxy = extent_box.bounds
    win = from_bounds(minx, miny, maxx, maxy, src.transform)
    win = win.intersection(rasterio.windows.Window(0, 0, src.width, src.height))
    rgb = np.moveaxis(src.read([1, 2, 3], window=win), 0, -1)
    win_tr = rasterio.windows.transform(win, src.transform)
    ext = [win_tr.c, win_tr.c + win.width * win_tr.a,
           win_tr.f + win.height * win_tr.e, win_tr.f]
    ax.imshow(rgb, extent=ext)

    for item in geoms_info:
        geom = item.get('geometry')
        if geom is not None and not geom.is_empty:
            if geom.geom_type == 'Point':
                ax.plot(geom.x, geom.y, marker='x', markersize=8, color=item['color'], label=item.get('label'))
            elif geom.geom_type in ('Polygon', 'MultiPolygon'):
                polys = [geom] if geom.geom_type == 'Polygon' else geom.geoms
                for p in polys:
                    gx, gy = p.exterior.xy
                    ax.plot(gx, gy, color=item['color'], linewidth=item.get('lw', 1.8),
                            linestyle=item.get('ls', '-'), label=item.get('label') if p == polys[0] else None)

    ax.set_xlim(minx, maxx)
    ax.set_ylim(miny, maxy)
    ax.set_title(title, fontsize=10, fontweight='bold')
    handles, labels = ax.get_legend_handles_labels()
    if handles:
        ax.legend(handles, labels, loc='lower left', framealpha=0.85, fontsize=8)
    ax.axis('off')


def main():
    global OUT_DIR
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, default=OUT_DIR / 'selection_manifest.json')
    parser.add_argument('--output-dir', type=Path)
    parser.add_argument('--preflight-only', action='store_true')
    args = parser.parse_args()
    t0 = time.time()
    manifest_path = args.manifest.resolve()
    if not manifest_path.exists():
        raise FileNotFoundError(f"Selection manifest not found: {manifest_path}")

    with open(manifest_path, 'r', encoding='utf-8') as f:
        manifest = json.load(f)

    preflight = validate_selection(manifest, manifest_dir=manifest_path.parent, tile_dir=TILE_DIR)
    print(json.dumps(preflight, indent=2, ensure_ascii=False))
    require_ready(preflight)
    if args.preflight_only:
        return
    if args.output_dir is None:
        raise ValueError('--output-dir must name a NEW directory; historical evidence is immutable')
    OUT_DIR = args.output_dir.resolve()
    OUT_DIR.mkdir(parents=True, exist_ok=False)
    # Bind this run to the reviewed selection, and disclose its actual entry point.
    (OUT_DIR / 'selection_manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')

    print(f"[LOT3] Starting evaluation for {len(manifest['cases'])} cases: T11-T20...")
    print(f"[LOT3] Loading LiDAR: {LAZ_PATH} ...")
    lidar_data = LidarProcessor(LAZ_PATH, DTM_PATH).process_multicategory()
    print("[LOT3] Initializing SAM2...")
    model = SAM2BuildingSegmenter()

    cached_tile = None
    cached_tile_data = None

    all_case_results = []
    extracted_records = []
    selection_records = []
    unrecovered_records = []

    for case in manifest['cases']:
        case_id = case['test_id']
        tile_name = case['tile']
        search_bbox = case['search_bbox']
        search_geom = box(*search_bbox)
        tile_p = TILE_DIR / tile_name

        print(f"\n--- Processing {case_id} ({case['archetype']}) on {tile_name} ---")

        # Load tile if not cached
        if cached_tile != tile_name:
            print(f"[LOT3] Loading tile raster {tile_name}...")
            with rasterio.open(tile_p) as src:
                rgb = np.moveaxis(src.read([1, 2, 3]), 0, -1)
                tr = src.transform
            model.set_image(rgb, tr)
            cached_tile = tile_name
            cached_tile_data = (rgb, tr)
        else:
            rgb, tr = cached_tile_data

        # Run extraction pipeline
        t_start = time.time()
        res = retry_roof_geometry(search_geom, rgb, tr, lidar_data, model)
        dur = time.time() - t_start

        candidates = res.get('candidates', [])
        status = res.get('status', 'UNKNOWN')
        print(f"[LOT3] Result for {case_id}: status={status}, recovered bodies={len(candidates)} ({dur:.2f}s)")

        case_diag = {
            'test_id': case_id,
            'tile': tile_name,
            'archetype': case['archetype'],
            'search_center': case['search_center'],
            'search_bbox': search_bbox,
            'status': status,
            'duration_s': round(dur, 2),
            'prompts': {
                'status': res['prompts'].get('status'),
                'seed_count': len(res['prompts'].get('seeds', [])),
                'seeds': [
                    {'point': s['point'], 'area_m2': round(s['area_m2'], 1), 'mean_h': round(s['mean_h'], 1)}
                    for s in res['prompts'].get('seeds', [])
                ]
            },
            'bodies': []
        }

        # Record search window
        selection_records.append({
            'test_id': case_id,
            'archetype': case['archetype'],
            'tile': tile_name,
            'status': status,
            'bodies_count': len(candidates),
            'geometry': search_geom
        })

        if not candidates:
            unrecovered_records.append({
                'test_id': case_id,
                'archetype': case['archetype'],
                'tile': tile_name,
                'status': status,
                'geometry': Point(case['search_center'][0], case['search_center'][1])
            })

        body_geoms = []
        for b_idx, cand in enumerate(candidates, 1):
            body_id = f"{case_id}:C{b_idx}"
            geom = cand['geometry']
            body_geoms.append(geom)

            rec = {
                'id': body_id,
                'test_id': case_id,
                'body_index': b_idx,
                'archetype': case['archetype'],
                'tile': tile_name,
                'sam2_score': round(float(cand.get('sam2_score', 0.0)), 3),
                'simple_method': str(cand.get('simple_method', '')),
                'simple_support': round(float(cand.get('simple_support', 0.0)), 3),
                'simple_coverage': round(float(cand.get('simple_coverage', 0.0)), 3),
                'vertices': int(cand.get('vertices', 0)),
                'area_m2': round(float(geom.area), 1),
                'vegetation_fraction': round(float(cand.get('vegetation_fraction', 0.0)), 3),
                'building_fraction': round(float(cand.get('building_fraction', 0.0)), 3),
                'color_method': str(cand.get('color_method', '')),
                'owner_verdict': 'PENDING_OWNER_REVIEW',
                'qa_status': 'NECESITA_VERIFICARE_LOT3',
                'geometry': geom
            }
            extracted_records.append(rec)
            case_diag['bodies'].append({k: v for k, v in rec.items() if k != 'geometry'})

        all_case_results.append(case_diag)

        # Generate individual side-by-side image: T*.png
        # Compute framing box covering search_bbox and all extracted bodies + 8m margin
        all_objs = [search_geom] + body_geoms
        u_box = unary_union(all_objs)
        bminx, bminy, bmaxx, bmaxy = u_box.bounds
        pad = 8.0
        frame_box = box(bminx - pad, bminy - pad, bmaxx + pad, bmaxy + pad)

        with rasterio.open(tile_p) as src:
            fig, (ax_a, ax_b) = plt.subplots(1, 2, figsize=(14, 7), layout='constrained')

            # Panel A: Clean Ortho without contours
            draw_panel(ax_a, src, frame_box, [], f"{case_id} — A. Ortofoto Nativ Curat (Fara contur)")

            # Panel B: Ortho with results overlaid
            layers_b = [
                {'geometry': search_geom, 'color': '#00FFFF', 'lw': 1.0, 'ls': ':', 'label': 'Fereastra cautare'}
            ]
            if body_geoms:
                for b_i, b_geom in enumerate(body_geoms, 1):
                    b_id = f"{case_id}:C{b_i}"
                    b_meta = case_diag['bodies'][b_i - 1]
                    lbl = f"{b_id} ({b_meta['vertices']}v, {b_meta['area_m2']}m², supp={b_meta['simple_support']})"
                    layers_b.append({
                        'geometry': b_geom,
                        'color': '#39FF14',
                        'lw': 2.0,
                        'ls': '-',
                        'label': lbl
                    })
                title_b = f"{case_id} — B. Rezultat ({len(body_geoms)} corpuri) [PENDING_OWNER_REVIEW]"
            else:
                layers_b.append({
                    'geometry': Point(case['search_center'][0], case['search_center'][1]),
                    'color': '#FF2A00',
                    'label': f'Centroid cautare ({status})'
                })
                title_b = f"{case_id} — B. NERECUPERAT ({status}) [PENDING_OWNER_REVIEW]"

            draw_panel(ax_b, src, frame_box, layers_b, title_b)

            fig.suptitle(
                f"StratumRO Lot 3 — {case_id}: {case['archetype']} ({tile_name})\n"
                f"[Status: {status} | Corpuri: {len(body_geoms)} | PENDING_OWNER_REVIEW]",
                fontsize=12, fontweight='bold'
            )
            case_img_path = OUT_DIR / f"{case_id}.png"
            fig.savefig(case_img_path, dpi=180)
            plt.close(fig)
            print(f"[LOT3] Saved detail image: {case_img_path.name}")

    # Generate 10-case contact sheet (2 rows x 5 cols)
    print("\n[LOT3] Generating 10-case contact sheet...")
    fig, axes = plt.subplots(2, 5, figsize=(25, 11), layout='constrained')
    axes = axes.flatten()

    for idx, case in enumerate(manifest['cases']):
        ax = axes[idx]
        case_id = case['test_id']
        tile_name = case['tile']
        tile_p = TILE_DIR / tile_name
        search_geom = box(*case['search_bbox'])
        c_diag = all_case_results[idx]
        c_bodies = [r for r in extracted_records if r['test_id'] == case_id]

        all_objs = [search_geom] + [b['geometry'] for b in c_bodies]
        u_box = unary_union(all_objs)
        bminx, bminy, bmaxx, bmaxy = u_box.bounds
        pad = 6.0
        frame_box = box(bminx - pad, bminy - pad, bmaxx + pad, bmaxy + pad)

        with rasterio.open(tile_p) as src:
            layers = [{'geometry': search_geom, 'color': '#00E5FF', 'lw': 0.8, 'ls': ':'}]
            if c_bodies:
                for b in c_bodies:
                    layers.append({'geometry': b['geometry'], 'color': '#39FF14', 'lw': 1.6, 'ls': '-'})
                title = f"{case_id}: {len(c_bodies)} corp(uri) ({sum(b['area_m2'] for b in c_bodies):.0f}m²)"
            else:
                layers.append({'geometry': Point(case['search_center'][0], case['search_center'][1]), 'color': '#FF2A00'})
                title = f"{case_id}: NERECUPERAT ({c_diag['status'][:15]})"
            draw_panel(ax, src, frame_box, layers, title)

    sheet_path = OUT_DIR / 'lot3_contact_sheet.png'
    fig.suptitle("StratumRO Lot 3 (T11–T20) — Planșă Generală de Inspecție Vizuală [PENDING_OWNER_REVIEW]",
                 fontsize=16, fontweight='bold')
    fig.savefig(sheet_path, dpi=160)
    plt.close(fig)
    print(f"[LOT3] Saved contact sheet: {sheet_path.name}")

    # Save GeoPackage layers
    gpkg_path = OUT_DIR / 'lot3_results.gpkg'
    print(f"[LOT3] Writing GeoPackage layers to {gpkg_path}...")
    crs = 'EPSG:3844'
    if extracted_records:
        gdf_ext = gpd.GeoDataFrame(extracted_records, crs=crs)
        gdf_ext.to_file(gpkg_path, layer='CORPURI_EXTRASE_LOT3', driver='GPKG')
    if selection_records:
        gdf_sel = gpd.GeoDataFrame(selection_records, crs=crs)
        gdf_sel.to_file(gpkg_path, layer='FERESTRE_SELECTIE_LOT3', driver='GPKG')
    if unrecovered_records:
        gdf_unrec = gpd.GeoDataFrame(unrecovered_records, crs=crs)
        gdf_unrec.to_file(gpkg_path, layer='CAZURI_NERECUPERATE_LOT3', driver='GPKG')

    # Save summary report JSON
    total_bodies = len(extracted_records)
    cases_with_bodies = len([c for c in all_case_results if len(c['bodies']) > 0])
    cases_without_bodies = len(all_case_results) - cases_with_bodies

    report = {
        'lot': 3,
        'execution_scope': 'LOCAL_RETRY_ONLY_NOT_FULL_PRODUCTION_PIPELINE',
        'selection_manifest_sha256': sha256_file(manifest_path),
        'preflight': preflight,
        'date': '2026-10-13',
        'execution_duration_s': round(time.time() - t0, 1),
        'total_cases_evaluated': len(all_case_results),
        'cases_with_extracted_bodies': cases_with_bodies,
        'cases_unrecovered': cases_without_bodies,
        'total_bodies_extracted': total_bodies,
        'governance_status': 'PENDING_OWNER_REVIEW',
        'cases': all_case_results
    }
    report_path = OUT_DIR / 'lot3_report.json'
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"[LOT3] Saved summary report: {report_path.name}")

    print(f"\n=======================================================")
    print(f"[LOT3] Finalizat în {time.time() - t0:.1f}s.")
    print(f"Cazuri evaluate: {len(all_case_results)} (T11-T20)")
    print(f"Cazuri cu corpuri extrase: {cases_with_bodies}")
    print(f"Cazuri nerecuperate: {cases_without_bodies}")
    print(f"Total corpuri extrase: {total_bodies}")
    print(f"Toate artefactele sunt salvate în: {OUT_DIR}")
    print(f"=======================================================")


if __name__ == '__main__':
    main()
