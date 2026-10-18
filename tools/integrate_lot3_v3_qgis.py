# -*- coding: utf-8 -*-
"""
Integrate StratumRO Lot 3 v3 (T11-T20) into the active QGIS project via QGIS MCP.
- Retains initial Lot 3 and 2026-10-13 revision as unchecked historical groups.
- Adds new active group LOT3_REVIZIE_V3_T11_T20 with:
  * LOT3_V3_CORPURI_EXTRASE (cyan neon #00e5ff) - 18 extracted bodies
  * LOT3_V3_CAZURI_NERECUPERATE (red marker #ff1744) - 1 unrecovered case (T19)
  * LOT3_V3_FERESTRE_SELECTIE (dashed yellow #ffd700) - 10 selection windows
  * LOT3_V3_MASCA_BRUTA (dotted purple #9c27b0, unchecked) - 27 raw mask attempts
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

OUT_DIR = ROOT / 'workspace/reviews/lot3_revision_v3_20261016'
EXPECTED_PROJECT = ROOT / 'workspace/reviews/body_recovery_20261013/inspectie_corectii.qgs'
RELEASE_PROJECT = ROOT / 'workspace/reviews/retry_six_release_20261013/inspectie_completa_8_orto_loturi.qgs'
GPKG_BASE = str((OUT_DIR / 'results/lot3_results.gpkg').resolve()).replace('\\', '/')
EXPECTED_PROJECT_STR = str(EXPECTED_PROJECT.resolve()).replace('\\', '/')

PYQGIS_SNIPPET = f"""# -*- coding: utf-8 -*-
import traceback

