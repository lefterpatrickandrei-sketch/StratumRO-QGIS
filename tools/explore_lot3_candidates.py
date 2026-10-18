# -*- coding: utf-8 -*-
"""
Deep exploration tool for Lot 3 candidates T11-T20.
Dumps diagnostic visual multi-panels (RGB, nDSM, Class 6) for each candidate.
"""
from pathlib import Path
import json
import rasterio
from rasterio.windows import from_bounds
import numpy as np
import matplotlib.pyplot as plt
from shapely.geometry import box, Point

ROOT = Path(__file__).resolve().parent.parent
VRT_PATH = ROOT / 'workspace/output/ortofoto_cluj_usamv_rgb.vrt'
LAZ_PATH = 'C:/Users/lefpa/Desktop/date/Z_VladP/Comparatie/LAZ/NorPuncte_St70_S42.laz'
DTM_PATH = 'C:/Users/lefpa/Desktop/date/Z_VladP/Comparatie/DTM3m/DTM3m.tif'
MANIFEST_PATH = ROOT / 'workspace/reviews/lot3_20261013/selection_manifest.json'
OUT_DIR = ROOT / 'workspace/reviews/lot3_revision_20261013/diagnostics'
OUT_DIR.mkdir(parents=True, exist_ok=True)

import sys
sys.path.insert(0, str(ROOT))

from stratum_ro.lidar_processor import LidarProcessor

def main():
    print("Loading LiDAR data...")
    lidar = LidarProcessor(LAZ_PATH, DTM_PATH).process_multicategory()
    ndsm = lidar['ndsm']
    building = lidar['class_evidence']['building']
    tr_lidar = lidar['transform']

    with open(MANIFEST_PATH, 'r', encoding='utf-8') as f:
        manifest = json.load(f)

    with rasterio.open(VRT_PATH) as vrt:
        for case in manifest['cases']:
            tid = case['test_id']
            pt = case['search_center']
            bbox = case['search_bbox']
            
            # Context window: 70m x 70m around center
            cx, cy = pt
            w = 35.0
            ctx_bounds = (cx - w, cy - w, cx + w, cy + w)
            
            # 1. Read RGB from VRT
            win = from_bounds(*ctx_bounds, vrt.transform)
            win_tr = rasterio.windows.transform(win, vrt.transform)
            rgb = np.moveaxis(vrt.read([1, 2, 3], window=win), 0, -1)
            ext_rgb = [win_tr.c, win_tr.c + win.width * win_tr.a,
                       win_tr.f + win.height * win_tr.e, win_tr.f]

            # 2. Extract nDSM in same extent
            # Map extent to lidar pixels
            c0, r0 = (~tr_lidar)*(ctx_bounds[0], ctx_bounds[3])
            c1, r1 = (~tr_lidar)*(ctx_bounds[2], ctx_bounds[1])
            c_min, c_max = max(0, int(min(c0, c1))), min(ndsm.shape[1], int(max(c0, c1)))
            r_min, r_max = max(0, int(min(r0, r1))), min(ndsm.shape[0], int(max(r0, r1)))
            sub_ndsm = ndsm[r_min:r_max, c_min:c_max]
            sub_bld = building[r_min:r_max, c_min:c_max]
            
            # Coordinates for lidar extent
            x_min, y_max = tr_lidar * (c_min, r_min)
            x_max, y_min = tr_lidar * (c_max, r_max)
            ext_lidar = [x_min, x_max, y_min, y_max]

            # Create plot with 3 panels
            fig, axes = plt.subplots(1, 3, figsize=(18, 6))
            
            # Panel 1: RGB with original bbox and point
            ax = axes[0]
            ax.imshow(rgb, extent=ext_rgb)
            # draw bbox
            bx = [bbox[0], bbox[2], bbox[2], bbox[0], bbox[0]]
            by = [bbox[1], bbox[1], bbox[3], bbox[3], bbox[1]]
            ax.plot(bx, by, color='yellow', linestyle='--', linewidth=1.5, label='orig bbox')
            ax.plot(pt[0], pt[1], 'ro', markersize=6, label='orig center')
            ax.set_title(f"{tid}: RGB Ortho (Context 70m)", fontsize=11, fontweight='bold')
            ax.legend(loc='lower left', fontsize=8)
            ax.axis('off')

            # Panel 2: nDSM
            ax = axes[1]
            im = ax.imshow(sub_ndsm, extent=ext_lidar, cmap='viridis', vmin=0, vmax=15)
            ax.plot(bx, by, color='white', linestyle='--', linewidth=1.5)
            ax.plot(pt[0], pt[1], 'ro', markersize=6)
            ax.set_title(f"{tid}: LiDAR nDSM (Height 0-15m)", fontsize=11, fontweight='bold')
            plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
            ax.axis('off')

            # Panel 3: Building returns
            ax = axes[2]
            im_b = ax.imshow(sub_bld, extent=ext_lidar, cmap='magma', vmin=0, vmax=5)
            ax.plot(bx, by, color='cyan', linestyle='--', linewidth=1.5)
            ax.plot(pt[0], pt[1], 'ro', markersize=6)
            ax.set_title(f"{tid}: Building Class Returns", fontsize=11, fontweight='bold')
            plt.colorbar(im_b, ax=ax, fraction=0.046, pad=0.04)
            ax.axis('off')

            fig.suptitle(f"{tid} — {case['archetype']} ({case['tile']})", fontsize=13, fontweight='bold')
            plt.tight_layout()
            out_p = OUT_DIR / f"{tid}_diagnostic.png"
            plt.savefig(out_p, dpi=150)
            plt.close()
            print(f"Saved diagnostic for {tid} -> {out_p}")

if __name__ == '__main__':
    main()
