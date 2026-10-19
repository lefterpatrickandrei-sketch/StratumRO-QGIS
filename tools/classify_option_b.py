# -*- coding: utf-8 -*-
"""
tools/classify_option_b.py
==========================
Classifies ALL Option B regional cases (216) with an explicit reason per case.

Design rules (AGENTS.md, "Dovezi si statut"):
* Every case is classified; none is dropped silently. The primary reasons plus
  the passed cases always sum to the number of input cases (partition check).
* Sensor facts (NoData contact, RGB validity, nDSM height, route) are READ from
  measured evidence (sensor_validation.json); they are never assigned here and
  no candidate id is special-cased.
* Missing, partial or stale evidence never counts as a pass.
* Geometry is never modified here (no clipping, no seam cuts). Overlaps are
  reported, not repaired.
* The only positive status is GATES_PASSED_PENDING_OWNER_REVIEW. It means the
  internal development gates found no blocking flag. It is NOT acceptance, NOT
  ANCPI validation and says nothing about recall or cadastral accuracy.
* Thresholds are development signals, not legal criteria.
"""

import argparse
import hashlib
import json
import math
import sys
from collections import Counter
from dataclasses import dataclass, asdict
from pathlib import Path

import numpy as np
from shapely.geometry import Polygon
from shapely.strtree import STRtree

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE_GPKG = ROOT / "workspace" / "reviews" / "option_b_repair_20261019_v2" / "simple_variations.gpkg"
DEFAULT_EVIDENCE = ROOT / "workspace" / "option_b_validation_20261019" / "sensor_validation.json"

PASS_STATUS = "GATES_PASSED_PENDING_OWNER_REVIEW"
FLAGGED_STATUS = "FLAGGED_NOT_PROPOSED"

# Flag codes
INVALID_GEOMETRY = "INVALID_GEOMETRY"
EVIDENCE_STALE = "EVIDENCE_STALE"
NO_SENSOR_EVIDENCE = "NO_SENSOR_EVIDENCE"
NODATA_CONTACT = "NODATA_CONTACT"
RGB_VALIDITY_BELOW_THRESHOLD = "RGB_VALIDITY_BELOW_THRESHOLD"
SUSPECT_SOL_SUB_1_8M = "SUSPECT_SOL_SUB_1_8M"
SUSPECT_VEGETATION = "SUSPECT_VEGETATION"
HEIGHT_MISSING_OR_PARTIAL = "HEIGHT_MISSING_OR_PARTIAL"
OVERLAP_CONTAINED = "OVERLAP_CONTAINED"
OVERLAP_CONTAINS_OTHER = "OVERLAP_CONTAINS_OTHER"            # informational
OVERLAP_SEAM = "OVERLAP_SEAM"
OVERLAP_WITH_FLAGGED_PARTNER = "OVERLAP_WITH_FLAGGED_PARTNER"  # informational
UPSTREAM_DIAGNOSTIC = "UPSTREAM_DIAGNOSTIC"
DUPLICATE_NODES = "DUPLICATE_NODES"
SPURIOUS_HOLE = "SPURIOUS_HOLE"
ACUTE_ANGLE = "ACUTE_ANGLE"
SHORT_EDGE = "SHORT_EDGE"                                    # informational

# Order decides the single primary reason of a flagged case.
PRIORITY = [
    INVALID_GEOMETRY, EVIDENCE_STALE, NO_SENSOR_EVIDENCE, NODATA_CONTACT,
    RGB_VALIDITY_BELOW_THRESHOLD, SUSPECT_SOL_SUB_1_8M, SUSPECT_VEGETATION,
    HEIGHT_MISSING_OR_PARTIAL, OVERLAP_CONTAINED, OVERLAP_SEAM,
    UPSTREAM_DIAGNOSTIC, DUPLICATE_NODES, SPURIOUS_HOLE, ACUTE_ANGLE,
]
INFORMATIONAL = {OVERLAP_CONTAINS_OTHER, OVERLAP_WITH_FLAGGED_PARTNER, SHORT_EDGE}
GEOMETRY_ARTIFACTS = {DUPLICATE_NODES, SPURIOUS_HOLE, ACUTE_ANGLE}


@dataclass(frozen=True)
class Thresholds:
    min_height_median_m: float = 1.8      # development signal, not a legal threshold
    min_valid_fraction: float = 0.995
    containment: float = 0.80
    min_overlap_m2: float = 0.05
    min_hole_area_m2: float = 2.0
    min_angle_deg: float = 40.0
    short_edge_m: float = 1.0
    duplicate_node_tol_m: float = 1e-4