try:
    from qgis.core import (
        QgsProject, QgsVectorLayer, QgsFillSymbol, QgsMarkerSymbol,
        QgsSingleSymbolRenderer, QgsRectangle, QgsPalLayerSettings,
        QgsVectorLayerSimpleLabeling, QgsTextFormat, QgsTextBufferSettings
    )
    from qgis.utils import iface
    from qgis.PyQt.QtGui import QColor, QFont

    p = QgsProject.instance()
    root = p.layerTreeRoot()
    expected_project = '{EXPECTED_PROJECT_STR}'
    if p.fileName().replace('\\\\', '/').lower() != expected_project.lower():
        raise RuntimeError(f'Wrong shared project: {{p.fileName()}}; expected {{expected_project}}')
    if p.isDirty() or any(getattr(l, 'isEditable', lambda: False)() for l in p.mapLayers().values()):
        raise RuntimeError('Unsaved project or editable layers; reconcile user changes first')

    # 1. Manage historical Lot 3 groups
    for old_name in ['LOT3_T11_T20_IN_VERIFICARE', 'LOT3_ISTORIC_INITIAL_NEACCEPTAT']:
        grp = root.findGroup(old_name)
        if grp:
            grp.setName('LOT3_ISTORIC_INITIAL_NEACCEPTAT')
            grp.setItemVisibilityChecked(False)
            for ch in grp.children():
                ch.setItemVisibilityChecked(False)

    rev_old_grp = root.findGroup('LOT3_REVIZIE_T11_T20')
    if rev_old_grp:
        rev_old_grp.setName('LOT3_REVIZIE_20261013_ISTORIC')
        rev_old_grp.setItemVisibilityChecked(False)
        for ch in rev_old_grp.children():
            ch.setItemVisibilityChecked(False)

    # Remove existing v3 group if rerunning
    v3_grp_name = 'LOT3_REVIZIE_V3_T11_T20'
    existing_v3 = root.findGroup(v3_grp_name)
    if existing_v3:
        for child in list(existing_v3.children()):
            if hasattr(child, 'layerId'):
                p.removeMapLayer(child.layerId())
        root.removeChildNode(existing_v3)

    for l in list(p.mapLayers().values()):
        if l.name().startswith('LOT3_V3_'):
            p.removeMapLayer(l.id())

    # Create new v3 group at top
    v3_grp = root.insertGroup(0, v3_grp_name)
    v3_grp.setExpanded(True)
    v3_grp.setItemVisibilityChecked(True)

    gpkg_base = '{GPKG_BASE}'

    def make_label_settings(field_name, text_color, buffer_color, size_pt=9):
        settings = QgsPalLayerSettings()
        settings.fieldName = field_name
        settings.isExpression = False
        settings.enabled = True
        
        tformat = QgsTextFormat()
        font = QFont('Segoe UI', size_pt, QFont.Bold)
        tformat.setFont(font)
        tformat.setSize(size_pt)
        tformat.setColor(QColor(text_color))
        
        buf = QgsTextBufferSettings()
        buf.setEnabled(True)
        buf.setSize(1.0)
        buf.setColor(QColor(buffer_color))
        tformat.setBuffer(buf)
        settings.setFormat(tformat)
        return settings

    # Layer 1: LOT3_V3_CORPURI_EXTRASE
    ds_corp = f"{{gpkg_base}}|layername=CORPURI_EXTRASE_LOT3"
    lyr_corp = QgsVectorLayer(ds_corp, 'LOT3_V3_CORPURI_EXTRASE', 'ogr')
    if lyr_corp.isValid():
        sym_corp = QgsFillSymbol.createSimple({{
            'color': '0,0,0,0',
            'outline_color': '#00e5ff',
            'outline_width': '0.7',
            'outline_style': 'solid'
        }})
        lyr_corp.setRenderer(QgsSingleSymbolRenderer(sym_corp))
        lbl_corp = make_label_settings('id', '#00b0ff', '#ffffff', 9)
        lyr_corp.setLabeling(QgsVectorLayerSimpleLabeling(lbl_corp))
        lyr_corp.setLabelsEnabled(True)
        p.addMapLayer(lyr_corp, False)
        node_corp = v3_grp.addLayer(lyr_corp)
        node_corp.setItemVisibilityChecked(True)
        print(f"Added LOT3_V3_CORPURI_EXTRASE: {{lyr_corp.featureCount()}} features")
    else:
        raise RuntimeError('Failed to load CORPURI_EXTRASE_LOT3')

    # Layer 2: LOT3_V3_CAZURI_NERECUPERATE
    ds_nerec = f"{{gpkg_base}}|layername=CAZURI_NERECUPERATE_LOT3"
    lyr_nerec = QgsVectorLayer(ds_nerec, 'LOT3_V3_CAZURI_NERECUPERATE', 'ogr')
    if lyr_nerec.isValid():
        sym_nerec = QgsMarkerSymbol.createSimple({{
            'name': 'cross',
            'size': '4.0',
            'color': '#ff1744',
            'outline_color': '#ff1744',
            'outline_width': '0.8'
        }})
        lyr_nerec.setRenderer(QgsSingleSymbolRenderer(sym_nerec))
        lbl_nerec = make_label_settings('test_id', '#d50000', '#ffffff', 9)
        lyr_nerec.setLabeling(QgsVectorLayerSimpleLabeling(lbl_nerec))
        lyr_nerec.setLabelsEnabled(True)
        p.addMapLayer(lyr_nerec, False)
        node_nerec = v3_grp.addLayer(lyr_nerec)
        node_nerec.setItemVisibilityChecked(True)
        print(f"Added LOT3_V3_CAZURI_NERECUPERATE: {{lyr_nerec.featureCount()}} features")
    else:
        raise RuntimeError('Failed to load CAZURI_NERECUPERATE_LOT3')

    # Layer 3: LOT3_V3_FERESTRE_SELECTIE
    ds_sel = f"{{gpkg_base}}|layername=FERESTRE_SELECTIE_LOT3"
    lyr_sel = QgsVectorLayer(ds_sel, 'LOT3_V3_FERESTRE_SELECTIE', 'ogr')
    if lyr_sel.isValid():
        sym_sel = QgsFillSymbol.createSimple({{
            'color': '0,0,0,0',
            'outline_color': '#ffd700',
            'outline_width': '0.4',
            'outline_style': 'dash'
        }})
        lyr_sel.setRenderer(QgsSingleSymbolRenderer(sym_sel))
        lbl_sel = make_label_settings('test_id', '#e65100', '#ffffff', 8)
        lyr_sel.setLabeling(QgsVectorLayerSimpleLabeling(lbl_sel))
        lyr_sel.setLabelsEnabled(True)
        p.addMapLayer(lyr_sel, False)
        node_sel = v3_grp.addLayer(lyr_sel)
        node_sel.setItemVisibilityChecked(True)
        print(f"Added LOT3_V3_FERESTRE_SELECTIE: {{lyr_sel.featureCount()}} features")
    else:
        raise RuntimeError('Failed to load FERESTRE_SELECTIE_LOT3')

    # Layer 4: LOT3_V3_MASCA_BRUTA (unchecked)
    ds_raw = f"{{gpkg_base}}|layername=MASCA_BRUTA_LOT3"
    lyr_raw = QgsVectorLayer(ds_raw, 'LOT3_V3_MASCA_BRUTA', 'ogr')
    if lyr_raw.isValid():
        sym_raw = QgsFillSymbol.createSimple({{
            'color': '0,0,0,0',
            'outline_color': '#9c27b0',
            'outline_width': '0.3',
            'outline_style': 'dot'
        }})
        lyr_raw.setRenderer(QgsSingleSymbolRenderer(sym_raw))
        p.addMapLayer(lyr_raw, False)
        node_raw = v3_grp.addLayer(lyr_raw)
        node_raw.setItemVisibilityChecked(False)
        print(f"Added LOT3_V3_MASCA_BRUTA (unchecked): {{lyr_raw.featureCount()}} features")

    # Set canvas extent to encompass all Lot 3 v3 cases
    if iface and iface.mapCanvas():
        ext = QgsRectangle(390550.0, 585050.0, 391380.0, 585680.0)
        iface.mapCanvas().setExtent(ext)
        iface.mapCanvas().refresh()

    if not lyr_corp.isValid() or lyr_corp.featureCount() != 18:
        raise RuntimeError(f'Unexpected extracted bodies count: {{lyr_corp.featureCount()}}; expected 18')
    if not lyr_nerec.isValid() or lyr_nerec.featureCount() != 1:
        raise RuntimeError(f'Unexpected unrecovered count: {{lyr_nerec.featureCount()}}; expected 1')
    if not lyr_sel.isValid() or lyr_sel.featureCount() != 10:
        raise RuntimeError(f'Unexpected selection window count: {{lyr_sel.featureCount()}}; expected 10')

    if not p.write():
        raise RuntimeError('Project save failed')
    print('PYQGIS_SUCCESS')
