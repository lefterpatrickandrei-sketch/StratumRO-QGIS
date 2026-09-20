# -*- coding: utf-8 -*-
"""
CLI runner for StratumRO Closed-Loop Development Cycle.
Usage:
    python tools/run_closed_loop.py --milestone "Geospatial Platform & API" --desc "FastAPI and Web Cockpit integration"
"""

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from stratum_ro.ai.closed_loop import ClosedLoopOrchestrator


def main():
    parser = argparse.ArgumentParser(description="StratumRO Closed-Loop Development Milestone Runner")
    parser.add_argument("--milestone", type=str, default="Milestone Check", help="Name of the development milestone")
    parser.add_argument("--desc", type=str, default="Closed-loop verification of platform changes", help="Description")
    parser.add_argument("--files", nargs="*", default=[], help="List of changed files")
    parser.add_argument("--skip-kilo", action="store_true", help="Skip Kilo adversarial review step")
    args = parser.parse_args()

    orchestrator = ClosedLoopOrchestrator()
    report = orchestrator.run_full_cycle(
        milestone_name=args.milestone,
        description=args.desc,
        changed_files=args.files,
        skip_kilo=args.skip_kilo,
    )

    print("\n" + "=" * 70)
    print(f"  STRATUMRO CLOSED-LOOP REPORT: {report.milestone_name}")
    print("=" * 70)
    print(f"Timestamp:       {report.timestamp}")
    print(f"Overall Status:  {report.overall_status}")
    print(f"Tests:           {report.tests.passed} passed, {report.tests.skipped} skipped, {report.tests.failed} failed ({report.tests.duration_sec}s)")
    print(f"QGIS Socket:     {'ONLINE (' + str(report.qgis.layers_count) + ' layers)' if report.qgis.connected else 'OFFLINE'}")
    print(f"NVIDIA NIM:      {report.nim.status} ({report.nim.model})")
    print(f"Kilo Reviewer:   {report.kilo.verdict} ({report.kilo.reviewer})")

    if report.kilo.findings:
        print("\nKilo Top Findings:")
        for f in report.kilo.findings:
            print(f"  {f}")

    # Save artifact
    out_dir = PROJECT_ROOT / "workspace" / "output"
    out_dir.mkdir(parents=True, exist_ok=True)
    report_file = out_dir / "latest_closed_loop_report.json"
    
    report_data = {
        "milestone": report.milestone_name,
        "timestamp": report.timestamp,
        "overall_status": report.overall_status,
        "summary": report.summary,
        "tests": {
            "total": report.tests.total_discovered,
            "passed": report.tests.passed,
            "skipped": report.tests.skipped,
            "failed": report.tests.failed,
            "duration_sec": report.tests.duration_sec,
        },
        "qgis": {
            "connected": report.qgis.connected,
            "layers_count": report.qgis.layers_count,
            "layer_names": report.qgis.layer_names,
        },
        "nim": {
            "status": report.nim.status,
            "model": report.nim.model,
            "duration_sec": report.nim.duration_sec,
        },
        "kilo": {
            "verdict": report.kilo.verdict,
            "status": report.kilo.status,
            "duration_sec": report.kilo.duration_sec,
            "findings": report.kilo.findings,
            "full_review": report.kilo.full_review,
        },
    }
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2, ensure_ascii=False)

    print(f"\n[+] Detailed report written to: {report_file}")
    if report.kilo.full_review:
        kilo_md = out_dir / "latest_kilo_review.md"
        with open(kilo_md, "w", encoding="utf-8") as f:
            f.write(f"# KILO ADVERSARIAL MILESTONE REVIEW: {report.milestone_name}\n\n" + report.kilo.full_review)
        print(f"[+] Kilo markdown review written to: {kilo_md}")

    return 0 if report.overall_status in ("PASS", "PASS_WITH_WARNINGS") else 1


if __name__ == "__main__":
    sys.exit(main())