def geometry_metrics(geom, th=Thresholds()):
    """Measured geometry facts. Never modifies the geometry."""
    m = dict(valid=False, duplicate_nodes=0, hole_areas_m2=[], min_edge_m=None,
             min_angle_deg=None, n_vertices=0, area_m2=0.0)
    if geom is None or geom.is_empty:
        return m
    m["valid"] = bool(geom.is_valid)
    m["area_m2"] = float(geom.area)
    polys = list(geom.geoms) if geom.geom_type == "MultiPolygon" else [geom]
    edges, angles = [], []
    for poly in polys:
        if poly.geom_type != "Polygon":
            continue
        for ring in [poly.exterior, *poly.interiors]:
            coords = np.asarray(ring.coords)
            seg = np.linalg.norm(np.diff(coords, axis=0), axis=1)
            m["duplicate_nodes"] += int((seg <= th.duplicate_node_tol_m).sum())
            edges.extend(seg[seg > th.duplicate_node_tol_m].tolist())
            m["n_vertices"] += max(len(coords) - 1, 0)
        for hole in poly.interiors:
            m["hole_areas_m2"].append(float(Polygon(hole).area))
        pts = np.asarray(poly.exterior.coords)[:-1]
        if len(pts) >= 3:
            a = np.roll(pts, 1, axis=0) - pts
            b = np.roll(pts, -1, axis=0) - pts
            na, nb = np.linalg.norm(a, axis=1), np.linalg.norm(b, axis=1)
            ok = (na > 1e-6) & (nb > 1e-6)
            if ok.any():
                cos = (a[ok] * b[ok]).sum(axis=1) / (na[ok] * nb[ok])
                angles.extend(np.degrees(np.arccos(np.clip(cos, -1.0, 1.0))).tolist())
    m["min_edge_m"] = float(min(edges)) if edges else None
    m["min_angle_deg"] = float(min(angles)) if angles else None
    return m


def find_overlaps(ids, geoms, min_overlap_m2):
    """Pairs of valid geometries overlapping by more than min_overlap_m2."""
    usable = [g is not None and not g.is_empty and g.is_valid for g in geoms]
    tree = STRtree([g if ok else Polygon() for g, ok in zip(geoms, usable)])
    pairs = []
    for i, g in enumerate(geoms):
        if not usable[i]:
            continue
        for j in sorted(int(x) for x in tree.query(g)):
            if j <= i or not usable[j]:
                continue
            inter = g.intersection(geoms[j]).area
            if inter > min_overlap_m2:
                small = min(g.area, geoms[j].area)
                pairs.append(dict(a=ids[i], b=ids[j], overlap_m2=round(float(inter), 3),
                                  containment=round(float(inter / small), 3),
                                  smaller=ids[i] if g.area <= geoms[j].area else ids[j]))
    return pairs


def _num(value):
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def load_evidence(evidence_path, source_gpkg):
    """Return (records, stale_reason). stale_reason is None only if the evidence
    file recorded the SHA-256 of the current source GeoPackage and it matches."""
    data = json.loads(Path(evidence_path).read_text(encoding="utf-8"))
    records = data.get("records", {})
    recorded = {Path(k.replace("\\", "/")).as_posix(): v for k, v in data.get("source_sha256", {}).items()}
    try:
        rel = Path(source_gpkg).resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return records, "SOURCE_OUTSIDE_REPOSITORY_HASH_NOT_COMPARABLE"
    if rel not in recorded:
        return records, "SOURCE_HASH_NOT_RECORDED_IN_EVIDENCE"
    if sha256_file(source_gpkg) != recorded[rel]:
        return records, "SOURCE_HASH_MISMATCH"
    return records, None