except Exception as e:
    print('PYQGIS_EXCEPTION:', traceback.format_exc())
"""


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
    print("1. Sending Lot 3 v3 integration script to QGIS MCP...")
    res = send_qgis_mcp("execute_code", {"code": PYQGIS_SNIPPET, "timeout": 30.0})
    checked_qgis_result(res, 'PYQGIS_SUCCESS')
    stdout = res.get("result", {}).get("stdout", "")
    print("STDOUT:", stdout)

    print("2. Syncing release project copy...")
    shutil.copyfile(EXPECTED_PROJECT, RELEASE_PROJECT)
    print(f"Synchronized {RELEASE_PROJECT.name} ({RELEASE_PROJECT.stat().st_size} bytes)")

    print("3. Capturing overview canvas screenshot...")
    capture_view("qgis_canvas_lot3_v3.png", 390550.0, 585050.0, 391380.0, 585680.0)

    print("4. Capturing closeup on T11/T12...")
    capture_view("qgis_canvas_lot3_t11_t12_closeup.png", 391210.0, 585560.0, 391330.0, 585640.0)

    print("5. Capturing closeup on T17 (L/T articulated wing)...")
    capture_view("qgis_canvas_lot3_t17_closeup.png", 390750.0, 585440.0, 390860.0, 585540.0)

    print("6. Capturing closeup on T15 / T20...")
    capture_view("qgis_canvas_lot3_t15_t20_closeup.png", 390920.0, 585190.0, 391050.0, 585295.0)

    print("\nIntegration into QGIS Desktop completed successfully!")


if __name__ == '__main__':
    main()
