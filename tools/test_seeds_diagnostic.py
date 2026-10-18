# -*- coding: utf-8 -*-
from pathlib import Path
import json
import rasterio
import numpy as np
from shapely.geometry import box
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from stratum_ro.lidar_processor import LidarProcessor
from stratum_ro.roof_retry import roof_retry_prompts

def main():
    lidar = LidarProcessor('C:/Users/lefpa/Desktop/date/Z_VladP/Comparatie/LAZ/NorPuncte_St70_S42.laz',
                           'C:/Users/lefpa/Desktop/date/Z_VladP/Comparatie/DTM3m/DTM3m.tif').process_multicategory()

    with open(ROOT / 'workspace/reviews/lot3_revision_20261013/selection_manifest.json') as f:
        manifest = json.load(f)

    for c in manifest['cases']:
        tid = c['test_id']
        geom = box(*c['target_extent'])
        tile = c['tile']
        with rasterio.open(tile) as src:
            rgb = np.moveaxis(src.read([1, 2, 3]), 0, -1)
            res = roof_retry_prompts(geom, rgb, src.transform, lidar)
            seeds = res.get('seeds', [])
            print(f"{tid}: status={res['status']}, seed_count={len(seeds)}")
            for s in seeds:
                print(f"   pt={s['point']}, area={s['area_m2']:.1f}m2, mean_h={s['mean_h']:.1f}m")

if __name__ == '__main__':
    main()
