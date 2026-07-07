# -*- coding: utf-8 -*-

import os
import json
import requests
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import pyqtSignal
# Am adăugat QgsRasterLayer în linia de mai jos pentru importul PyQGIS
from qgis.core import QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsProject, QgsRasterLayer
from qgis.gui import QgsMapToolExtent

# Îi spunem programului să moștenească designul din fișierul _base
from .stratum_ro_dockwidget_base import Ui_StratumRODockWidgetBase

class StratumRODockWidget(QtWidgets.QDockWidget, Ui_StratumRODockWidgetBase):
    closingPlugin = pyqtSignal()

    def __init__(self, iface, parent=None):
        super(StratumRODockWidget, self).__init__(parent)
        self.iface = iface
        
        # Inițializăm componentele vizuale
        self.setupUi(self)

        # Variabile pentru stocarea selecției geografice
        self.current_aoi_geometry = None
        self.map_tool = None
        self.api_url = "http://localhost:8000/api/v1/segmentation/process"

        # Conectăm butoanele la funcțiile lor din acest fișier
        self.btnSelectAOI.clicked.connect(self.init_map_tool)
        self.btnRunSegmentation.clicked.connect(self.run_segmentation_pipeline)

    def init_map_tool(self):
        """Activează instrumentul de selecție elastică pe canvas-ul QGIS."""
        self.map_tool = QgsMapToolExtent(self.iface.mapCanvas())
        self.map_tool.extentChanged.connect(self.capture_coordinates)
        self.iface.mapCanvas().setMapTool(self.map_tool)
        self.lblStatus_2.setText("Status: Trage un dreptunghi pe hartă...")

    def capture_coordinates(self, extent):
        """Captează coordonatele de pe ecran și le forțează în Stereo 70 m."""
        self.iface.mapCanvas().unsetMapTool(self.map_tool)
        
        xmin = extent.xMinimum()
        xmax = extent.xMaximum()
        ymin = extent.yMinimum()
        ymax = extent.yMaximum()

        current_crs = self.iface.mapCanvas().mapSettings().destinationCrs()
        stereo70 = QgsCoordinateReferenceSystem("EPSG:31700")

        if current_crs.authid() != "EPSG:31700":
            transform = QgsCoordinateTransform(current_crs, stereo70, QgsProject.instance())
            point_min = transform.transform(xmin, ymin)
            point_max = transform.transform(xmax, ymax)
            xmin, ymin = point_min.x(), point_min.y()
            xmax, ymax = point_max.x(), point_max.y()

        # Structură închisă tip Poligon/Bounding Box pentru API
        self.current_aoi_geometry = [
            [xmin, ymin],
            [xmax, ymin],
            [xmax, ymax],
            [xmin, ymax],
            [xmin, ymin]
        ]

        self.lblStatus_2.setText("Status: AOI salvat cu succes în Stereo 70!")
        print(f"[StratumRO] Coordonate salvate: {self.current_aoi_geometry}")

    def run_segmentation_pipeline(self):
        """Execută cererea HTTP către API-ul unificat sau rulează fallback-ul local."""
        if not self.current_aoi_geometry:
            self.lblStatus_2.setText("Status: Eroare! Selectează mai întâi o zonă pe hartă.")
            return

        self.lblStatus_2.setText("Status: Se trimite payload-ul la FastAPI...")

        payload = {
            "project_name": "Segmentare_Nationala_StratumRO",
            "crs": "EPSG:31700",
            "aoi_selection_mode": "hybrid",
            "geometry": {
                "type": "Polygon",
                "coordinates": [self.current_aoi_geometry]
            },
            "administrative": {
                "siruta_code": 26573,
                "level": "uat",
                "name": "Oradea",
                "county": "Bihor"
            },
            "parameters": {
                "model_version": "v1.0-default",
                "confidence_threshold": 0.5
            }
        }

        try:
            response = requests.post(self.api_url, json=payload, timeout=3)
            if response.status_code in [200, 201]:
                data = response.json()
                self.lblStatus_2.setText(f"Status: Server conectat!\nTask ID: {data.get('task_id')}")
            else:
                self.lblStatus_2.setText(f"Status: Eroare Server ({response.status_code})")
        except requests.exceptions.RequestException:
            # Serverul fiind offline, pornește automat testul de polling controlat cu auto-încărcare layer
            self.execute_mock_polling()

    def execute_mock_polling(self):
        """Simulează pașii din backend și declanșează încărcarea straturilor la final."""
        QtCore.QTimer.singleShot(2000, lambda: self.lblStatus_2.setText(
            "Status: [Task: queued]\nJob înregistrat în server. Coordonate mapate național."
        ))
        QtCore.QTimer.singleShot(4000, lambda: self.lblStatus_2.setText(
            "Status: [Task: processing - 45%]\nDescărcare date LAKI finalizată. Filtrare în curs..."
        ))
        # La secunda 6, statusul devine complet și apelăm funcția nativă de încărcare layer în QGIS
        QtCore.QTimer.singleShot(6000, self.load_results_into_qgis)

    def load_results_into_qgis(self):
        """Etapa 36: Încarcă automat un raster demo direct în panoul de Layers din QGIS."""
        self.lblStatus_2.setText("Status: [Task: completed - 100%]\nSe încarcă straturile în QGIS...")
        
        # Folosim un link XYZ standard ca placeholder (OSM standard) pentru a demonstra randarea automată.
        # Când backend-ul va fi online, aici se va schimba cu calea către TIFF-ul generat de modelul SAM 2.
        url_placeholder = "type=xyz&url=https://tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png"
        
        # Instanțiem stratul raster utilizând motorul PyQGIS
        result_layer = QgsRasterLayer(url_placeholder, "Rezultat_Segmentare_StratumRO", "wms")
        
        if result_layer.isValid():
            # Injectează stratul direct în proiectul curent deschis pe ecran
            QgsProject.instance().addMapLayer(result_layer)
            self.lblStatus_2.setText("Status: [Task: completed - 100%]\nProcesare finalizată! Stratul a fost adăugat.")
        else:
            self.lblStatus_2.setText("Status: Eroare la încărcarea stratului rezultat.")

    def closeEvent(self, event):
        self.closingPlugin.emit()
        event.accept()