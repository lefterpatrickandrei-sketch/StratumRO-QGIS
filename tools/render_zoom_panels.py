# -*- coding: utf-8 -*-
"""
Render Zoom Panels with Cadastral Overlays (P2.1)
================================================
Produces:
1. docs/assets/zoom_campus_core.jpg
   BBox: [390880, 585480, 391150, 585720] - Central campus buildings
2. docs/assets/zoom_boulevard_fp_reale.jpg
   BBox: [390600, 585620, 390880, 585820] - Calea Mănăștur residential strip (OSM verified)
3. docs/assets/zoom_cimitir_sud.jpg
   BBox: [390900, 585050, 391180, 585320] - Mănăștur Cemetery edge & vegetation rejection

Supports execution via QGIS Python (python-qgis.bat) or standard Python virtualenv.
Requires local datasets in workspace/output/ and data/ground_truth/.
"""

import os
import sys

base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, base_dir)

try:
    from qgis.core import (
        QgsApplication,
        QgsRasterLayer,
        QgsVectorLayer,
        QgsCoordinateReferenceSystem,
        QgsSingleSymbolRenderer,
        QgsFillSymbol,
        QgsMapSettings,
        QgsMapRendererParallelJob,
        QgsRectangle
    )
    from PyQt5.QtCore import QSize
    HAS_QGIS = True
except ImportError:
    HAS_QGIS = False

PANELS = [
    {
        "name": "zoom_campus_core.jpg",
        "title": "Campus Core",
        "bbox": [390880, 585480, 391150, 585720],
        "size": (1200, 900)
    },
    {
        "name": "zoom_boulevard_fp_reale.jpg",
        "title": "Boulevard Residential (OSM Verified)",
        "bbox": [390600, 585620, 390880, 585820],
        "size": (1200, 900)
    },
    {
        "name": "zoom_cimitir_sud.jpg",
        "title": "Cemetery South & False Positive Filtering",
        "bbox": [390900, 585050, 391180, 585320],
        "size": (1200, 900)
    }
]


def render_all_with_pillow():
    from tools.render_visual_evidence import (
        render_campus_core_zoom,
        render_boulevard_zoom,
        render_cemetery_zoom
    )
    assets_dir = os.path.join(base_dir, "docs", "assets")
    render_campus_core_zoom(os.path.join(assets_dir, "zoom_campus_core.jpg"))
    render_boulevard_zoom(os.path.join(assets_dir, "zoom_boulevard_fp_reale.jpg"))
    render_cemetery_zoom(os.path.join(assets_dir, "zoom_cimitir_sud.jpg"))
    print("[+] Rendered 3 zoom panels via PIL/Rasterio.")


def render_with_qgis():
    qgs = QgsApplication([], False)
    qgs.initQgis()

    orto_path = os.path.join(base_dir, "workspace", "output", "ortofoto_cluj_usamv_rgb.vrt")
    pred_path = os.path.join(base_dir, "workspace", "output", "cladiri_stereo70.gpkg") + "|layername=CLADIRI_HIBRID"
    gt_path = os.path.join(base_dir, "data", "ground_truth", "tier1_teren.geojson")

    orto_layer = QgsRasterLayer(orto_path, "Ortofoto RGB", "gdal")
    pred_layer = QgsVectorLayer(pred_path, "AI Pred", "ogr")
    gt_layer = QgsVectorLayer(gt_path, "Ground Truth", "ogr")

    if not orto_layer.isValid() or not pred_layer.isValid():
        print("[-] Layers invalid for QGIS rendering")
        qgs.exitQgis()
        return False

    sym_pred = QgsFillSymbol.createSimple({
        "color": "255,109,0,45",
        "outline_color": "255,109,0,255",
        "outline_width": "0.9",
        "outline_style": "solid"
    })
    pred_layer.setRenderer(QgsSingleSymbolRenderer(sym_pred))

    sym_gt = QgsFillSymbol.createSimple({
        "color": "0,0,0,0",
        "outline_color": "0,255,255,255",
        "outline_width": "1.0",
        "outline_style": "dash"
    })
    gt_layer.setRenderer(QgsSingleSymbolRenderer(sym_gt))

    for panel in PANELS:
        settings = QgsMapSettings()
        settings.setLayers([gt_layer, pred_layer, orto_layer])
        settings.setDestinationCrs(QgsCoordinateReferenceSystem("EPSG:3844"))
        b = panel["bbox"]
        settings.setExtent(QgsRectangle(b[0], b[1], b[2], b[3]))
        settings.setOutputSize(QSize(panel["size"][0], panel["size"][1]))

        job = QgsMapRendererParallelJob(settings)
        job.start()
        job.waitForFinished()

        out_path = os.path.join(base_dir, "docs", "assets", panel["name"])
        job.renderedImage().save(out_path, "JPEG", 92)
        print(f"[+] Rendered QGIS panel {panel['name']}")

    qgs.exitQgis()
    return True


if __name__ == "__main__":
    if HAS_QGIS:
        try:
            render_with_qgis()
        except Exception as e:
            print(f"[!] QGIS error ({e}), falling back to PIL/rasterio renderer...")
            render_all_with_pillow()
    else:
        render_all_with_pillow()
