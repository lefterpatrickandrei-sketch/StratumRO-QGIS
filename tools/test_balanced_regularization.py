# -*- coding: utf-8 -*-
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import geopandas as gpd
from stratum_ro.roof_simple_geometry import roof_shape_variations, simple_roof_geometry
from stratum_ro.core.geometry.regularizer import compute_orthogonality_ratio, orthogonalize_cad, remove_acute_spikes

gdf = gpd.read_file(ROOT / "workspace/reviews/option_b_repair_20261019_v2/simple_variations.gpkg", layer="B_SIMPLE")

for cid in ['OPT_B_046:C1', 'OPT_B_126:C1', 'OPT_B_144:C1', 'OPT_B_028:C1', 'OPT_B_035:C1']:
    sub = gdf[gdf['candidate_id'] == cid]
    if len(sub) == 0:
        continue
    g = sub.iloc[0].geometry

    # Test balanced simplification: Douglas-Peucker 0.8m - 1.0m to remove teeth
    for tol in [0.6, 0.8, 1.0, 1.2]:
        s = g.simplify(tol, preserve_topology=True)
        # Check variations on simplified
        try:
            chosen, alts = roof_shape_variations(s, min_support=0.82, min_coverage=0.82, min_edge=1.2)
            ortho_alts = [a for a in alts if a.get('eligible') and a.get('method') in ['ORTHOGONAL_RUNS', 'RECTANGLE']]
        except Exception:
            ortho_alts = []

        if ortho_alts:
            ortho_alts.sort(key=lambda x: x.get('iou', 0), reverse=True)
            res = ortho_alts[0]['geometry']
            fam = ortho_alts[0]['family']
            m = f"ORTHO_RUNS_{fam}"
        else:
            res = orthogonalize_cad(s, tolerance=0.7)
            m = "CAD_ORTHO"

        res = remove_acute_spikes(res, min_angle_deg=70.0)
        n = len(res.exterior.coords) - 1 if res and res.is_valid else 0
        ratio = compute_orthogonality_ratio(res) if res and res.is_valid else 0
        iou = g.intersection(res).area / g.union(res).area if res and res.is_valid else 0
        print(f"cid={cid}, tol={tol}: {m}, nodes={n}, ortho={ratio:.2f}, iou={iou:.3f}, area={res.area:.1f}")
