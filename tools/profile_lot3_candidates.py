# -*- coding: utf-8 -*-
from pathlib import Path
import json
import rasterio
import numpy as np
from scipy.ndimage import label, find_objects
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from stratum_ro.lidar_processor import LidarProcessor

VRT_PATH = ROOT / 'workspace/output/ortofoto_cluj_usamv_rgb.vrt'
LAZ_PATH = 'C:/Users/lefpa/Desktop/date/Z_VladP/Comparatie/LAZ/NorPuncte_St70_S42.laz'
DTM_PATH = 'C:/Users/lefpa/Desktop/date/Z_VladP/Comparatie/DTM3m/DTM3m.tif'
MANIFEST_PATH = ROOT / 'workspace/reviews/lot3_20261013/selection_manifest.json'

def main():
    lidar = LidarProcessor(LAZ_PATH, DTM_PATH).process_multicategory()
    ndsm = lidar['ndsm']
    building = lidar['class_evidence']['building']
    tr = lidar['transform']

    with open(MANIFEST_PATH, 'r', encoding='utf-8') as f:
        manifest = json.load(f)

    with rasterio.open(VRT_PATH) as vrt:
        for case in manifest['cases']:
            tid = case['test_id']
            pt = case['search_center']
            bbox = case['search_bbox']
            archetype = case['archetype']
            cx, cy = pt
            w = 40.0
            b = (cx - w, cy - w, cx + w, cy + w)
            c0, r0 = (~tr)*(b[0], b[3])
            c1, r1 = (~tr)*(b[2], b[1])
            c_min, c_max = max(0, int(min(c0, c1))), min(ndsm.shape[1], int(max(c0, c1)))
            r_min, r_max = max(0, int(min(r0, r1))), min(ndsm.shape[0], int(max(r0, r1)))
            sub_h = ndsm[r_min:r_max, c_min:c_max]
            sub_b = building[r_min:r_max, c_min:c_max]
            
            clump = (sub_h >= 2.5) & ((sub_b > 0) | (sub_h >= 3.5))
            labs, num = label(clump)
            print(f"\n=== {tid} ({archetype}) ===")
            print(f"Orig center: {pt}, Orig bbox: {bbox}")
            
            for i, sl in enumerate(find_objects(labs), 1):
                if sl is None: continue
                comp = labs[sl] == i
                area = comp.sum() * abs(tr.determinant)
                if area < 25: continue
                rr, cc = np.indices(comp.shape)
                rr, cc = rr[comp] + sl[0].start + r_min, cc[comp] + sl[1].start + c_min
                xs, ys = tr * (cc + 0.5, rr + 0.5)
                mean_h = float(np.mean(ndsm[rr, cc]))
                max_h = float(np.max(ndsm[rr, cc]))
                b_ret = int(np.sum(building[rr, cc] > 0))
                center_x, center_y = float(np.median(xs)), float(np.median(ys))
                bounds = [round(float(np.min(xs)-1), 1), round(float(np.min(ys)-1), 1),
                          round(float(np.max(xs)+1), 1), round(float(np.max(ys)+1), 1)]
                dist = np.hypot(center_x - pt[0], center_y - pt[1])
                
                # Sample RGB at clump center
                r_vrt, c_vrt = vrt.index(center_x, center_y)
                px = vrt.read([1, 2, 3], window=rasterio.windows.Window(c_vrt, r_vrt, 1, 1))
                rgb = px[:, 0, 0].tolist()
                print(f"  Clump #{i}: area={area:.1f}m2, mean_h={mean_h:.1f}m, max_h={max_h:.1f}m, bld_ret={b_ret}, center=({center_x:.1f}, {center_y:.1f}), dist={dist:.1f}m, RGB={rgb}, bounds={bounds}")

if __name__ == '__main__':
    main()
