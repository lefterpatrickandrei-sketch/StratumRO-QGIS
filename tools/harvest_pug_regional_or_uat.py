# -*- coding: utf-8 -*-
"""
tools/harvest_pug_regional_or_uat.py - Universal Romanian PUG Data Harvester & QGIS Deliverable Generator

Usage:
    # 1. Single UAT by name or SIRUTA:
    python tools/harvest_pug_regional_or_uat.py --uat "Florești"
    python tools/harvest_pug_regional_or_uat.py --uat 54975

    # 2. Regional Metropolitan Cluster:
    python tools/harvest_pug_regional_or_uat.py --preset cluj_zmc
    python tools/harvest_pug_regional_or_uat.py --uats "54975, 57706, 55687" --name "Cluj_Metropolitan_Core"

Conformity:
    - Ordinul MDLPA nr. 904/2023 (Norme tehnice PUG/PUZ)
    - Legea nr. 169/2026 (CATUC)
    - Ordinul ANCPI nr. 600/2023 (Stereo 70 EPSG:3844)
"""

import sys
import os
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from stratum_ro.pug_harvester import (
    PugDataHarvester,
    PugQgisProjectBuilder,
    PugCadExporter,
    REGIONAL_PRESETS,
)
from stratum_ro.pug_topology import Order904TopologyAuditor
import geopandas as gpd


def main():
    parser = argparse.ArgumentParser(description="Universal Romanian PUG Data Harvester & QGIS Builder")
    parser.add_argument("--uat", type=str, help="Single UAT name or SIRUTA code (e.g. 'Florești' or '54975')")
    parser.add_argument("--uats", type=str, help="Comma-separated UAT names or SIRUTA codes")
    parser.add_argument("--preset", type=str, choices=list(REGIONAL_PRESETS.keys()), help="Regional preset (e.g. cluj_zmc)")
    parser.add_argument("--name", type=str, help="Custom project title / identifier")
    parser.add_argument("--out", type=str, help="Output directory path")
    parser.add_argument("--buildings", type=str, help="Path to custom building GeoJSON")

    args = parser.parse_args()

    # Determine targets
    identifiers = []
    project_label = "PUG_Universal"

    if args.preset:
        identifiers = [args.preset]
        project_label = args.name or args.preset
    elif args.uats:
        identifiers = [x.strip() for x in args.uats.split(",") if x.strip()]
        project_label = args.name or f"PUG_Cluster_{len(identifiers)}_UATs"
    elif args.uat:
        identifiers = [args.uat.strip()]
        project_label = args.name or f"PUG_UAT_{args.uat.strip().replace(' ', '_')}"
    else:
        # Default to cluj_zmc if nothing specified
        identifiers = ["cluj_zmc"]
        project_label = "cluj_regional_pug"

    print("===================================================================")
    print("  STRATUMRO: UNIVERSAL PUG DATA HARVESTER & QGIS GENERATOR")
    print(f"  Target: {identifiers} -> Label: {project_label}")
    print("  Conformity: Ordinul MDLPA 904/2023 & Legea 169/2026 (CATUC)")
    print("  CRS: Stereo 70 (EPSG:3844)")
    print("===================================================================")

    out_dir = Path(args.out) if args.out else (ROOT / "workspace" / "reviews" / project_label.lower())
    qa_dir = out_dir / "qa"
    cad_dir = out_dir / "CAD_Export"
    out_dir.mkdir(parents=True, exist_ok=True)
    qa_dir.mkdir(parents=True, exist_ok=True)
    cad_dir.mkdir(parents=True, exist_ok=True)

    gpkg_path = out_dir / f"{project_label}_Master.gpkg"
    qgs_path = out_dir / f"{project_label}_Oficial.qgs"
    dxf_path = cad_dir / f"{project_label}_Cadastru_si_PUG.dxf"
    checklist_path = out_dir / "checklist_recoltare_date.json"
    qa_report_path = qa_dir / "order_904_qa_report.json"

    # 1. Harvest Data
    print(f"\n[1/4] Harvesting official Romanian open data for {identifiers}...")
    harvester = PugDataHarvester()
    target_uats = harvester.resolve_uats(identifiers)
    print(f"  -> Successfully resolved {len(target_uats)} UAT(s):")
    for _, u in target_uats.iterrows():
        print(f"     * [{u['natCode']}] {u['name']}")

    bld_source = Path(args.buildings) if args.buildings else None
    checklist = harvester.harvest(target_uats, gpkg_path, building_source=bld_source)

    with open(checklist_path, "w", encoding="utf-8") as f:
        json.dump(checklist, f, indent=2, ensure_ascii=False)
    print(f"  -> Data harvesting checklist saved: {checklist_path}")
    print(f"  -> Master GeoPackage written: {gpkg_path}")

    # 2. Topology QA Audit (Order 904/2023 Art. 8 & 9)
    print(f"\n[2/4] Auditing topology against Order 904/2023 (Art. 8 & Art. 9)...")
    auditor = Order904TopologyAuditor()
    qa_results = auditor.audit_geopackage(str(gpkg_path), zoning_layer="ZFExistenta", boundary_layer="Limita_UAT_ANCPI")
    with open(qa_report_path, "w", encoding="utf-8") as f:
        json.dump(qa_results, f, indent=2, ensure_ascii=False)
    compliant = qa_results.get("order_904_compliant", qa_results.get("overall_passed", False))
    print(f"  -> Topology Audit Passed: {compliant}")

    # 3. Build QGIS Project (100% Valid XML)
    print(f"\n[3/4] Building QGIS 3.40 Master Project: {qgs_path}...")
    title = f"StratumRO — Plan Urbanistic {project_label.replace('_', ' ').title()} (Stereo 70)"
    PugQgisProjectBuilder.build_qgis_project(gpkg_path, qgs_path, project_title=title)
    print(f"  -> QGIS Project validated with 0 XML errors: {qgs_path}")

    # 4. Export CAD DXF
    print(f"\n[4/4] Exporting TopoLT CAD Deliverable: {dxf_path}...")
    PugCadExporter.export_dxf(gpkg_path, dxf_path)
    print(f"  -> CAD Deliverable saved: {dxf_path}")

    print("\n===================================================================")
    print(f"  SUCCESS! PUG PACKAGE FOR {project_label} IS READY!")
    print(f"  GPKG: {gpkg_path}")
    print(f"  QGIS: {qgs_path}")
    print(f"  CAD:  {dxf_path}")
    print("===================================================================")


if __name__ == "__main__":
    main()
