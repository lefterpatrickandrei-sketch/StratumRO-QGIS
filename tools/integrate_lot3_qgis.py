# -*- coding: utf-8 -*-
"""
Integrate StratumRO Lot 3 (T11-T20) into the active QGIS project via QGIS MCP.
Creates group LOT3_T11_T20_IN_VERIFICARE with:
- LOT3_CORPURI_EXTRASE (cyan neon #00e5ff)
- LOT3_CAZURI_NERECUPERATE (red marker #ff1744)
- LOT3_FERESTRE_SELECTIE (dashed yellow #ffd700)
Saves project and captures canvas screenshots.
"""
import sys
import json
import base64
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools.qgis_mcp_query import send_qgis_mcp

PYQGIS_SCRIPT = r"""
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

    grp_name = 'LOT3_T11_T20_IN_VERIFICARE'
    
    # 1. Remove existing group and layers if present
    existing_grp = root.findGroup(grp_name)
    if existing_grp:
        for child in list(existing_grp.children()):
            if hasattr(child, 'layerId'):
                lyr_id = child.layerId()
                p.removeMapLayer(lyr_id)
        root.removeChildNode(existing_grp)
    for l in list(p.mapLayers().values()):
        if l.name().startswith('LOT3_'):
            p.removeMapLayer(l.id())

    # Create new group at top
    lot3_grp = root.insertGroup(0, grp_name)
    lot3_grp.setExpanded(True)
    lot3_grp.setItemVisibilityChecked(True)

    gpkg_base = 'C:/Users/lefpa/Downloads/QGIS-AI/workspace/reviews/lot3_20261013/lot3_results.gpkg'

    # Helper for label format
    def make_label_settings(expr_or_field, is_expr, text_color, buffer_color, size_pt=9):
        settings = QgsPalLayerSettings()
        settings.fieldName = expr_or_field
        settings.isExpression = is_expr
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

    # Layer 1: LOT3_CORPURI_EXTRASE
    ds_corp = f"{gpkg_base}|layername=CORPURI_EXTRASE_LOT3"
    lyr_corp = QgsVectorLayer(ds_corp, 'LOT3_CORPURI_EXTRASE', 'ogr')
    if lyr_corp.isValid():
        sym_corp = QgsFillSymbol.createSimple({
            'color': '0,0,0,0',
            'outline_color': '#00e5ff',
            'outline_width': '0.7',
            'outline_style': 'solid'
        })
        lyr_corp.setRenderer(QgsSingleSymbolRenderer(sym_corp))
        lbl_corp = make_label_settings('"id"', True, '#00b0ff', '#ffffff', 9)
        lyr_corp.setLabeling(QgsVectorLayerSimpleLabeling(lbl_corp))
        lyr_corp.setLabelsEnabled(True)
        p.addMapLayer(lyr_corp, False)
        node_corp = lot3_grp.addLayer(lyr_corp)
        node_corp.setItemVisibilityChecked(True)
        print("Added LOT3_CORPURI_EXTRASE")
    else:
        print("FAILED to load CORPURI_EXTRASE_LOT3")

    # Layer 2: LOT3_CAZURI_NERECUPERATE
    ds_nerec = f"{gpkg_base}|layername=CAZURI_NERECUPERATE_LOT3"
    lyr_nerec = QgsVectorLayer(ds_nerec, 'LOT3_CAZURI_NERECUPERATE', 'ogr')
    if lyr_nerec.isValid():
        sym_nerec = QgsMarkerSymbol.createSimple({
            'name': 'cross',
            'size': '4.0',
            'color': '#ff1744',
            'outline_color': '#ff1744',
            'outline_width': '0.8'
        })
        lyr_nerec.setRenderer(QgsSingleSymbolRenderer(sym_nerec))
        lbl_nerec = make_label_settings('"test_id" || \' (NERECUPERAT)\'', True, '#d50000', '#ffffff', 9)
        lyr_nerec.setLabeling(QgsVectorLayerSimpleLabeling(lbl_nerec))
        lyr_nerec.setLabelsEnabled(True)
        p.addMapLayer(lyr_nerec, False)
        node_nerec = lot3_grp.addLayer(lyr_nerec)
        node_nerec.setItemVisibilityChecked(True)
        print("Added LOT3_CAZURI_NERECUPERATE")
    else:
        print("FAILED to load CAZURI_NERECUPERATE_LOT3")

    # Layer 3: LOT3_FERESTRE_SELECTIE
    ds_sel = f"{gpkg_base}|layername=FERESTRE_SELECTIE_LOT3"
    lyr_sel = QgsVectorLayer(ds_sel, 'LOT3_FERESTRE_SELECTIE', 'ogr')
    if lyr_sel.isValid():
        sym_sel = QgsFillSymbol.createSimple({
            'color': '0,0,0,0',
            'outline_color': '#ffd700',
            'outline_width': '0.4',
            'outline_style': 'dash'
        })
        lyr_sel.setRenderer(QgsSingleSymbolRenderer(sym_sel))
        lbl_sel = make_label_settings('"test_id"', False, '#e65100', '#ffffff', 8)
        lyr_sel.setLabeling(QgsVectorLayerSimpleLabeling(lbl_sel))
        lyr_sel.setLabelsEnabled(True)
        p.addMapLayer(lyr_sel, False)
        node_sel = lot3_grp.addLayer(lyr_sel)
        node_sel.setItemVisibilityChecked(True)
        print("Added LOT3_FERESTRE_SELECTIE")
    else:
        print("FAILED to load FERESTRE_SELECTIE_LOT3")

    # Set canvas extent to encompass all Lot 3 cases
    if iface and iface.mapCanvas():
        ext = QgsRectangle(390550.0, 585050.0, 391380.0, 585680.0)
        iface.mapCanvas().setExtent(ext)
        iface.mapCanvas().refresh()

    p.write()
    print("PYQGIS_SUCCESS: Integrated LOT3 group, styled layers, zoomed canvas, saved project.")
except Exception as e:
    print("PYQGIS_EXCEPTION:", traceback.format_exc())
"""