def classify(cases, evidence, *, stale_reason=None, accept_stale=False,
             th=Thresholds(), geometry_artifacts_blocking=True, evidence_tag="new"):
    """cases: iterable of dict(candidate_id, geometry, is_proposal).
    Returns (per_case_list, summary_dict). Geometry is never modified."""
    cases = list(cases)
    ids = [str(c["candidate_id"]) for c in cases]
    if len(set(ids)) != len(ids):
        raise ValueError("candidate_id values must be unique")
    geoms = [c.get("geometry") for c in cases]

    flags = {cid: [] for cid in ids}
    metrics = {}
    measured = {}

    def add(cid, code, blocking, detail=None):
        flags[cid].append(dict(code=code, blocking=bool(blocking), detail=detail))

    # --- pass 1: per-case facts -------------------------------------------
    for cid, case, geom in zip(ids, cases, geoms):
        gm = geometry_metrics(geom, th)
        metrics[cid] = gm
        if not gm["valid"]:
            add(cid, INVALID_GEOMETRY, True)
        if stale_reason:
            add(cid, EVIDENCE_STALE, not accept_stale, stale_reason)
        ev = (evidence.get(cid) or {}).get(evidence_tag)
        if not ev:
            add(cid, NO_SENSOR_EVIDENCE, True)
            ev = {}
        measured[cid] = {k: ev.get(k) for k in (
            "touches_nodata", "rgb_valid_fraction", "height_valid_fraction",
            "height_median_m", "h90_m", "route")} if ev else {}
        if ev:
            if ev.get("touches_nodata") is None:
                add(cid, NO_SENSOR_EVIDENCE, True, "touches_nodata missing")
            elif bool(ev["touches_nodata"]):
                add(cid, NODATA_CONTACT, True)
            rgb = _num(ev.get("rgb_valid_fraction"))
            if rgb is None:
                add(cid, NO_SENSOR_EVIDENCE, True, "rgb_valid_fraction missing")
            elif rgb < th.min_valid_fraction:
                add(cid, RGB_VALIDITY_BELOW_THRESHOLD, True, round(rgb, 4))
            hv = _num(ev.get("height_valid_fraction"))
            med = _num(ev.get("height_median_m"))
            if hv is None or med is None or hv < th.min_valid_fraction:
                add(cid, HEIGHT_MISSING_OR_PARTIAL, True, hv)
            elif med < th.min_height_median_m:
                add(cid, SUSPECT_SOL_SUB_1_8M, True,
                    dict(height_median_m=round(med, 3), h90_m=_num(ev.get("h90_m"))))
            if ev.get("route") == "LIKELY_VEGETATION_REVIEW":
                add(cid, SUSPECT_VEGETATION, True, _num(ev.get("vegetation_fraction")))
        if not case.get("is_proposal", True):
            add(cid, UPSTREAM_DIAGNOSTIC, True, "separated as diagnostic upstream")
        if gm["duplicate_nodes"]:
            add(cid, DUPLICATE_NODES, geometry_artifacts_blocking, gm["duplicate_nodes"])
        small = [a for a in gm["hole_areas_m2"] if a < th.min_hole_area_m2]
        if small:
            add(cid, SPURIOUS_HOLE, geometry_artifacts_blocking, [round(a, 3) for a in small])
        if gm["min_angle_deg"] is not None and gm["min_angle_deg"] < th.min_angle_deg:
            add(cid, ACUTE_ANGLE, geometry_artifacts_blocking, round(gm["min_angle_deg"], 2))
        if gm["min_edge_m"] is not None and gm["min_edge_m"] < th.short_edge_m:
            add(cid, SHORT_EDGE, False, round(gm["min_edge_m"], 3))

    # --- pass 2: overlaps, aware of whether the partner is already flagged ---
    base_blocked = {cid: any(f["blocking"] for f in flags[cid]) for cid in ids}
    overlaps = find_overlaps(ids, geoms, th.min_overlap_m2)
    for p in overlaps:
        for cid, partner in ((p["a"], p["b"]), (p["b"], p["a"])):
            detail = dict(partner=partner, overlap_m2=p["overlap_m2"], containment=p["containment"])
            if base_blocked[partner]:
                add(cid, OVERLAP_WITH_FLAGGED_PARTNER, False, detail)
            elif p["containment"] >= th.containment:
                if cid == p["smaller"]:
                    add(cid, OVERLAP_CONTAINED, True, detail)
                else:
                    add(cid, OVERLAP_CONTAINS_OTHER, False, detail)
            else:
                add(cid, OVERLAP_SEAM, True, detail)

    # --- result ------------------------------------------------------------
    results = []
    for cid, geom in zip(ids, geoms):
        blocking_codes = {f["code"] for f in flags[cid] if f["blocking"]}
        primary = next((c for c in PRIORITY if c in blocking_codes), None)
        results.append(dict(
            candidate_id=cid,
            status=FLAGGED_STATUS if blocking_codes else PASS_STATUS,
            primary_reason=primary,
            flags=flags[cid],
            metrics=metrics[cid],
            measured=measured[cid],
            geometry_sha256=hashlib.sha256(geom.wkb).hexdigest() if geom is not None and not geom.is_empty else None,
        ))

    by_primary = Counter(r["primary_reason"] for r in results if r["primary_reason"])
    passed = sum(r["status"] == PASS_STATUS for r in results)
    by_any = Counter(f["code"] for r in results for f in r["flags"])
    summary = dict(
        total=len(results), passed_pending_owner_review=passed,
        flagged=len(results) - passed,
        by_primary_reason=dict(by_primary), by_any_flag=dict(by_any),
        partition_ok=(sum(by_primary.values()) + passed == len(results)),
        overlap_pairs=len(overlaps), overlaps=overlaps,
        evidence_stale_reason=stale_reason, evidence_stale_accepted=bool(stale_reason and accept_stale),
        geometry_artifacts_blocking=geometry_artifacts_blocking,
        thresholds=asdict(th),
        note=("Internal development gates only. Not owner acceptance, not ANCPI validation; "
              "no recall or cadastral accuracy is measured. Thresholds are not legal criteria."),
    )
    return results, summary


