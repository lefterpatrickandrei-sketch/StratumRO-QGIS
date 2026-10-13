# -*- coding: utf-8 -*-
"""
Integrate StratumRO Lot 3 Revision (T11-T20) into the active QGIS project via QGIS MCP.
- Retains initial Lot 3 as unchecked historical group LOT3_ISTORIC_INITIAL_NEACCEPTAT.
- Adds new active group LOT3_REVIZIE_T11_T20 with:
  * LOT3_REV_CORPURI_EXTRASE (cyan neon #00e5ff)
  * LOT3_REV_CAZURI_NERECUPERATE (red marker #ff1744)
  * LOT3_REV_FERESTRE_SELECTIE (dashed yellow #ffd700)
  * LOT3_REV_MASCA_BRUTA (dashed purple #9c27b0, unchecked)
- Validates layer counts and feature readbacks.
- Saves project and synchronizes release copy.
- Captures live canvas screenshots.
"""
from pathlib import Path
import sys
import json
import base64
import shutil

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools.qgis_mcp_query import send_qgis_mcp
from stratum_ro.evaluation_preflight import checked_qgis_result

OUT_DIR = ROOT / 'workspace/reviews/lot3_revision_20261013'
SNIPPET_FILE = ROOT / 'tools/qgis_integrate_lot3_revision_snippet.py'
EXPECTED_PROJECT = ROOT / 'workspace/reviews/body_recovery_20261013/inspectie_corectii.qgs'
RELEASE_PROJECT = ROOT / 'workspace/reviews/retry_six_release_20261013/inspectie_completa_8_orto_loturi.qgs'


def capture_view(name, xmin, ymin, xmax, ymax):
    script = f"""
from qgis.core import QgsRectangle
from qgis.utils import iface
if iface and iface.mapCanvas():
    iface.mapCanvas().setExtent(QgsRectangle({xmin}, {ymin}, {xmax}, {ymax}))
    iface.mapCanvas().refresh()
    print('VIEW_READY')
"""
    res = send_qgis_mcp("execute_code", {"code": script, "timeout": 15.0})
    checked_qgis_result(res, 'VIEW_READY')

    snap = send_qgis_mcp("get_canvas_screenshot")
    if snap.get("status") == "success" and "base64_data" in snap.get("result", {}):
        data = snap["result"]["base64_data"]
        raw = base64.b64decode(data)
        out_p = OUT_DIR / name
        out_p.write_bytes(raw)
        print(f"Captured live screenshot: {out_p.name} ({len(raw)} bytes)")
        return out_p
    else:
        print(f"Failed to capture {name}: {snap}")
        return None


def main():
    print("1. Sending Lot 3 revision integration script to QGIS MCP...")
    pyqgis_code = SNIPPET_FILE.read_text(encoding='utf-8')
    res = send_qgis_mcp("execute_code", {"code": pyqgis_code, "timeout": 30.0})
    checked_qgis_result(res, 'PYQGIS_SUCCESS')
    stdout = res.get("result", {}).get("stdout", "")
    print("STDOUT:", stdout)

    print("2. Syncing release project copy...")
    shutil.copyfile(EXPECTED_PROJECT, RELEASE_PROJECT)
    print(f"Synchronized {RELEASE_PROJECT.name} ({RELEASE_PROJECT.stat().st_size} bytes)")

    print("3. Capturing overview canvas screenshot...")
    capture_view("qgis_canvas_lot3_revision.png", 390550.0, 585050.0, 391380.0, 585680.0)

    print("4. Capturing closeup on T11/T12...")
    capture_view("qgis_canvas_lot3_t11_t12_closeup.png", 391210.0, 585560.0, 391330.0, 585640.0)

    print("5. Capturing closeup on T17 (L/T articulated wing)...")
    capture_view("qgis_canvas_lot3_t17_closeup.png", 390750.0, 585440.0, 390860.0, 585540.0)

    print("\nIntegration into QGIS Desktop completed successfully!")


if __name__ == '__main__':
    main()
