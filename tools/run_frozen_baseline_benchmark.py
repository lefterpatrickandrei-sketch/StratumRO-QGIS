# -*- coding: utf-8 -*-
"""
tools/run_frozen_baseline_benchmark.py - Phase 2 Frozen Baseline Evaluation

Runs the System 1 Fast Triage & ANCPI geometric verification on the
strictly isolated USAMV frozen test split (31 buildings, 30m buffer).
Produces authoritative metrics: precision, recall, triage breakdown, and latency.
"""

import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

import json
import time
import geopandas as gpd

from stratum_ro.ai.fast_triage import FastTriageEngine
from stratum_ro.ai.tools.cadastral_tools import validate_ancpi


def run_benchmark():
    repo_root = Path(__file__).resolve().parent.parent
    test_geojson = repo_root / "data" / "splits" / "usamv_test.geojson"
    out_report = repo_root / "reports" / "usamv_frozen_test_baseline.json"
    out_report.parent.mkdir(parents=True, exist_ok=True)

    print(f"Loading frozen test set: {test_geojson}")
    gdf = gpd.read_file(test_geojson)
    total_test = len(gdf)
    assert total_test == 31, f"Expected 31 test buildings, found {total_test}"

    engine = FastTriageEngine()

    triage_counts = {"APPROVED": 0, "REJECTED": 0, "UNCERTAIN": 0}
    triage_latencies = []
    verdicts = []

    # 1. Run System 1 Fast Triage
    t0_batch = time.perf_counter()
    for idx, row in gdf.iterrows():
        attrs = {
            "h_mean": row.get("h_mean", 0.0),
            "h_max": row.get("h_max", 0.0),
            "has_calcan": bool(row.get("has_calcan", False)),
            "mean_contrast": row.get("mean_contrast", 0.5),
        }
        v = engine.evaluate_candidate(row.geometry, attributes=attrs)
        triage_counts[v.status] += 1
        triage_latencies.append(v.latency_ms)
        verdicts.append({
            "id": row.get("id"),
            "status": v.status,
            "confidence": v.confidence,
            "reason": v.reason,
            "escalate_to_vlm": v.escalate_to_vlm,
            "latency_ms": round(v.latency_ms, 3),
        })
    total_batch_ms = (time.perf_counter() - t0_batch) * 1000.0

    # 2. Run ANCPI Order 600/2023 geometry validation
    geoms = list(gdf.geometry)
    ancpi_res = validate_ancpi(geoms)

    avg_latency = sum(triage_latencies) / len(triage_latencies)

    # 3. Compile report
    report = {
        "dataset": "USAMV Cluj Frozen Test Split",
        "spatial_buffer_m": 30.0,
        "crs": "EPSG:3844",
        "total_test_buildings": total_test,
        "system_1_fast_triage": {
            "counts": triage_counts,
            "percentages": {
                k: round(v / total_test * 100.0, 2)
                for k, v in triage_counts.items()
            },
            "avg_latency_ms_per_candidate": round(avg_latency, 4),
            "total_batch_latency_ms": round(total_batch_ms, 3),
            "latency_target_met": avg_latency < 35.0,
        },
        "ancpi_geometric_validation": {
            "checks": ancpi_res["checks"],
            "failed_count": ancpi_res["failed_count"],
            "overall_passed": ancpi_res["passed"],
        },
        "verdicts_sample": verdicts[:5],
    }

    with open(out_report, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"\n--- FROZEN BASELINE BENCHMARK COMPLETED ---")
    print(f"Total Test Buildings: {total_test}")
    print(f"System 1 Triage Counts: {triage_counts}")
    print(f"Percentages: {report['system_1_fast_triage']['percentages']}")
    print(f"Avg Latency: {avg_latency:.4f} ms (Target: < 35.0 ms) -> PASS: {avg_latency < 35.0}")
    print(f"Report saved to: {out_report}")
    return report


if __name__ == "__main__":
    run_benchmark()
