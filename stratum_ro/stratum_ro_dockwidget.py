# -*- coding: utf-8 -*-

import os
import requests
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import pyqtSignal
# Am adăugat QgsRasterLayer și QgsVectorLayer pentru importurile PyQGIS
from qgis.core import QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsProject, QgsRasterLayer, QgsVectorLayer
from qgis.gui import QgsMapToolExtent

# Îi spunem programului să moștenească designul din fișierul _base
from .stratum_ro_dockwidget_base import Ui_StratumRODockWidgetBase

class SegmentationWorker(QtCore.QThread):
    """
    Worker asincron (Etapa 40) pentru a executa cererile HTTP către backend-ul MLOps
    fără a bloca firul principal de execuție al interfeței grafice QGIS.
    """
    statusChanged = QtCore.pyqtSignal(str)
    taskCompleted = QtCore.pyqtSignal(str, str)  # raster_path, vector_path
    taskFailed = QtCore.pyqtSignal(str)  # error_message

    def __init__(self, api_url, payload, parent=None):
        super(SegmentationWorker, self).__init__(parent)
        self.api_url = api_url
        self.payload = payload

    def run(self):
        try:
            self.statusChanged.emit("Status: Se trimite cererea la FastAPI...")
            
            # 1. Trimiterea cererii POST inițiale (Etapa 37)
            response = requests.post(self.api_url, json=self.payload, timeout=10)
            
            # Tratare erori de status HTTP (Etapa 38)
            if response.status_code not in [200, 201, 202]:
                self.taskFailed.emit(f"Eroare Server: Cod status HTTP {response.status_code}")
                return

            data = response.json()
            task_id = data.get("task_id")
            
            # Dacă serverul întoarce direct rezultatele (sincron)
            if not task_id:
                results = data.get("results", {})
                if results:
                    self.taskCompleted.emit(results.get("raster_path"), results.get("vector_path"))
                else:
                    self.taskFailed.emit("Eroare Server: Răspunsul serverului nu conține rezultate sau Task ID.")
                return

            # 2. Polling asincron pentru verificarea statusului task-ului (Etapa 40)
            self.statusChanged.emit(f"Status: Task înregistrat!\nID: {task_id}")
            
            # Reconstituim URL-ul de polling bazat pe api_url:
            # /api/v1/segmentation/process -> /api/v1/tasks/{id}
            base_url = self.api_url.rsplit("/segmentation/process", 1)[0]
            poll_url = f"{base_url}/tasks/{task_id}"

            max_retries = 30  # Maxim 60 de secunde (30 interogări * 2 secunde pauză)
            retry_count = 0
            
            while retry_count < max_retries:
                self.msleep(2000)  # Așteaptă 2 secunde (QThread msleep)
                
                try:
                    poll_response = requests.get(poll_url, timeout=5)
                    if poll_response.status_code == 200:
                        poll_data = poll_response.json()
                        status = poll_data.get("status")
                        progress = poll_data.get("progress", 0)
                        
                        if status == "completed":
                            results = poll_data.get("results", {})
                            self.taskCompleted.emit(results.get("raster_path"), results.get("vector_path"))
                            return
                        elif status == "failed":
                            errors = poll_data.get("errors", ["Eroare internă backend"])
                            self.taskFailed.emit(f"Eroare Backend: {', '.join(errors)}")
                            return
                        else:
                            # Stadiu intermediar (queued / processing)
                            self.statusChanged.emit(f"Status: [Task: {status} - {progress}%]\nSe prelucrează datele...")
                    else:
                        self.statusChanged.emit(f"Status: Interogare task... (Cod HTTP {poll_response.status_code})")
                except requests.exceptions.RequestException:
                    # Tolerăm erori minore/temporare de conexiune în timpul polling-ului
                    self.statusChanged.emit("Status: Conexiune instabilă. Se reîncearcă...")
                
                retry_count += 1

            self.taskFailed.emit("Eroare: Timpul de așteptare pentru finalizarea procesării a expirat (Timeout).")

        except requests.exceptions.Timeout:
            self.taskFailed.emit("Eroare de rețea: Timpul de conectare la server a expirat (Timeout).")
        except requests.exceptions.ConnectionError:
            self.taskFailed.emit("Eroare: Nu s-a putut stabili conexiunea cu serverul. Asigură-te că backend-ul FastAPI local pe portul 8000 este pornit.")
        except Exception as e:
            self.taskFailed.emit(f"Eroare neprevăzută în firul de fundal: {str(e)}")


