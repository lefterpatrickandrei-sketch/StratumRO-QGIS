"""Merge VLM advice into the 2D roof proposals and prepare them for 3D cadastre (local, no GPU).

Per building:
  stare            ADMIS_PROPUS (VLM p(ADMIS) >= --admis-thr) or INCERT; owner_verdict stays PENDING_OWNER_REVIEW
  tip_acoperis     roof shape (TERASA_PLAT, O_APA, DOUA_APE, PATRU_APE, MANSARDA, COMPLEX, ALTUL): LiDAR decides
                   flat vs pitched where it covers the roof, the VLM picks the shape among the allowed ones
  tip_ndsm         independent LiDAR hint: PLAT when the nDSM relief inside the roof is < 1 m, otherwise INCLINAT
  h_streasina_m / h_coama_m / h_relief_m   nDSM p15 / p98 / difference inside the roof (1 m grid, metres above ground)
  ajustare_m       mean parallel shift applied to the edges when snapping them onto the eave line

Edge snapping moves each edge parallel to itself (-0.9..+0.9 m) to the offset with the strongest outline
probability (ensemble edge head, trained on owner eaves); neighbouring edges are re-intersected, so right
angles stay right. New buildings come from the candidate chips the VLM did not call ELIMINAT.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from roof2d_data import rasterize  # noqa: E402
from scan_roof2d_aoi import resolve_overlaps  # noqa: E402

ROOF_RO = {"FLAT": "TERASA_PLAT", "SHED": "O_APA", "GABLE": "DOUA_APE", "HIP": "PATRU_APE",
           "MANSARD": "MANSARDA", "COMPLEX": "COMPLEX", "OTHER": "ALTUL"}


def _intersect(p1, d1, p2, d2):
    """Intersection of lines p1 + t d1 and p2 + s d2 (None when parallel)."""
    den = d1[0] * d2[1] - d1[1] * d2[0]
    if abs(den) < 1e-9:
        return None
    t = ((p2[0] - p1[0]) * d2[1] - (p2[1] - p1[1]) * d2[0]) / den
    return p1 + t * d1


def snap_edges(poly, sample, max_shift: float = 0.9, step: float = 0.15, min_gain: float = 0.05):
    """Shift each edge parallel to itself onto the strongest outline response. Returns (polygon, mean |shift|)."""
    from shapely.geometry import Polygon

    pts = np.asarray(poly.exterior.coords)[:-1].astype(float)
    n = len(pts)
    if n < 4 or n > 16:
        return poly, 0.0
    ccw = Polygon(pts).exterior.is_ccw
    shifts = []
    for i in range(n):
        a, b = pts[i], pts[(i + 1) % n]
        d = b - a
        length = float(np.hypot(*d))
        if length < 1.0:
            continue
        u = d / length
        normal = np.array([u[1], -u[0]]) if ccw else np.array([-u[1], u[0]])  # outward

        def score(off):
            ts = np.linspace(0.1, 0.9, max(5, int(length / 0.3)))
            return float(np.mean([sample(a + t * d + off * normal) for t in ts]))

        offs = np.arange(-max_shift, max_shift + 1e-9, step)
        vals = [score(o) for o in offs]
        best = int(np.argmax(vals))
        if vals[best] < score(0.0) + min_gain:
            continue
        off = float(offs[best])
        pa, pb = pts[i - 1], pts[(i + 2) % n]
        new_a = _intersect(pts[i - 1], a - pa, a + off * normal, u)
        new_b = _intersect(b + off * normal, u, pb, pb - b)
        if new_a is None or new_b is None:
            continue
        cand = pts.copy()
        cand[i], cand[(i + 1) % n] = new_a, new_b
        cp = Polygon(cand)
        if cp.is_valid and abs(cp.area - Polygon(pts).area) < 0.3 * Polygon(pts).area:
            pts = cand
            shifts.append(abs(off))
    out = Polygon(pts)
    return (out if out.is_valid else poly), (float(np.mean(shifts)) if shifts else 0.0)


def ndsm_attrs(poly, ndsm, ndsm_t) -> dict:
    inner = poly.buffer(-0.5)
    m = rasterize([inner if not inner.is_empty else poly], ndsm_t, ndsm.shape, all_touched=True)
    v = ndsm[m & np.isfinite(ndsm)]
    if v.size < 3:
        return {"h_streasina_m": None, "h_coama_m": None, "h_relief_m": None, "tip_ndsm": "FARA_LIDAR"}
    lo, hi = float(np.percentile(v, 15)), float(np.percentile(v, 98))
    return {"h_streasina_m": round(lo, 2), "h_coama_m": round(hi, 2), "h_relief_m": round(hi - lo, 2),
            "tip_ndsm": "PLAT" if hi - lo < 1.0 else "INCLINAT"}


def merge(final_gpkg: Path, chips_dir: Path, preds_path: Path, probs: Path, ndsm_path: Path, out: Path,
          admis_thr: float, drop_elim_thr: float) -> dict:
    import geopandas as gpd
    import rasterio

    preds = json.loads(Path(preds_path).read_text(encoding="utf-8"))
    with rasterio.open(probs) as src:
        edge, transform = src.read(2).astype(np.float32) / 255.0, src.transform
    inv = ~transform

    def sample(xy):
        c, r = inv * (float(xy[0]), float(xy[1]))
        r, c = int(r), int(c)
        return edge[r, c] if 0 <= r < edge.shape[0] and 0 <= c < edge.shape[1] else 0.0

    with rasterio.open(ndsm_path) as src:
        ndsm, ndsm_t = src.read(1).astype(np.float32), src.transform

    props = gpd.read_file(final_gpkg, layer="proposals_all")
    cands = gpd.read_file(chips_dir / "candidates_epsg3844.gpkg", layer="candidates")
    items = []
    for _, r in props.iterrows():
        items.append({"id": r.proposal_id, "sursa": "MODEL_ENSEMBLE", "geometry": r.geometry,
                      "mean_roof_prob": float(r.mean_roof_prob), "pred": preds.get("prop_" + r.proposal_id)})
    new_kept = new_dropped = 0
    for _, r in cands.iterrows():
        p = preds.get(r.candidate_id)
        model_sees_it = r.outline_source == "roof_prob_0.25"
        if p is None or p["verdict"]["ELIMINAT"] >= drop_elim_thr or not (model_sees_it or p["verdict"]["ADMIS"] >= 0.7):
            new_dropped += 1
            continue
        new_kept += 1
        items.append({"id": "NOU_" + r.candidate_id, "sursa": "NOU_LIDAR_" + r.outline_source.upper(),
                      "geometry": r.geometry, "mean_roof_prob": None, "pred": p})

    rows = []
    for it in items:
        g, shift = snap_edges(it["geometry"], sample)
        p = it["pred"] or {"verdict": {"ADMIS": 0.0, "AJUSTARE": 1.0, "ELIMINAT": 0.0}}
        v = p["verdict"]
        roof = p.get("roof_type", {})
        lid = ndsm_attrs(g, ndsm, ndsm_t)
        allowed = {"PLAT": ["FLAT"], "INCLINAT": [k for k in roof if k != "FLAT"]}.get(lid["tip_ndsm"], list(roof))
        rt = max(allowed, key=lambda k: roof.get(k, 0.0)) if roof else "OTHER"
        rows.append({
            "proposal_id": it["id"], "sursa": it["sursa"],
            "stare": "ADMIS_PROPUS" if v["ADMIS"] >= admis_thr else "INCERT",
            "owner_verdict": "PENDING_OWNER_REVIEW",
            "vlm_admis": v["ADMIS"], "vlm_ajustare": v["AJUSTARE"], "vlm_eliminat": v["ELIMINAT"],
            "tip_acoperis": ROOF_RO[rt], "tip_acoperis_prob": roof.get(rt), "mean_roof_prob": it["mean_roof_prob"],
            "ajustare_m": round(shift, 2), "geometry": g,
        })
    # snapping may push an edge into a neighbour: clip again, the VLM-preferred building wins
    kept, dropped = resolve_overlaps([(r["geometry"], r["vlm_admis"]) for r in rows], min_keep=0.5, with_index=True)
    final = []
    for g, _, _, k in kept:
        r = dict(rows[k], geometry=g, area_m2=round(g.area, 2))
        r.update(ndsm_attrs(g, ndsm, ndsm_t))
        final.append(r)
    gdf = gpd.GeoDataFrame(final, geometry="geometry", crs="EPSG:3844")
    if out.exists():
        out.unlink()
    for name, sub in {"cladiri_2d_toate": gdf, "admis_propus": gdf[gdf.stare == "ADMIS_PROPUS"],
                      "incert": gdf[gdf.stare == "INCERT"], "cladiri_noi": gdf[gdf.sursa.str.startswith("NOU")]}.items():
        sub.to_file(out, layer=name, driver="GPKG")
    agree = gdf[gdf.tip_ndsm != "FARA_LIDAR"]
    flat_vlm = agree.tip_acoperis == "TERASA_PLAT"
    return {
        "buildings": len(gdf), "admis_propus": int((gdf.stare == "ADMIS_PROPUS").sum()),
        "incert": int((gdf.stare == "INCERT").sum()), "new_buildings_kept": new_kept,
        "new_candidates_dropped_by_vlm": new_dropped, "dropped_after_snap_overlap": dropped,
        "edges_snapped_share": round(float((gdf.ajustare_m > 0).mean()), 3),
        "roof_types": gdf.tip_acoperis.value_counts().to_dict(),
        "flat_vs_lidar_agreement": round(float((flat_vlm == (agree.tip_ndsm == "PLAT")).mean()), 3) if len(agree) else None,
        "admis_thr": admis_thr,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--final", type=Path, default=REPO_ROOT / "workspace/reviews/final_2d_roofs_loopq4_epsg3844.gpkg")
    ap.add_argument("--chips", type=Path, required=True)
    ap.add_argument("--preds", type=Path, required=True)
    ap.add_argument("--probs", type=Path, default=REPO_ROOT / "workspace/colab_runs/loop_q/ens_b1_b3r_l3.tif")
    ap.add_argument("--ndsm", type=Path, default=REPO_ROOT / "workspace/derived/cluj_ndsm_1m.tif")
    ap.add_argument("--admis-thr", type=float, default=0.5)
    ap.add_argument("--drop-elim-thr", type=float, default=0.5)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)
    print(json.dumps(merge(args.final, args.chips, args.preds, args.probs, args.ndsm, args.out, args.admis_thr,
                           args.drop_elim_thr), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
