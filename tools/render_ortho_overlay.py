# -*- coding: utf-8 -*-
"""
Render Orthophoto Inspection Map with Cadastral Overlays (P2.1)
==============================================================
Produces docs/assets/inspectie_orto_cadastru_ai.jpg showing:
- 10cm Orthophoto base
- Ground Truth (cyan dashed)
- AI Predictions (orange solid)
- Sector Boundary (yellow)

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
        QgsProject,
        QgsRasterLayer,
        QgsVectorLayer,
        QgsCoordinateReferenceSystem,
        QgsSingleSymbolRenderer,
        QgsFillSymbol,
        QgsMapSettings,
        QgsMapRendererParallelJob,
        QgsRectangle
    )
    from PyQt5.QtGui import QColor
    from PyQt5.QtCore import QSize
    HAS_QGIS = True
except ImportError:
    HAS_QGIS = False


def render_with_qgis():
    qgs = QgsApplication([], False)
    qgs.initQgis()

    orto_path = os.path.join(base_dir, "workspace", "output", "ortofoto_cluj_usamv_rgb.vrt")
    pred_path = os.path.join(base_dir, "workspace", "output", "cladiri_stereo70.gpkg") + "|layername=CLADIRI_HIBRID"
    gt_path = os.path.join(base_dir, "data", "ground_truth", "tier1_teren.geojson")
    limita_path = os.path.join(base_dir, "workspace", "output", "cladiri_stereo70.gpkg") + "|layername=LIMITA_SECTOR_CADASTRAL"

    orto_layer = QgsRasterLayer(orto_path, "Ortofoto RGB", "gdal")
    if not orto_layer.isValid():
        print("[-] Ortofoto layer invalid")
        qgs.exitQgis()
        return False

    pred_layer = QgsVectorLayer(pred_path, "AI Pred", "ogr")
    sym_pred = QgsFillSymbol.createSimple({
        "color": "255,109,0,40",
        "outline_color": "255,109,0,255",
        "outline_width": "0.7",
        "outline_style": "solid"
    })
    pred_layer.setRenderer(QgsSingleSymbolRenderer(sym_pred))

    gt_layer = QgsVectorLayer(gt_path, "Ground Truth", "ogr")
    sym_gt = QgsFillSymbol.createSimple({
        "color": "0,0,0,0",
        "outline_color": "0,255,255,255",
        "outline_width": "0.8",
        "outline_style": "dash"
    })
    gt_layer.setRenderer(QgsSingleSymbolRenderer(sym_gt))

    limita_layer = QgsVectorLayer(limita_path, "Limita Sector", "ogr")

    settings = QgsMapSettings()
    settings.setLayers([gt_layer, pred_layer, orto_layer])
    settings.setDestinationCrs(QgsCoordinateReferenceSystem("EPSG:3844"))

    if limita_layer.isValid() and not limita_layer.extent().isEmpty():
        bbox = limita_layer.extent()
        print(f"[+] Using dynamic extent from LIMITA_SECTOR_CADASTRAL: {bbox.toString()}")
    else:
        bbox = QgsRectangle(390529.4, 584837.7, 391578.0, 585886.3)
        print(f"[!] Warning: LIMITA_SECTOR_CADASTRAL not found, using fallback bbox: {bbox.toString()}")

    settings.setExtent(bbox)
    settings.setOutputSize(QSize(2400, 1840))

    job = QgsMapRendererParallelJob(settings)
    job.start()
    job.waitForFinished()

    out_jpg = os.path.join(base_dir, "docs", "assets", "inspectie_orto_cadastru_ai.jpg")
    os.makedirs(os.path.dirname(out_jpg), exist_ok=True)
    job.renderedImage().save(out_jpg, "JPEG", 92)
    print(f"[+] Rendered QGIS Orthophoto inspection map to: {out_jpg}")
    qgs.exitQgis()
    return True


def render_with_pillow():
    from tools.render_visual_evidence import render_general_inspection_map
    out_jpg = os.path.join(base_dir, "docs", "assets", "inspectie_orto_cadastru_ai.jpg")
    render_general_inspection_map(out_jpg)


if __name__ == "__main__":
    if HAS_QGIS:
        try:
            render_with_qgis()
        except Exception as e:
            print(f"[!] QGIS rendering failed ({e}), falling back to PIL/rasterio renderer...")
            render_with_pillow()
    else:
        print("[i] QGIS Python bindings not found in current environment. Using headless PIL/rasterio renderer.")
        render_with_pillow()