def main():
    print("1. Sending Lot 3 integration script to QGIS MCP...")
    res = send_qgis_mcp("execute_code", {"code": PYQGIS_SCRIPT, "timeout": 30.0})
    stdout = res.get("result", {}).get("stdout", "")
    print("STDOUT:", stdout)

    print("2. Calling save_project...")
    save_res = send_qgis_mcp("save_project")
    print("Save result:", save_res)

    print("3. Capturing overview canvas screenshot...")
    img_res = send_qgis_mcp("get_canvas_screenshot")
    out_img = ROOT / "workspace/reviews/lot3_20261013/qgis_canvas_lot3.png"
    if img_res.get("status") == "success":
        b64 = img_res.get("result", {}).get("base64_data")
        if b64:
            with open(out_img, "wb") as f:
                f.write(base64.b64decode(b64))
            print(f"Canvas overview screenshot saved to: {out_img}")
    else:
        print("Failed to capture overview screenshot:", img_res)

    # 4. Zoom to T12 and capture closeup
    zoom_t12_script = r"""
try:
    from qgis.core import QgsRectangle
    from qgis.utils import iface
    if iface and iface.mapCanvas():
        ext = QgsRectangle(391240.0, 585570.0, 391320.0, 585640.0)
        iface.mapCanvas().setExtent(ext)
        iface.mapCanvas().refresh()
    print("ZOOM_T12_SUCCESS")
except Exception as e:
    print("ZOOM_T12_ERR:", e)
"""
    send_qgis_mcp("execute_code", {"code": zoom_t12_script, "timeout": 15.0})
    img_t12_res = send_qgis_mcp("get_canvas_screenshot")
    out_t12_img = ROOT / "workspace/reviews/lot3_20261013/qgis_canvas_lot3_t12_closeup.png"
    if img_t12_res.get("status") == "success":
        b64 = img_t12_res.get("result", {}).get("base64_data")
        if b64:
            with open(out_t12_img, "wb") as f:
                f.write(base64.b64decode(b64))
            print(f"Canvas T12 closeup screenshot saved to: {out_t12_img}")

    # Reset canvas back to campus overview
    reset_script = r"""
try:
    from qgis.core import QgsRectangle
    from qgis.utils import iface
    if iface and iface.mapCanvas():
        ext = QgsRectangle(390550.0, 585050.0, 391380.0, 585680.0)
        iface.mapCanvas().setExtent(ext)
        iface.mapCanvas().refresh()
    print("RESET_CANVAS_SUCCESS")
except Exception as e:
    print("RESET_CANVAS_ERR:", e)
"""
    send_qgis_mcp("execute_code", {"code": reset_script, "timeout": 15.0})

    # Synchronize release project file
    active_qgs = ROOT / "workspace/reviews/body_recovery_20261013/inspectie_corectii.qgs"
    release_qgs = ROOT / "workspace/reviews/retry_six_release_20261013/inspectie_completa_8_orto_loturi.qgs"
    if active_qgs.exists() and release_qgs.exists():
        shutil.copy2(active_qgs, release_qgs)
        print(f"Synchronized {release_qgs} from active project.")

if __name__ == "__main__":
    main()