def run(source_gpkg, geometry_layer, proposals_layer, evidence_path, *, geometry_gpkg=None,
        accept_stale=False, geometry_artifacts_blocking=True):
    import geopandas as gpd
    source_gpkg = Path(source_gpkg)
    geometry_gpkg = Path(geometry_gpkg) if geometry_gpkg else source_gpkg
    gdf = gpd.read_file(geometry_gpkg, layer=geometry_layer)
    proposal_ids = set(gpd.read_file(source_gpkg, layer=proposals_layer)["candidate_id"])
    records, stale = load_evidence(evidence_path, source_gpkg)
    cases = [dict(candidate_id=r["candidate_id"], geometry=r.geometry,
                  is_proposal=r["candidate_id"] in proposal_ids) for _, r in gdf.iterrows()]
    results, summary = classify(cases, records, stale_reason=stale, accept_stale=accept_stale,
                                geometry_artifacts_blocking=geometry_artifacts_blocking)
    summary.update(source_gpkg=str(source_gpkg), geometry_gpkg=str(geometry_gpkg),
                   geometry_layer=geometry_layer, proposals_layer=proposals_layer,
                   evidence=str(evidence_path), crs=str(gdf.crs))
    return results, summary


def main(argv=None):
    ap = argparse.ArgumentParser(description="Classify all Option B cases with reason codes")
    ap.add_argument("--source-gpkg", default=str(DEFAULT_SOURCE_GPKG))
    ap.add_argument("--geometry-gpkg", default=None, help="GeoPackage holding the geometry layer (default: source)")
    ap.add_argument("--geometry-layer", default="B_SIMPLE")
    ap.add_argument("--proposals-layer", default="B_ROOF_PROPOSALS")
    ap.add_argument("--evidence", default=str(DEFAULT_EVIDENCE))
    ap.add_argument("--geometry-stage", choices=["raw", "cleaned"], default="raw",
                    help="raw: geometry artifacts (dup nodes, holes, spikes) are informational; "
                         "cleaned: they block")
    ap.add_argument("--accept-stale-evidence", action="store_true")
    ap.add_argument("--expected-total", type=int, default=216)
    ap.add_argument("--json-output", default=None)
    args = ap.parse_args(argv)

    results, summary = run(args.source_gpkg, args.geometry_layer, args.proposals_layer, args.evidence,
                           geometry_gpkg=args.geometry_gpkg, accept_stale=args.accept_stale_evidence,
                           geometry_artifacts_blocking=(args.geometry_stage == "cleaned"))
    ok = summary["partition_ok"] and summary["total"] == args.expected_total
    summary["expected_total"] = args.expected_total
    summary["partition_check"] = "OK" if ok else "FAILED"

    print(f"total={summary['total']} passed={summary['passed_pending_owner_review']} "
          f"flagged={summary['flagged']} partition={summary['partition_check']}")
    for code, n in sorted(summary["by_primary_reason"].items(), key=lambda kv: -kv[1]):
        print(f"  {code}: {n}")
    if summary["evidence_stale_reason"]:
        print(f"[!] evidence stale: {summary['evidence_stale_reason']}")

    if args.json_output:
        out = Path(args.json_output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(dict(summary=summary, cases=results), indent=2, default=str), encoding="utf-8")
        print(f"[*] report: {out}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
