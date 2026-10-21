# -*- coding: utf-8 -*-
"""
tools/audit_cluj_pug_topology.py - Order 904/2023 Article 9 Topology Audit for Cluj ZMC

Runs automated topological compliance checks on Cluj_Regional_PUG_Master.gpkg:
1. Article 8: Simple valid geometries (ISO 19125-1).
2. Article 9(1): Functional zoning without internal overlaps.
3. Article 9(1): Functional zoning without gaps against ZMC administrative boundary.
4. Produces authoritative QA audit report.
"""

import sys
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

import geopandas as gpd
from shapely.ops import unary_union
from stratum_ro.pug_topology import Order904TopologyAuditor


def main():
    print("===================================================================")
    print("  STRATUMRO: PUG TOPOLOGY AUDIT (Ordinul MDLPA 904/2023 Art. 9)")
    print("  Dataset: Cluj Regional PUG Master (ZMC)")
    print("===================================================================")

    gpkg_path = ROOT / "workspace" / "reviews" / "cluj_regional_pug" / "Cluj_Regional_PUG_Master.gpkg"
    out_report = ROOT / "workspace" / "reviews" / "cluj_regional_pug" / "qa" / "order_904_qa_report.json"

    assert gpkg_path.exists(), f"GeoPackage not found: {gpkg_path}"

    auditor = Order904TopologyAuditor(tolerance_m2=0.01, crs="EPSG:3844")

    # 1. Load ZFExistenta
    print("\n[1/3] Auditing ZFExistenta simple geometries & overlaps...")
    zf = gpd.read_file(str(gpkg_path), layer="ZFExistenta")
    res_geom = auditor.check_simple_geometries(zf)
    print(f"  -> Simple Geometries (Art. 8): {'PASS' if res_geom.passed else 'FAIL'} ({res_geom.details})")

    res_overlap = auditor.check_functional_zoning_no_overlaps(zf)
    print(f"  -> No Overlaps (Art. 9.1): {'PASS' if res_overlap.passed else 'FAIL'} ({res_overlap.details})")

    # 2. Load Limita_ZMC_UAT
    print("\n[2/3] Auditing Boundary Coverage (Art. 9.1: No Gaps)...")
    uats = gpd.read_file(str(gpkg_path), layer="Limita_ZMC_UAT")
    zmc_boundary = unary_union(list(uats.geometry))

    res_coverage = auditor.check_boundary_coverage(zf, zmc_boundary)
    print(f"  -> Boundary Coverage (Art. 9.1): {'PASS' if res_coverage.passed else 'FAIL'} ({res_coverage.details})")

    # 3. Compile QA Report
    overall_passed = res_geom.passed and res_overlap.passed and res_coverage.passed
    report = {
        "dataset": "Cluj_Regional_PUG_Master.gpkg",
        "regiune": "Zona Metropolitană Cluj (ZMC)",
        "crs": "EPSG:3844",
        "normativ": "Ordinul MDLPA nr. 904/2023 & Legea nr. 169/2026 (CATUC)",
        "statut_document": "PLAN_SITUATIE_EXISTENTA_DOCUMENT_DE_LUCRU",
        "overall_passed": overall_passed,
        "checks": [
            {
                "article": "Art. 8",
                "name": res_geom.check_name,
                "passed": res_geom.passed,
                "defects": res_geom.defect_count,
                "details": res_geom.details,
            },
            {
                "article": "Art. 9(1)",
                "name": res_overlap.check_name,
                "passed": res_overlap.passed,
                "defects": res_overlap.defect_count,
                "overlap_area_m2": res_overlap.defect_area_m2,
                "details": res_overlap.details,
            },
            {
                "article": "Art. 9(1)",
                "name": res_coverage.check_name,
                "passed": res_coverage.passed,
                "defects": res_coverage.defect_count,
                "gap_area_m2": res_coverage.defect_area_m2,
                "details": res_coverage.details,
            },
        ],
    }

    with open(out_report, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"\n[3/3] QA Audit Completed: Overall Passed = {overall_passed}")
    print(f"Report saved to: {out_report}")
    print("===================================================================")
    return report


if __name__ == "__main__":
    main()
