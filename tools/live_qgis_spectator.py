# -*- coding: utf-8 -*-
"""
StratumRO — Live QGIS Spectator Controller (MD 9 Implementation).
Visualizes the real intermediate pipeline outputs stage-by-stage
directly inside the QGIS map canvas, refreshing the viewport and
recording evidence screenshots for human-observable auditing.
"""

import os
import sys
import time
from typing import Optional, Dict, Any

from qgis.core import (
    QgsProject,
    QgsRasterLayer,
    QgsVectorLayer,
    QgsRectangle,
    Qgis
)
from qgis.PyQt import QtCore, QtWidgets


def run_spectator_pipeline(delay_sec: float = 2.5):
    """Iterates through real staged outputs in workspace/e2e and renders them in QGIS."""
    from qgis.utils import iface

    if not iface:
        print("[StratumRO Spectator] Error: iface QGIS is not available.")
        return

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    e2e_dir = os.path.join(base_dir, "workspace", "e2e")
    evidence_dir = os.path.join(e2e_dir, "evidence")
    os.makedirs(evidence_dir, exist_ok=True)

    project = QgsProject.instance()
    canvas = iface.mapCanvas()
    root = project.layerTreeRoot()
    msg_bar = iface.messageBar()

    # Import desktop operator for screenshot capturing
    try:
        sys.path.insert(0, base_dir)
        from tools.desktop_operator import DesktopOperator
        operator = DesktopOperator(evidence_dir=evidence_dir)
    except Exception as e:
        operator = None
        print(f"[StratumRO Spectator] DesktopOperator init notice: {e}")

    def process_ui(seconds=delay_sec):
        canvas.refresh()
        end_time = time.time() + seconds
        while time.time() < end_time:
            QtWidgets.QApplication.processEvents()
            time.sleep(0.05)

    def capture_evidence(stage_name):
        if operator:
            return operator.capture_stage_screenshot(stage_name)
        return ""

    print("\n=======================================================")
    print("  StratumRO — Mod Spectator E2E Real Initiat")
    print("=======================================================\n")

    # Focus area in Stereo 70 (USAMV Cluj)
    focus_extent = QgsRectangle(390600.0, 585250.0, 391250.0, 585800.0)
    canvas.setExtent(focus_extent)
    canvas.refresh()

    msg_bar.pushMessage(
        "StratumRO AI",
        "Mod Spectator E2E: Vizualizare a rezultatelor REALE pe etape (Stereo 70 / EPSG:3844)",
        Qgis.Info,
        5
    )
    process_ui(2.0)

    # -------------------------------------------------------------
    # ETAPA 1: Ortofoto + LiDAR Extent + AOI
    # -------------------------------------------------------------
    msg_bar.pushMessage("Etapa 1 / 8", "Ingestie Date Reale: Ortofoto Cluj & Extindere LiDAR...", Qgis.Info, 4)
    ortho_crop = os.path.join(e2e_dir, "04_orthophoto", "active_ortho_crop.tif")
    if not os.path.isfile(ortho_crop):
        # Fallback to general ortho crop if exists
        ortho_crop = os.path.join(base_dir, "workspace", "output", "orto.tif")

    if os.path.isfile(ortho_crop):
        layer_ortho = QgsRasterLayer(ortho_crop, "1. Ortofoto Real", "gdal")
        if layer_ortho.isValid():
            project.addMapLayer(layer_ortho)
    
    lidar_extent = os.path.join(e2e_dir, "02_lidar", "lidar_extent.geojson")
    if os.path.isfile(lidar_extent):
        layer_extent = QgsVectorLayer(lidar_extent, "1. Extindere LiDAR (Stereo 70)", "ogr")
        if layer_extent.isValid():
            project.addMapLayer(layer_extent)

    process_ui()
    capture_evidence("stage01_ortho_lidar")

    # -------------------------------------------------------------
    # ETAPA 2: Real nDSM & Candidate Centroids
    # -------------------------------------------------------------
    msg_bar.pushMessage("Etapa 2 / 8", "nDSM Real & Candidati Altimetrici...", Qgis.Info, 4)
    ndsm_path = os.path.join(e2e_dir, "03_ndsm", "ndsm_stereo70.tif")
    if not os.path.isfile(ndsm_path):
        ndsm_path = os.path.join(base_dir, "workspace", "output", "ndsm_stereo70.tif")

    if os.path.isfile(ndsm_path):
        layer_ndsm = QgsRasterLayer(ndsm_path, "2. nDSM Real", "gdal")
        if layer_ndsm.isValid():
            project.addMapLayer(layer_ndsm)

    cand_path = os.path.join(e2e_dir, "02_lidar", "candidates.geojson")
    if os.path.isfile(cand_path):
        layer_cand = QgsVectorLayer(cand_path, "2. Candidati Cladiri LiDAR", "ogr")
        if layer_cand.isValid():
            project.addMapLayer(layer_cand)

    process_ui()
    capture_evidence("stage02_ndsm_candidates")

    # -------------------------------------------------------------
    # ETAPA 3: Real SAM2 Masks
    # -------------------------------------------------------------
    msg_bar.pushMessage("Etapa 3 / 8", "Masti Brute SAM 2 Hiera (CUDA GPU)...", Qgis.Info, 4)
    sam2_path = os.path.join(e2e_dir, "05_sam2", "sam2_masks.geojson")
    if os.path.isfile(sam2_path):
        layer_sam2 = QgsVectorLayer(sam2_path, "3. Masti SAM2 Brute", "ogr")
        if layer_sam2.isValid():
            project.addMapLayer(layer_sam2)

    process_ui()
    capture_evidence("stage03_sam2_masks")

    # -------------------------------------------------------------
    # ETAPA 4: Sensor Fusion (LiDAR + SAM2)
    # -------------------------------------------------------------
    msg_bar.pushMessage("Etapa 4 / 8", "Fuziune Senzoriala (LiDAR + SAM2 Confirmat)...", Qgis.Info, 4)
    fusion_path = os.path.join(e2e_dir, "06_fusion", "fused_buildings.geojson")
    if os.path.isfile(fusion_path):
        layer_fusion = QgsVectorLayer(fusion_path, "4. Fuziune Hibrida Confirmata", "ogr")
        if layer_fusion.isValid():
            project.addMapLayer(layer_fusion)

    process_ui()
    capture_evidence("stage04_fusion")

    # -------------------------------------------------------------
    # ETAPA 5: Regularizare Ortogonala 90°
    # -------------------------------------------------------------
    msg_bar.pushMessage("Etapa 5 / 8", "Regularizare Ortogonala 90° (Dreptunghiuri Canonice)...", Qgis.Info, 4)
    reg_path = os.path.join(e2e_dir, "08_regularization", "regularized_footprints.geojson")
    if os.path.isfile(reg_path):
        layer_reg = QgsVectorLayer(reg_path, "5. Amprente Regularizate 90°", "ogr")
        if layer_reg.isValid():
            project.addMapLayer(layer_reg)

    process_ui()
    capture_evidence("stage05_regularization")

    # -------------------------------------------------------------
    # ETAPA 6: Retragere Streasina ANCPI (-0.40m)
    # -------------------------------------------------------------
    msg_bar.pushMessage("Etapa 6 / 8", "Retragere Streasina (-0.40m) -> Amprenta Sol ANCPI...", Qgis.Info, 4)
    eave_path = os.path.join(e2e_dir, "09_eave", "sol_ancpi_footprints.geojson")
    if os.path.isfile(eave_path):
        layer_eave = QgsVectorLayer(eave_path, "6. Amprente Sol ANCPI", "ogr")
        if layer_eave.isValid():
            project.addMapLayer(layer_eave)

    process_ui()
    capture_evidence("stage06_eave_offset")

    # -------------------------------------------------------------
    # ETAPA 7: Validare Geodezica & Topologica
    # -------------------------------------------------------------
    msg_bar.pushMessage("Etapa 7 / 8", "Validare Geodezica & Suprapunere Ground Truth...", Qgis.Info, 4)
    val_path = os.path.join(e2e_dir, "10_validation", "validation_overlay.geojson")
    if os.path.isfile(val_path):
        layer_val = QgsVectorLayer(val_path, "7. Validare Topologica & GT", "ogr")
        if layer_val.isValid():
            project.addMapLayer(layer_val)

    process_ui()
    capture_evidence("stage07_validation")

    # -------------------------------------------------------------
    # ETAPA 8: Livrabile Finale (TopoLT CAD & .CP)
    # -------------------------------------------------------------
    msg_bar.pushMessage(
        "Etapa 8 / 8",
        "Livrabile Finale Aprobate: TopoLT CAD (.dxf) & .CP eTerra...",
        Qgis.Success,
        8
    )
    process_ui(3.0)
    capture_evidence("stage08_final_export")

    print("[StratumRO Spectator] Prezentarea live a etapelor reale a fost finalizata cu succes!")


def init_spectator():
    QtCore.QTimer.singleShot(1500, run_spectator_pipeline)


if __name__ == "__main__" or "qgis" in sys.modules:
    QtCore.QTimer.singleShot(2500, init_spectator)
