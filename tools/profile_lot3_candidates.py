# -*- coding: utf-8 -*-
"""
Inspect specific candidate coordinates against orthophoto RGB and LiDAR nDSM
to compile detailed visual characteristics BEFORE finalizing the selection manifest.
"""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import rasterio
import numpy as np
from rasterio.windows import from_bounds
from stratum_ro.lidar_processor import LidarProcessor

# Test sample candidates
test_candidates = [
    # idx, tile, center_x, center_y, name/note
    (134, 'cache_tile_Cluj-2-0_halo.tif', 391271.5, 585615.4, 'Villa simple rect / gabled roof on eastern border'),
    (96,  'cache_tile_Cluj-2-0_halo.tif', 391294.6, 585609.3, 'Eastern residential house with garden/trees'),
    (81,  'cache_tile_Cluj-2-1_halo.tif', 391307.0, 585503.1, 'Residential house adjacent to neighboring building'),
    (59,  'cache_tile_Cluj-0-2_halo.tif', 390798.6, 585113.1, 'Southern utility building / simple pavilion'),
    (124, 'cache_tile_Cluj-0-2_halo.tif', 390827.0, 585151.7, 'Small isolated outbuilding / annex in south'),
    (39,  'cache_tile_Cluj-0-0_halo.tif', 390632.2, 585534.8, 'L/U-shaped farm pavilion or warehouse in NW'),
    (45,  'cache_tile_Cluj-0-0_halo.tif', 390615.0, 585593.5, 'Complex wing / adjacent structures NW'),
    (44,  'cache_tile_Cluj-0-1_halo.tif', 390801.5, 585494.5, 'Central-west academic building with multiple wings'),
    (50,  'cache_tile_Cluj-0-1_halo.tif', 390842.4, 585339.5, 'Dense cluster with 6 neighbors needing separation'),
    (38,  'cache_tile_Cluj-1-1_halo.tif', 390999.7, 585287.7, 'Campus pavilion partially shaded by large trees'),
    (46,  'cache_tile_Cluj-1-1_halo.tif', 391109.3, 585477.8, 'Elongated hall with gray/metal roof'),
    (33,  'cache_tile_Cluj-1-0_halo.tif', 391001.9, 585797.7, 'Northern pavilion adjacent to tree canopy'),
    (16,  'cache_tile_Cluj-1-2_halo.tif', 390997.5, 585178.5, 'Large southern complex / sports or exhibition hall'),
    (28,  'cache_tile_Cluj-1-0_halo.tif', 390903.7, 585561.7, 'Building near central alley with eave shadows')
]

tile_dir = ROOT / 'workspace/reviews/prompt_recovery_20261013/full_aoi'

print(f"{'IDX':<5} {'TILE':<28} {'CX, CY':<22} {'RGB MEAN':<18} {'NDVI/SAT':<10} {'NOTE'}")
print("-" * 105)

for idx, tile_name, cx, cy, note in test_candidates:
    tile_p = tile_dir / tile_name
    with rasterio.open(tile_p) as src:
        win = from_bounds(cx - 15, cy - 15, cx + 15, cy + 15, src.transform)
        rgb = src.read([1, 2, 3], window=win)
        r_m = float(np.mean(rgb[0]))
        g_m = float(np.mean(rgb[1]))
        b_m = float(np.mean(rgb[2]))
        color_desc = f"R={r_m:.0f},G={g_m:.0f},B={b_m:.0f}"
        coord_str = f"{cx:.1f}, {cy:.1f}"
    print(f"{idx:<5} {tile_name:<28} {coord_str:<22} {color_desc:<18} {note}")
