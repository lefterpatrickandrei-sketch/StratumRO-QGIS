"""Reproducible standalone diagnostic runner for T10 repair verification.

Loads the CURRENT partial geometry (T10:A1, source_id REF_TIER1_006:B00011)
from retry_six.gpkg layer CORPURI_RECTIFICATE as the BEFORE reference.
Executes sensor-supported retry for T10 without hardcoding coordinates,
and outputs before/after comparisons, candidate GeoPackage layers, and provenance.
Does NOT modify frozen references or active deliverables.
"""
from pathlib import Path
import sys, argparse, json
import geopandas as gpd
import rasterio, numpy as np
from rasterio.windows import from_bounds
from shapely.geometry import box, Point
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from stratum_ro.roof_retry import retry_roof_geometry
from stratum_ro.sam2_engine import SAM2BuildingSegmenter
from stratum_ro.lidar_processor import LidarProcessor


def draw_panel(ax, ortho_src, extent_box, geom_dict, title):
    """Self-contained renderer for ortho crop and layered vector geometries."""
    minx, miny, maxx, maxy = extent_box.bounds
    win = from_bounds(minx, miny, maxx, maxy, ortho_src.transform)
    win = win.intersection(rasterio.windows.Window(0, 0, ortho_src.width, ortho_src.height))
    rgb = np.moveaxis(ortho_src.read([1, 2, 3], window=win), 0, -1)
    win_transform = rasterio.windows.transform(win, ortho_src.transform)
    ext = [win_transform.c, win_transform.c + win.width * win_transform.a,
           win_transform.f + win.height * win_transform.e, win_transform.f]
    ax.imshow(rgb, extent=ext)

    for item in geom_dict:
        geom = item.get('geometry')
        if geom is not None and not geom.is_empty:
            gx, gy = geom.exterior.xy
            ax.plot(gx, gy, color=item['color'], linewidth=item.get('lw', 1.8),
                    linestyle=item.get('ls', '-'), label=item['label'])

    ax.set_xlim(minx, maxx)
    ax.set_ylim(miny, maxy)
    ax.set_title(title, fontsize=11, fontweight='bold')
    ax.legend(loc='lower left', framealpha=0.85, fontsize=8)
    ax.axis('off')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--output-dir',
        default=str(ROOT / 'workspace/reviews/t10_antigravity_20261013'),
        help='Output directory for T10 repair artifacts'
    )
    args = parser.parse_args()
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    # 1. Source reference and CURRENT partial before-geometry
    source_gpkg = ROOT / 'workspace/reviews/retry_six_release_20261013/retry_six.gpkg'
    if not source_gpkg.exists():
        raise FileNotFoundError(f"Source GPKG not found: {source_gpkg}")

    current_rectified = gpd.read_file(source_gpkg, layer='CORPURI_RECTIFICATE')
    # Filter safely using ID 'T10:A1' or test_id 'T10' or source_id 'REF_TIER1_006:B00011'
    t10_before = current_rectified[
        (current_rectified.get('id', '') == 'T10:A1') |
        (current_rectified.get('test_id', '') == 'T10') |
        (current_rectified.get('source_id', '') == 'REF_TIER1_006:B00011')
    ]
    if t10_before.empty:
        raise RuntimeError("T10 partial before-geometry not found in retry_six.gpkg")
    t10_geom = t10_before.geometry.iloc[0]

    # Historical rejected mask for lineage context
    historical_rejected = gpd.read_file(source_gpkg, layer='RESPINSE_ANTERIOR')
    t10_hist = historical_rejected[
        (historical_rejected.get('id', '') == 'T10') |
        (historical_rejected.get('source_id', '') == 'REF_TIER1_006:B00011')
    ]
    hist_geom = t10_hist.geometry.iloc[0] if not t10_hist.empty else None

    # 2. Find covering tile
    tiles = []
    tile_dir = ROOT / 'workspace/reviews/prompt_recovery_20261013/full_aoi'
    for path in sorted(tile_dir.glob('cache_tile_*_halo.tif')):
        with rasterio.open(path) as src:
            tiles.append((path, box(*src.bounds)))
    options = [(bounds.boundary.distance(t10_geom), str(path), path)
               for path, bounds in tiles if bounds.covers(t10_geom.buffer(5))]
    if not options:
        raise RuntimeError('No tile fully covers T10')
    tile_path = max(options)[2]

    # 3. Process LiDAR and initialize SAM2
    print(f"[T10] Processing LiDAR and loading tile: {tile_path.name} ...", flush=True)
    lidar_data = LidarProcessor(
        'C:/Users/lefpa/Desktop/date/Z_VladP/Comparatie/LAZ/NorPuncte_St70_S42.laz',
        'C:/Users/lefpa/Desktop/date/Z_VladP/Comparatie/DTM3m/DTM3m.tif'
    ).process_multicategory()

    model = SAM2BuildingSegmenter()
    with rasterio.open(tile_path) as src:
        rgb = np.moveaxis(src.read([1, 2, 3]), 0, -1)
        tr = src.transform
    model.set_image(rgb, tr)

    # 4. Execute retry on T10 using the search footprint to recover full extent
    search_geom = hist_geom if hist_geom is not None else t10_geom
    retry = retry_roof_geometry(search_geom, rgb, tr, lidar_data, model)

    # 5. Build reports and sanitize records for GPKG and JSON export
    report = {
        'test_id': 'T10',
        'source_id': 'REF_TIER1_006:B00011',
        'tile': str(tile_path),
        'prompts': retry['prompts'],
        'attempts': [],
        'outcome': retry['status'],
        'status': 'PENDING_OWNER_REVIEW'
    }

    raw_attempts_records = []
    for attempt in retry['attempts']:
        # Extract scalar diagnostics for JSON report
        diag = {k: v for k, v in attempt.items() if k not in ('geometry', 'raw_optical', 'point')}
        report['attempts'].append(diag)
        
        # Save raw optical mask attempt if present
        raw_opt = attempt.get('raw_optical')
        if raw_opt is not None and not raw_opt.is_empty:
            raw_rec = {
                'id': f"T10:RAW_A{attempt['index']}",
                'test_id': 'T10',
                'source_id': 'REF_TIER1_006:B00011',
                'attempt_index': attempt['index'],
                'sam2_score': float(attempt.get('sam2_score', 0.0)),
                'status': str(attempt.get('status', '')),
                'geometry': raw_opt
            }
            raw_attempts_records.append(raw_rec)

    records = []
    for candidate in retry['candidates']:
        rec = {
            'id': f"T10:A{candidate['attempt_index']}",
            'test_id': 'T10',
            'source_id': 'REF_TIER1_006:B00011',
            'attempt_index': int(candidate['attempt_index']),
            'sam2_score': float(candidate.get('sam2_score', 0.0)),
            'simple_method': str(candidate.get('simple_method', '')),
            'simple_support': float(candidate.get('simple_support', 0.0)),
            'simple_coverage': float(candidate.get('simple_coverage', 0.0)),
            'vertices': int(candidate.get('vertices', 0)),
            'vegetation_fraction': float(candidate.get('vegetation_fraction', 0.0)),
            'building_fraction': float(candidate.get('building_fraction', 0.0)),
            'color_method': str(candidate.get('color_method', '')),
            'qa_status': 'NECESITA_VERIFICARE',
            'owner_verdict': 'PENDING_OWNER_REVIEW',
            'geometry': candidate['geometry']
        }
        records.append(rec)

    report['retained_count'] = len(records)
    (out / 't10_report.json').write_text(json.dumps(report, indent=2))

    # 6. Save GeoPackage layers
    target_gpkg = out / 't10_repair.gpkg'
    if records:
        gdf_cands = gpd.GeoDataFrame(records, crs=current_rectified.crs)
        gdf_cands.to_file(target_gpkg, layer='NOI_IPOTEZE_T10', driver='GPKG')
    if raw_attempts_records:
        gdf_raw = gpd.GeoDataFrame(raw_attempts_records, crs=current_rectified.crs)
        gdf_raw.to_file(target_gpkg, layer='INCERCARI_OPTICE_RAW', driver='GPKG')
    t10_before.to_file(target_gpkg, layer='INAINTE_PARTIAL_T10_A1', driver='GPKG')
    if hist_geom is not None:
        t10_hist.to_file(target_gpkg, layer='MASCA_ISTORICA_RESPINSA', driver='GPKG')

    # 7. Generate comparison visualization using self-contained renderer
    vrt_path = ROOT / 'workspace/output/ortofoto_cluj_usamv_rgb.vrt'
    if vrt_path.exists():
        with rasterio.open(vrt_path) as ortho:
            import shapely.ops
            all_geoms = [t10_geom] + [r['geometry'] for r in records]
            if hist_geom is not None:
                all_geoms.append(hist_geom)
            u_geom = shapely.ops.unary_union(all_geoms)
            b_minx, b_miny, b_maxx, b_maxy = u_geom.bounds
            margin = 6.0
            extent_box = box(b_minx - margin, b_miny - margin, b_maxx + margin, b_maxy + margin)

            fig, axes = plt.subplots(1, 2, figsize=(16, 8), layout='constrained')
            
            # Left: BEFORE (Current partial T10:A1 + historical rejected)
            before_layers = [
                {
                    'geometry': t10_geom,
                    'color': '#FF6B00',
                    'lw': 2.0,
                    'ls': '-',
                    'label': f"T10:A1 Parțial curent ({len(t10_geom.exterior.coords)-1} vârfuri, {t10_geom.area:.1f} m²)"
                }
            ]
            if hist_geom is not None:
                before_layers.append({
                    'geometry': hist_geom,
                    'color': '#C800FF',
                    'lw': 1.2,
                    'ls': '--',
                    'label': "Mască istorică respinsă (decupată)"
                })
            draw_panel(axes[0], ortho, extent_box, before_layers, "T10 ÎNAINTE: Geometrie parțială T10:A1 (nesatisfăcătoare)")

            # Right: AFTER (New hypothesis + previous faint reference)
            after_layers = [
                {
                    'geometry': t10_geom,
                    'color': '#FF6B00',
                    'lw': 1.0,
                    'ls': ':',
                    'label': "T10:A1 Parțial anterior (referință)"
                }
            ]
            if raw_attempts_records:
                after_layers.append({
                    'geometry': raw_attempts_records[0]['geometry'],
                    'color': '#00E5FF',
                    'lw': 1.0,
                    'ls': '--',
                    'label': f"Mască SAM2 brută (scor {raw_attempts_records[0]['sam2_score']:.3f})"
                })
            for r in records:
                after_layers.append({
                    'geometry': r['geometry'],
                    'color': '#00FF66',
                    'lw': 2.2,
                    'ls': '-',
                    'label': f"T10 Nou rectificat ({r['vertices']} vârfuri, {r['geometry'].area:.1f} m², supp={r['simple_support']:.2f})"
                })
            title_after = f"T10 DUPĂ: Noua ipoteză rectificată [{retry['status']}] (PENDING_OWNER_REVIEW)"
            draw_panel(axes[1], ortho, extent_box, after_layers, title_after)

            fig.suptitle(
                "StratumRO — Cazul T10:A1: Comparație ÎNAINTE (Parțial nesatisfăcător) vs DUPĂ (Rectificare)\n"
                "[Statut: PENDING_OWNER_REVIEW — Necesar verdict proprietar]",
                fontsize=13, fontweight='bold'
            )
            fig.savefig(out / 't10_before_after.png', dpi=200)
            plt.close(fig)

    print(f"[T10] Diagnoza finalizata. Status: {retry['status']}. Ipoteze retinute: {len(records)}. Rezultate in {out}", flush=True)


if __name__ == '__main__':
    main()
