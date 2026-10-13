# -*- coding: utf-8 -*-
import sys
import json
import base64
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools.qgis_mcp_query import send_qgis_mcp

PYQGIS_SCRIPT = r"""
import traceback
try:
    from qgis.core import (
        QgsProject, QgsVectorLayer, QgsFillSymbol, QgsSingleSymbolRenderer,
        QgsRectangle
    )
    from qgis.utils import iface
    from qgis.PyQt.QtGui import QColor

    p = QgsProject.instance()
    root = p.layerTreeRoot()

    # 1. Reload RECTIFICARI_T05_T06_T07_T10
    lyr_rect = [l for l in p.mapLayers().values() if l.name() == 'RECTIFICARI_T05_T06_T07_T10'][0]
    lyr_rect.dataProvider().forceReload()
    lyr_rect.reload()

    # 2. Update renderer categories and colors: T10:A1 becomes green (#39ff14) and labeled accepted
    renderer = lyr_rect.renderer()
    for i, cat in enumerate(renderer.categories()):
        if cat.value() == 'T10:A1':
            sym = cat.symbol().clone()
            sl = sym.symbolLayer(0)
            sl.setStrokeColor(QColor('#39ff14'))
            sl.setStrokeWidth(0.6)
            renderer.updateCategorySymbol(i, sym)
            renderer.updateCategoryLabel(i, 'T10:A1 (Acceptat proprietar)')
    lyr_rect.setRenderer(renderer.clone())

    # 3. Update labeling expression
    lbl = lyr_rect.labeling()
    if lbl:
        settings = lbl.settings()
        settings.fieldName = 'CASE WHEN "test_id" = \'T10\' THEN \'T10 - ACCEPTAT\' ELSE "test_id" END'
        settings.isExpression = True
        lbl.setSettings(settings)
        lyr_rect.setLabeling(lbl)

    # 4. Add historical layer (disabled/unchecked)
    hist_name = 'T10_ISTORIC_PARTIAL (Incomplet anterior)'
    for l in list(p.mapLayers().values()):
        if l.name() == hist_name:
            p.removeMapLayer(l.id())

    hist_ds = 'C:/Users/lefpa/Downloads/QGIS-AI/workspace/reviews/retry_six_release_20261013/retry_six.gpkg|layername=T10_ISTORIC_PARTIAL_RESPINS'
    hist_lyr = QgsVectorLayer(hist_ds, hist_name, 'ogr')
    if hist_lyr.isValid():
        sym_hist = QgsFillSymbol.createSimple({
            'color': '0,0,0,0',
            'outline_color': '255,140,0,255',
            'outline_width': '0.6',
            'outline_style': 'dash'
        })
        hist_lyr.setRenderer(QgsSingleSymbolRenderer(sym_hist))
        p.addMapLayer(hist_lyr, False)
        tree_lyr = root.insertLayer(0, hist_lyr)
        tree_lyr.setItemVisibilityChecked(False)

    lyr_rect.triggerRepaint()

    # 5. Zoom canvas to T10
    if iface and iface.mapCanvas():
        ext = QgsRectangle(390915.0, 585645.0, 390955.0, 585685.0)
        iface.mapCanvas().setExtent(ext)
        iface.mapCanvas().refresh()

    p.write()
    print("PYQGIS_SUCCESS: Updated T10 category, label, added disabled history layer, zoomed canvas, saved project.")
except Exception as e:
    print("PYQGIS_EXCEPTION:", traceback.format_exc())
"""

def main():
    print("1. Sending script to QGIS MCP...")
    res = send_qgis_mcp("execute_code", {"code": PYQGIS_SCRIPT, "timeout": 30.0})
    stdout = res.get("result", {}).get("stdout", "")
    print("STDOUT:", stdout)
    
    print("2. Calling save_project...")
    save_res = send_qgis_mcp("save_project")
    print("Save:", save_res)
    
    print("3. Capturing live canvas...")
    img_res = send_qgis_mcp("get_canvas_screenshot")
    out_img = ROOT / "workspace/reviews/t10_antigravity_20261013/qgis_canvas_t10_integrated.png"
    if img_res.get("status") == "success":
        b64 = img_res.get("result", {}).get("base64_data")
        if b64:
            with open(out_img, "wb") as f:
                f.write(base64.b64decode(b64))
            print(f"Canvas saved: {out_img} ({out_img.stat().st_size} bytes)")
    else:
        print("Screenshot error:", img_res)

if __name__ == "__main__":
    main()
