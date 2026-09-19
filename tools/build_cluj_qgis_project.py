"""
Builds an authentic, professionally styled QGIS project for Phase 2 Cluj inspection.
Loads raster imagery, nDSM, raw SAM2 predictions, regularized CAD vectors,
deduplicated ground truth reference, and coregistration QC points.
"""

import sys
import os
from qgis.core import (
    QgsApplication,
    QgsProject,
    QgsRasterLayer,
    QgsVectorLayer,
    QgsCoordinateReferenceSystem,
    QgsLayerTreeGroup,
    QgsSingleSymbolRenderer,
    QgsFillSymbol,
    QgsMarkerSymbol,
    QgsLineSymbol,
    QgsSimpleFillSymbolLayer,
    QgsSimpleMarkerSymbolLayer,
    QgsPalLayerSettings,
    QgsVectorLayerSimpleLabeling,
    QgsTextFormat,
    QgsTextBufferSettings,
)
from PyQt5.QtGui import QColor

def create_cluj_project():
    app = QgsApplication([], False)
    QgsApplication.initQgis()

    project = QgsProject.instance()
    project.clear()
    project.setTitle("StratumRO — Cluj Phase 2 Benchmark Verification")

    # Set project CRS to Stereo 70 (EPSG:3844)
    crs_3844 = QgsCoordinateReferenceSystem("EPSG:3844")
    project.setCrs(crs_3844)

    base_dir = os.path.abspath(".")
    root = project.layerTreeRoot()

    # Create Groups
    group_qc = root.addGroup("04. Roof-to-Reference Centroid Divergence")
    group_ref = root.addGroup("03. Ground Truth Reference")
    group_ai = root.addGroup("02. AI Inference & CAD Regularization")
    group_rasters = root.addGroup("01. Source Rasters")

    # 1. Rasters
    ortho_path = os.path.join(base_dir, "workspace", "e2e", "04_orthophoto", "active_ortho_crop.tif")
    if os.path.exists(ortho_path):
        rl_ortho = QgsRasterLayer(ortho_path, "Cluj Orthophoto 20cm (RGB)", "gdal")
        if rl_ortho.isValid():
            project.addMapLayer(rl_ortho, False)
            group_rasters.addLayer(rl_ortho)
            print("[+] Added Cluj Orthophoto")

    ndsm_path = os.path.join(base_dir, "workspace", "derived", "cluj_ndsm_1m.tif")
    if os.path.exists(ndsm_path):
        rl_ndsm = QgsRasterLayer(ndsm_path, "Reconstructed nDSM 1m (LiDAR)", "gdal")
        if rl_ndsm.isValid():
            project.addMapLayer(rl_ndsm, False)
            group_rasters.addLayer(rl_ndsm)
            print("[+] Added Reconstructed nDSM")

    # 2. AI & CAD Vectors
    raw_pred_path = os.path.join(base_dir, "workspace", "predictions", "cluj_raw_sam2_predictions.geojson")
    if os.path.exists(raw_pred_path):
        vl_raw = QgsVectorLayer(raw_pred_path, "Raw SAM 2 Footprints (Organic AI)", "ogr")
        if vl_raw.isValid():
            symbol = QgsFillSymbol.createSimple({
                'color': '0,200,255,40',
                'outline_color': '0,180,240,255',
                'outline_width': '0.35',
                'outline_style': 'solid'
            })
            vl_raw.setRenderer(QgsSingleSymbolRenderer(symbol))
            project.addMapLayer(vl_raw, False)
            group_ai.addLayer(vl_raw)
            print("[+] Added Raw SAM 2 Footprints")

    reg_pred_path = os.path.join(base_dir, "workspace", "predictions", "cluj_regularized_predictions.geojson")
    if os.path.exists(reg_pred_path):
        vl_reg = QgsVectorLayer(reg_pred_path, "Regularized CAD Footprints (90° Orthogonal)", "ogr")
        if vl_reg.isValid():
            symbol = QgsFillSymbol.createSimple({
                'color': '255,140,0,60',
                'outline_color': '255,100,0,255',
                'outline_width': '0.6',
                'outline_style': 'solid'
            })
            vl_reg.setRenderer(QgsSingleSymbolRenderer(symbol))
            project.addMapLayer(vl_reg, False)
            group_ai.addLayer(vl_reg)
            print("[+] Added Regularized CAD Footprints")

    # 3. Ground Truth Reference
    ref_path = os.path.join(base_dir, "data", "derived_reference", "cluj_combined_unique_150.geojson")
    if os.path.exists(ref_path):
        vl_ref = QgsVectorLayer(ref_path, "Ground Truth Cadastre (150 Unique Buildings)", "ogr")
        if vl_ref.isValid():
            symbol = QgsFillSymbol.createSimple({
                'color': '0,0,0,0',
                'outline_color': '0,220,0,255',
                'outline_width': '0.7',
                'outline_style': 'solid'
            })
            vl_ref.setRenderer(QgsSingleSymbolRenderer(symbol))
            project.addMapLayer(vl_ref, False)
            group_ref.addLayer(vl_ref)
            print("[+] Added Ground Truth Reference Layer")

    # 4. Centroid Divergence Points
    qc_path = os.path.join(base_dir, "reports", "cluj", "coregistration_points.geojson")
    if os.path.exists(qc_path):
        vl_qc = QgsVectorLayer(qc_path, "Roof-to-Ref Centroid Divergence Points (26 buildings)", "ogr")
        if vl_qc.isValid():
            marker_symbol = QgsMarkerSymbol.createSimple({
                'name': 'cross',
                'size': '4.0',
                'color': '255,0,255,255',
                'outline_color': '255,0,255,255',
                'outline_width': '0.5'
            })
            vl_qc.setRenderer(QgsSingleSymbolRenderer(marker_symbol))

            # Add labeling with err2d
            pal_settings = QgsPalLayerSettings()
            pal_settings.fieldName = "concat('Δ2D: ', to_string(round(\"err2d\", 2)), ' m')"
            pal_settings.isExpression = True
            text_format = QgsTextFormat()
            text_format.setSize(8)
            text_format.setColor(QColor(255, 0, 255))
            buffer = QgsTextBufferSettings()
            buffer.setEnabled(True)
            buffer.setSize(1.0)
            buffer.setColor(QColor(255, 255, 255))
            text_format.setBuffer(buffer)
            pal_settings.setFormat(text_format)
            vl_qc.setLabeling(QgsVectorLayerSimpleLabeling(pal_settings))
            vl_qc.setLabelsEnabled(True)

            project.addMapLayer(vl_qc, False)
            group_qc.addLayer(vl_qc)
            print("[+] Added Roof-to-Ref Centroid Divergence Layer")

    output_project_path = os.path.join(base_dir, "StratumRO_Cluj_Phase2_Spectator.qgs")
    project.write(output_project_path)
    print(f"[+] Successfully wrote QGIS Project: {output_project_path}")

    QgsApplication.exitQgis()

if __name__ == "__main__":
    create_cluj_project()
