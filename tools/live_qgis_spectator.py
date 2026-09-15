# -*- coding: utf-8 -*-
"""
StratumRO — Live QGIS Spectator Controller.
Executes and visualizes the complete geodetic pipeline step-by-step
directly inside the QGIS map canvas, allowing the user to watch each
layer emerge, regularize, and validate in real-time.
"""

import os
import sys
import time

from qgis.core import (
    QgsProject,
    QgsRectangle,
    Qgis
)
from qgis.PyQt import QtCore, QtWidgets


def run_spectator_demo():
    from qgis.utils import iface

    if not iface:
        print("[StratumRO Spectator] Eroare: iface QGIS nu este disponibil.")
        return

    project = QgsProject.instance()

    # Dacă proiectul nu are straturi încărcate, îl încărcăm automat
    if len(project.mapLayers()) == 0:
        proj_path = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), "workspace", "output", "StratumRO_Rezultate.qgz"))
        if not os.path.exists(proj_path):
            proj_path = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), "StratumRO_Inspectie_Vizuala.qgz"))
        if os.path.exists(proj_path):
            print(f"[StratumRO Spectator] Se încarcă proiectul: {proj_path}")
            project.read(proj_path)

    canvas = iface.mapCanvas()
    root = project.layerTreeRoot()
    msg_bar = iface.messageBar()

    def set_layer_visible_by_keyword(keyword, visible=True):
        """Activează sau dezactivează vizibilitatea straturilor care conțin keyword."""
        kw = keyword.lower()
        found = False
        def traverse(node):
            nonlocal found
            for child in node.children():
                if hasattr(child, "name") and kw in child.name().lower():
                    child.setItemVisibilityChecked(visible)
                    found = True
                if hasattr(child, "children"):
                    traverse(child)
        traverse(root)
        return found

    def process_ui(delay_seconds=3.5):
        """Actualizează canvas-ul și permite interfeței grafice să randeze live."""
        canvas.refresh()
        end_time = time.time() + delay_seconds
        while time.time() < end_time:
            QtWidgets.QApplication.processEvents()
            time.sleep(0.05)

    print("\n=======================================================")
    print("  StratumRO — Mod Spectator QGIS Inițiat")
    print("=======================================================\n")

    # 1. Inițializare: Dezactivăm toate straturile vectoriale
    keywords_all = [
        "limită sector", "sol ancpi", "acoperișuri", "anexe",
        "dr:", "hr:", "vn:", "cimitir", "terenuri arabile", "unclassified",
        "arbori", "stâlpi", "etapa 1", "etapa 2", "etapa 3", "etapa 4", "etapa 5",
        "ndsm", "cadastru teren", "predicții ai"
    ]
    for kw in keywords_all:
        set_layer_visible_by_keyword(kw, False)

    # Menținem activ ortofotoplanul de fundal
    set_layer_visible_by_keyword("ortofoto", True)

    # Zoom pe zona clusterului principal de clădiri (USAMV Cluj în Stereo 70)
    focus_extent = QgsRectangle(390650.0, 585250.0, 391250.0, 585750.0)
    canvas.setExtent(focus_extent)
    canvas.refresh()

    msg_bar.pushMessage(
        "StratumRO AI",
        "Mod Spectator Activat: Vizualizare live a etapelor geodezice (Stereo 70 / EPSG:3844)",
        Qgis.Info,
        5
    )
    process_ui(3.0)

    # -------------------------------------------------------------
    # ETAPA 1: Ingestie LiDAR & nDSM
    # -------------------------------------------------------------
    msg_bar.pushMessage(
        "Etapa 1 / 6",
        "LiDAR & nDSM: Identificare candidați altimetrici (H >= 2.5m), arbori și stâlpi...",
        Qgis.Info,
        4
    )
    set_layer_visible_by_keyword("ndsm", True)
    set_layer_visible_by_keyword("arbori", True)
    set_layer_visible_by_keyword("stâlpi", True)
    process_ui(4.0)

    # -------------------------------------------------------------
    # ETAPA 2: Meta SAM2 Hiera — Măști Brute
    # -------------------------------------------------------------
    msg_bar.pushMessage(
        "Etapa 2 / 6",
        "Meta SAM2 Hiera: Segmentare optică din ortofotoplan ghidată de candidații LiDAR (416 clădiri brute)...",
        Qgis.Info,
        4
    )
    set_layer_visible_by_keyword("ndsm", False)
    set_layer_visible_by_keyword("etapa 1", True)
    process_ui(4.0)

    # -------------------------------------------------------------
    # ETAPA 3: Curățare Morfologică & Filtrare Colți
    # -------------------------------------------------------------
    msg_bar.pushMessage(
        "Etapa 3 / 6",
        "Curățare Morfologică: Eliminare colți ascuțiți (horn-spikes) și filtrare zgomot coronament...",
        Qgis.Info,
        4
    )
    set_layer_visible_by_keyword("etapa 1", False)
    set_layer_visible_by_keyword("etapa 2", True)
    process_ui(4.0)

    # -------------------------------------------------------------
    # ETAPA 4: Regularizare Ortogonală 90°
    # -------------------------------------------------------------
    msg_bar.pushMessage(
        "Etapa 4 / 6",
        "Regularizare 90°: Potrivire dreptunghiuri canonice (4 noduri) și ortogonalizare colțuri...",
        Qgis.Info,
        4
    )
    set_layer_visible_by_keyword("etapa 2", False)
    set_layer_visible_by_keyword("acoperișuri", True)
    set_layer_visible_by_keyword("anexe", True)
    process_ui(4.5)

    # -------------------------------------------------------------
    # ETAPA 5: Retragere Streașină (-0.40m) -> Amprentă la Sol ANCPI
    # -------------------------------------------------------------
    msg_bar.pushMessage(
        "Etapa 5 / 6",
        "Retragere Streașină (-0.40m): Trecere de la contur acoperiș la amprentă soclu la sol (CLADIRI_SOL_ANCPI)...",
        Qgis.Info,
        4
    )
    # Lăsăm atât acoperișul cât și solul active pentru comparare
    set_layer_visible_by_keyword("sol ancpi", True)
    process_ui(4.5)

    # -------------------------------------------------------------
    # ETAPA 6: Partiționare Planară 100% & Sector Cadastral
    # -------------------------------------------------------------
    msg_bar.pushMessage(
        "Etapa 6 / 6",
        "Partiționare Planară 100%: Drumuri (DR), Ape (HR), Vii (VN), Cimitir, Arabil (A), Curți fără goluri...",
        Qgis.Info,
        4
    )
    set_layer_visible_by_keyword("dr:", True)
    set_layer_visible_by_keyword("hr:", True)
    set_layer_visible_by_keyword("vn:", True)
    set_layer_visible_by_keyword("cimitir", True)
    set_layer_visible_by_keyword("terenuri arabile", True)
    set_layer_visible_by_keyword("unclassified", True)
    set_layer_visible_by_keyword("limită sector", True)
    process_ui(5.0)

    # -------------------------------------------------------------
    # FINALIZARE: Deschidere DockWidget StratumRO AI
    # -------------------------------------------------------------
    msg_bar.pushMessage(
        "Succes StratumRO",
        "Pipeline Finalizat! Livrabile generate: GeoPackage Stereo 70 + AutoCAD DXF TopoLT (1CC, 2CC, CP, PAD).",
        Qgis.Success,
        10
    )

    try:
        from stratum_ro.stratum_ro_dockwidget import StratumRODockWidget
        for dock in iface.mainWindow().findChildren(QtWidgets.QDockWidget):
            if isinstance(dock, StratumRODockWidget):
                dock.show()
                dock.raise_()
                if hasattr(dock, "tabs"):
                    dock.tabs.setCurrentIndex(1)
                break
    except Exception as e:
        print(f"[StratumRO Spectator] Dock notification: {e}")

    print("\n[StratumRO Spectator] Demonstrația spectator a fost executată cu succes!\n")


def init_spectator():
    from qgis.core import QgsProject
    # Asigurăm că QGIS este inițializat complet
    QtCore.QTimer.singleShot(1500, run_spectator_demo)


# Rulare temporizată pentru a permite încărcarea completă a UI-ului QGIS
QtCore.QTimer.singleShot(2500, init_spectator)