class StratumRODockWidget(QtWidgets.QDockWidget, Ui_StratumRODockWidgetBase):
    closingPlugin = pyqtSignal()

    def __init__(self, iface, parent=None):
        super(StratumRODockWidget, self).__init__(parent)
        self.iface = iface
        
        # Inițializăm componentele vizuale
        self.setupUi(self)

        # Variabile pentru stocarea selecției geografice și a thread-ului asincron
        self.current_aoi_geometry = None
        self.map_tool = None
        self.worker = None
        self.api_url = "http://localhost:8000/api/v1/segmentation/process"

        # Conectăm butoanele la funcțiile lor
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

    def validate_aoi_geometry(self):
        """Etapa 39: Validează structura geografică a Bounding Box-ului în Stereo 70."""
        if not self.current_aoi_geometry:
            return False, "Te rog selectează mai întâi o zonă pe hartă folosind butonul 'Selectează AOI'."
        
        # Limitele geodezice extinse ale României în Stereo 70 (EPSG:31700)
        # Acoperă inclusiv zonele de graniță: Jimbolia (vest), Sulina (est),
        # Vama Borșa (nord), Mangalia (sud-est)
        # X: ~128.000 – 875.000 m, Y: ~250.000 – 765.000 m
        RO_X_MIN, RO_X_MAX = 125000.0, 880000.0
        RO_Y_MIN, RO_Y_MAX = 245000.0, 770000.0
        
        for pt in self.current_aoi_geometry:
            x, y = pt[0], pt[1]
            if not (RO_X_MIN <= x <= RO_X_MAX) or not (RO_Y_MIN <= y <= RO_Y_MAX):
                return False, f"Coordonatele selectate ({x:.2f}, {y:.2f}) se află în afara limitelor geodezice ale României în Stereo 70."
        
        return True, ""

    def resolve_administrative_data(self):
        """
        Găsește dinamic UAT-ul, județul și codul SIRUTA prin intersecție spațială
        cu straturile vectoriale active în QGIS (de tip limite administrative / UAT).
        """
        fallback_data = {
            "siruta_code": 26573,
            "level": "uat",
            "name": "Oradea",
            "county": "Bihor"
        }
        
        if not self.current_aoi_geometry:
            return fallback_data

        try:
            from qgis.core import QgsPointXY, QgsGeometry, QgsFeatureRequest
            
            # 1. Construim geometria AOI
            poly_points = [QgsPointXY(pt[0], pt[1]) for pt in self.current_aoi_geometry]
            aoi_geom = QgsGeometry.fromPolygonXY([poly_points])
            centroid = aoi_geom.centroid().asPoint()
            
            # 2. Căutăm stratul UAT printre straturile active
            uat_layer = None
            for layer in QgsProject.instance().mapLayers().values():
                if isinstance(layer, QgsVectorLayer):
                    name_l = layer.name().lower()
                    if "uat" in name_l or "limite" in name_l or "siruta" in name_l or "localit" in name_l:
                        uat_layer = layer
                        break
            
            if not uat_layer:
                print("[StratumRO] Nu s-a găsit niciun strat activ de limite administrative (UAT/siruta). Se folosesc datele mock din Oradea.")
                return fallback_data

            # 3. Intersecție spațială pentru a găsi poligonul UAT care conține centroidul
            request = QgsFeatureRequest().setFilterRect(aoi_geom.boundingBox())
            for feature in uat_layer.getFeatures(request):
                if feature.geometry().contains(QgsGeometry.fromPointXY(centroid)) or feature.geometry().intersects(aoi_geom):
                    siruta = 26573
                    uat_name = "Oradea"
                    county = "Bihor"
                    
                    for field in uat_layer.fields():
                        f_name = field.name().lower()
                        if "siruta" in f_name or "cod" in f_name:
                            val = feature[field.name()]
                            if val is not None:
                                try:
                                    siruta = int(val)
                                except ValueError:
                                    pass
                        elif "name" in f_name or "uat" in f_name or "localit" in f_name or "denumire" in f_name:
                            val = feature[field.name()]
                            if val is not None:
                                uat_name = str(val)
                        elif "county" in f_name or "judet" in f_name or "județ" in f_name:
                            val = feature[field.name()]
                            if val is not None:
                                county = str(val)
                                
                    print(f"[StratumRO] UAT detectat dinamic: {uat_name} (SIRUTA: {siruta}), Județul: {county}")
                    return {
                        "siruta_code": siruta,
                        "level": "uat",
                        "name": uat_name,
                        "county": county
                    }
                    
        except Exception as e:
            print(f"[StratumRO] Eroare la detectarea administrativă dinamică: {str(e)}")
            
        return fallback_data

    def run_segmentation_pipeline(self):
        """Execută validările locale și lansează thread-ul de fundal către API-ul FastAPI."""
        
        # 1. Validare geometrică (Etapa 39)
        valid, msg = self.validate_aoi_geometry()
        if not valid:
            QtWidgets.QMessageBox.warning(self, "Validare Geometrie", msg)
            return

        self.lblStatus_2.setText("Status: Se pregătește cererea...")

        # Determinarea dinamică a datelor administrative (SIRUTA / UAT)
        admin_data = self.resolve_administrative_data()

        # Construirea payload-ului
        payload = {
            "project_name": "Segmentare_Nationala_StratumRO",
            "crs": "EPSG:31700",
            "aoi_selection_mode": "hybrid",
            "geometry": {
                "type": "Polygon",
                "coordinates": [self.current_aoi_geometry]
            },
            "administrative": admin_data,
            "parameters": {
                "model_version": "v1.0-default",
                "confidence_threshold": 0.5
            }
        }

        # Dezactivăm butonul pentru a preveni cereri multiple în paralel
        self.btnRunSegmentation.setEnabled(False)

        # 2. Inițierea firului de execuție asincron (Etapa 37, 38, 40)
        self.worker = SegmentationWorker(self.api_url, payload)
        self.worker.statusChanged.connect(self.on_worker_status_changed)
        self.worker.taskCompleted.connect(self.on_worker_task_completed)
        self.worker.taskFailed.connect(self.on_worker_task_failed)
        self.worker.start()

    def on_worker_status_changed(self, status_msg):
        """Actualizează eticheta de status din interfață cu mesajele trimise din thread."""
        self.lblStatus_2.setText(status_msg)

    def on_worker_task_completed(self, raster_path, vector_path):
        """Răspunsul la succes: reactivează butoanele și încarcă datele geospațiale în QGIS."""
        self.btnRunSegmentation.setEnabled(True)
        self.load_results_into_qgis(raster_path, vector_path)

    def on_worker_task_failed(self, error_message):
        """Tratarea erorilor prin pop-up QMessageBox (Etapa 38). Propune modul de Mock."""
        self.btnRunSegmentation.setEnabled(True)
        
        # Combinăm mesajul de eroare și întrebarea de Mock într-o singură fereastră
        msg_box = QtWidgets.QMessageBox(self)
        msg_box.setIcon(QtWidgets.QMessageBox.Critical)
        msg_box.setWindowTitle("Eroare Server MLOps")
        msg_box.setText(error_message)
        msg_box.setInformativeText("Dorești să pornești simularea locală (Mock) ca fallback?")
        msg_box.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        msg_box.setDefaultButton(QtWidgets.QMessageBox.No)
        
        reply = msg_box.exec_()
        if reply == QtWidgets.QMessageBox.Yes:
            self.execute_mock_polling()

    def execute_mock_polling(self):
        """Simulează asincron pașii din backend și declanșează încărcarea la final."""
        QtCore.QTimer.singleShot(2000, lambda: self.lblStatus_2.setText(
            "Status: [Task: queued]\nJob înregistrat în server. Coordonate mapate național."
        ))
        QtCore.QTimer.singleShot(4000, lambda: self.lblStatus_2.setText(
            "Status: [Task: processing - 45%]\nDescărcare date LAKI finalizată. Filtrare în curs..."
        ))
        
        # Calea relativă calculată din locația plugin-ului
        mock_raster = os.path.join(os.path.dirname(os.path.dirname(__file__)), "datasets", "orthophotos", "test_gdal_byte.tif")
        
        if not os.path.exists(mock_raster):
            QtCore.QTimer.singleShot(6000, lambda: self.lblStatus_2.setText(
                "Status: Fișier mock lipsă — plasează test_gdal_byte.tif în datasets/orthophotos/ relativ la workspace."
            ))
        else:
            QtCore.QTimer.singleShot(6000, lambda: self.load_results_into_qgis(raster_path=mock_raster))

    def load_results_into_qgis(self, raster_path=None, vector_path=None):
        """Etapa 36: Încarcă automat straturile (Raster și/sau Vector) rezultate direct în panoul de Layers din QGIS."""
        self.lblStatus_2.setText("Status: [Task: completed - 100%]\nSe încarcă straturile în QGIS...")
        
        # 1. Încărcare Strat Raster (Segmentare / Ortofoto / nDSM)
        raster_layer = None
        if raster_path and os.path.exists(raster_path):
            raster_layer = QgsRasterLayer(raster_path, "StratumRO_Raster_Rezultat", "gdal")
        else:
            url_placeholder = "type=xyz&url=https://tile.openstreetmap.org/{z}/{x}/{y}.png"
            raster_layer = QgsRasterLayer(url_placeholder, "StratumRO_Raster_Demo (WMS)", "wms")

        # 2. Încărcare Strat Vector (Amprente Clădiri - GeoPackage / Shapefile)
        vector_layer = None
        if vector_path and os.path.exists(vector_path):
            vector_layer = QgsVectorLayer(vector_path, "StratumRO_Clădiri_Vector", "ogr")

        # Adăugare în proiectul QGIS
        layers_added = []
        if raster_layer and raster_layer.isValid():
            QgsProject.instance().addMapLayer(raster_layer)
            layers_added.append("Raster")
            
        if vector_layer and vector_layer.isValid():
            QgsProject.instance().addMapLayer(vector_layer)
            layers_added.append("Vector")
            
        if layers_added:
            added_str = " + ".join(layers_added)
            self.lblStatus_2.setText(f"Status: [Task: completed - 100%]\nProcesare finalizată! S-au adăugat: {added_str}.")
        else:
            self.lblStatus_2.setText("Status: Eroare la încărcarea straturilor geospațiale rezultate.")

    def closeEvent(self, event):
        self.closingPlugin.emit()
        event.accept()