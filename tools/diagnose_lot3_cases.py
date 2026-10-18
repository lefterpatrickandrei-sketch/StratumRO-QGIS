# -*- coding: utf-8 -*-
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
OUT_DIR = ROOT / 'workspace/reviews/lot3_revision_20261013/case_studies'
OUT_DIR.mkdir(parents=True, exist_ok=True)

import sys
sys.path.insert(0, str(ROOT))
from stratum_ro.lidar_processor import LidarProcessor

def main():
    lidar = LidarProcessor(LAZ_PATH, DTM_PATH).process_multicategory()
    ndsm = lidar['ndsm']
    building = lidar['class_evidence']['building']
    tr_lidar = lidar['transform']

    with rasterio.open(VRT_PATH) as vrt:
        # T11 analysis
        # Looking at original T11 bbox: [391255.0, 585600.0, 391290.0, 585630.0]
        # In this vicinity, there is the residential building at x=391240..391260, y=585585..585605,
        # or at x=391275..391295, y=585590..585610.
        # Let's inspect a 60m x 60m box around (391270, 585615)
        print("T11...")
        # We will save detailed crop images with grid coordinates so we can read exact roof vertices and centers
        for tid, cx, cy, span in [
            ('T11', 391270, 585615, 30),
            ('T12', 391295, 585605, 30),
            ('T13', 391307, 585505, 30),
            ('T14', 391125, 585485, 35),
            ('T15', 390995, 585285, 35),
            ('T16', 390840, 585340, 35),
            ('T17', 390805, 585495, 45),
            ('T18', 390635, 585535, 45),
            ('T19', 390785, 585115, 35),
            ('T20', 391000, 585175, 50),
        ]:
            b = (cx - span, cy - span, cx + span, cy + span)
            win = from_bounds(*b, vrt.transform)
            rgb = np.moveaxis(vrt.read([1, 2, 3], window=win), 0, -1)
            win_tr = rasterio.windows.transform(win, vrt.transform)
            ext = [win_tr.c, win_tr.c + win.width * win_tr.a,
                   win_tr.f + win.height * win_tr.e, win_tr.f]
            
            fig, ax = plt.subplots(figsize=(10, 10))
            ax.imshow(rgb, extent=ext)
            # Add grid lines every 5 meters
            ax.set_xticks(np.arange(int(b[0]), int(b[2])+1, 5))
            ax.set_yticks(np.arange(int(b[1]), int(b[3])+1, 5))
            ax.grid(color='cyan', linestyle=':', linewidth=0.7, alpha=0.6)
            ax.set_title(f"{tid} — High-Res Grid Inspection ({span*2}m x {span*2}m)", fontsize=12, fontweight='bold')
            plt.savefig(OUT_DIR / f"{tid}_grid_inspection.png", dpi=200, bbox_inches='tight')
            plt.close()
            print(f"Saved {tid}_grid_inspection.png")

if __name__ == '__main__':
    main()
