# -*- coding: utf-8 -*-
"""
tools/build_cluj_regional_qgis_project.py - Cluj Regional PUG QGIS Master Project Builder

Builds the complete production QGIS project file (Cluj_Regional_PUG_Oficial.qgs)
and CAD DXF deliverable in Stereo 70 (EPSG:3844) with professional urban planning
symbology, labeled buildings (CL/CA/CAS), transparent magenta parcel boundaries,
and high-resolution orthophoto backdrop conforming to Order MDLPA nr. 904/2023.
"""

import sys
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from stratum_ro.pug_harvester import PugQgisProjectBuilder, PugCadExporter


def build_qgis_project():
    out_dir = ROOT / "workspace" / "reviews" / "cluj_regional_pug"
    gpkg_path = out_dir / "Cluj_Regional_PUG_Master.gpkg"
    qgs_path = out_dir / "Cluj_Regional_PUG_Oficial.qgs"
    cad_path = out_dir / "CAD_Export" / "Cluj_Regional_ZMC_Cadastru_si_PUG.dxf"

    assert gpkg_path.exists(), f"Master GPKG not found: {gpkg_path}"

    print(f"[1/2] Building Master QGIS Project: {qgs_path}")
    PugQgisProjectBuilder.build_qgis_project(
        gpkg_path,
        qgs_path,
        project_title="StratumRO — Plan Urbanistic Cluj Regional (ZMC) Oficial",
    )
    print(f"  -> QGIS Project saved and validated: {qgs_path}")

    print(f"\n[2/2] Exporting CAD TopoLT Deliverable: {cad_path}")
    PugCadExporter.export_dxf(gpkg_path, cad_path)
    print(f"  -> CAD DXF saved: {cad_path}")

    print("\n===================================================================")
    print("  CLUJ REGIONAL PUG PRODUCTION PACKAGE ASSEMBLED SUCCESSFULLY!")
    print("===================================================================")


if __name__ == "__main__":
    build_qgis_project()
