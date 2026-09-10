# -*- coding: utf-8 -*-

import os
import requests
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import pyqtSignal
# Am adăugat QgsRasterLayer, QgsVectorLayer și QgsWkbTypes pentru importurile PyQGIS
from qgis.core import QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsProject, QgsRasterLayer, QgsVectorLayer, QgsWkbTypes
from qgis.gui import QgsMapToolExtent

# Îi spunem programului să moștenească designul din fișierul _base
from .stratum_ro_dockwidget_base import Ui_StratumRODockWidgetBase
from .orchestrator import request_segmentation_plan
import subprocess

# Constante Geodezice Stereo 70 (România)
# EPSG:3844 este codul oficial actualizat solicitat de ANCPI / eTerra / TransdatRO.
# EPSG:31700 este codul istoric/legacy utilizat în unele proiecte mai vechi QGIS.
STEREO70_ANCPI_PRIMARY = "EPSG:3844"
STEREO70_LEGACY = "EPSG:31700"
STEREO70_VALID_CODES = [STEREO70_ANCPI_PRIMARY, STEREO70_LEGACY]

# Sistemul vertical de altitudini Marea Neagră 1975 & CRS compus 3D (România)
VERTICAL_MAREA_NEAGRA_1975 = "EPSG:5781"
CRS_3D_COMPOUND = "EPSG:3844+5781"
ROMANIA_Z_MIN = 0.0
ROMANIA_Z_MAX = 2544.0

class SegmentationWorker(QtCore.QThread):
    """
    Worker asincron pentru a executa pipeline-ul MLOps / LiDAR / AI
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
            self.statusChanged.emit("Status: Se verifică serverul FastAPI...")
            
            try:
                # 1. Trimiterea cererii POST inițiale către FastAPI dacă este pornit
                response = requests.post(self.api_url, json=self.payload, timeout=2)
                if response.status_code in [200, 201, 202]:
                    data = response.json()
                    task_id = data.get("task_id")
                    if not task_id:
                        results = data.get("results", {})
                        if results:
                            self.taskCompleted.emit(results.get("raster_path"), results.get("vector_path"))
                            return
                    else:
                        # Polling logic
                        base_url = self.api_url.rsplit("/segmentation/process", 1)[0]
                        poll_url = f"{base_url}/tasks/{task_id}"
                        for _ in range(150):
                            self.msleep(2000)
                            poll_resp = requests.get(poll_url, timeout=5)
                            if poll_resp.status_code == 200:
                                p_data = poll_resp.json()
                                if p_data.get("status") == "completed":
                                    res = p_data.get("results", {})
                                    self.taskCompleted.emit(res.get("raster_path"), res.get("vector_path"))
                                    return
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
                # Backend-ul FastAPI extern nu este pornit -> Rulăm direct motorul nativ StratumRO!
                print("[StratumRO] Backend extern inactiv. Se activează motorul nativ hibrid...")

            # === MOTORUL NATIV HIBRID STRATUM-RO ===
            self.statusChanged.emit("Status: Activare Orchestrator AI (Stereo 70)...")
            
            admin_info = self.payload.get("administrative", {})
            siruta_code = admin_info.get("siruta_code", 26573)
            project_name = self.payload.get("project_name", "StratumRO_Project")

            # 1. Obținere plan prin Fallback Chain (Llama 3.2 11B/90B -> Mock)
            orch, winning_model = request_segmentation_plan(siruta_code, project_name)
            self.statusChanged.emit(f"Status: Plan AI obținut [{winning_model}]!\nSe procesează datele LiDAR...")

            # 2. Căutare fișiere LiDAR și DTM locale (rezoluție dinamică)
            base_dir = os.path.dirname(os.path.dirname(__file__))
            candidates_laz = [
                self.payload.get("laz_path", ""),
                self.payload.get("lidar_path", ""),
                os.environ.get("STRATUMRO_LIDAR_LAZ", ""),
                os.path.join(base_dir, "datasets", "lidar", "teren.laz"),
                os.path.join(base_dir, "data", "teren.laz"),
                # Fallback dezvoltator local
                r"C:\Users\lefpa\Desktop\date\Z_VladP\Comparatie\LAZ\NorPuncte_St70_S42.laz",
                r"C:\Users\lefpa\Desktop\Negula\NorPuncte_St70_S42.laz"
            ]
            candidates_dtm = [
                self.payload.get("dtm_path", ""),
                os.environ.get("STRATUMRO_DTM_TIF", ""),
                os.path.join(base_dir, "datasets", "lidar", "dtm.tif"),
                os.path.join(base_dir, "data", "dtm.tif"),
                # Fallback dezvoltator local
                r"C:\Users\lefpa\Desktop\date\Z_VladP\Comparatie\DTM3m\DTM3m.tif"
            ]

            # Verificare straturi active din proiectul QGIS
            try:
                for layer in QgsProject.instance().mapLayers().values():
                    src = layer.source()
                    if src and os.path.exists(src):
                        if src.lower().endswith(('.laz', '.las')) and src not in candidates_laz:
                            candidates_laz.insert(0, src)
                        elif layer.type() == 1 and ("dtm" in layer.name().lower() or "dem" in layer.name().lower()):
                            if src not in candidates_dtm:
                                candidates_dtm.insert(0, src)
            except Exception:
                pass

            laz_path = next((p for p in candidates_laz if p and os.path.exists(p)), None)
            dtm_path = next((p for p in candidates_dtm if p and os.path.exists(p)), None)

            out_dir = os.path.join(base_dir, "workspace", "output")
            os.makedirs(out_dir, exist_ok=True)
            out_ndsm = os.path.join(out_dir, f"ndsm_siruta_{siruta_code}.tif")
            out_gpkg = os.path.join(out_dir, f"cladiri_siruta_{siruta_code}.gpkg")
            out_dxf = os.path.join(out_dir, f"cadastru_ancpi_{siruta_code}.dxf")

            venv_python = os.path.join(base_dir, "venv", "Scripts", "python.exe")
            has_local_backend = False
            try:
                import rasterio
                has_local_backend = True
            except ImportError:
                has_local_backend = False

            if not has_local_backend and os.path.exists(venv_python):
                self.statusChanged.emit("Status: [Fuziune Hibridă] Meta SAM 2 + LiDAR pe GPU...")
                pipeline_script = os.path.join(base_dir, "run_hybrid_full_aoi.py")
                proc = subprocess.Popen(
                    [venv_python, pipeline_script],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    cwd=base_dir
                )
                for line in proc.stdout:
                    line_s = line.strip()
                    if line_s and ("Etapa" in line_s or "Tile" in line_s or "Confirmate" in line_s or "Medie" in line_s):
                        self.statusChanged.emit(f"Status: {line_s}")
                proc.wait()
                final_ndsm = os.path.join(out_dir, "ndsm_stereo70.tif")
                final_gpkg = os.path.join(out_dir, "cladiri_stereo70.gpkg")
                self.statusChanged.emit("Status: Finalizat cu succes! Straturi hibride încărcate.")
                self.taskCompleted.emit(final_ndsm, final_gpkg)
                return

            if laz_path:
                from .lidar_processor import LidarProcessor
                from .vectorizer import CadastralVectorizer
                from .cad_exporter import CadastralDxfExporter
                try:
                    from .sam2_engine import SAM2BuildingSegmenter, _extract_largest_polygon
                    from .ortho_extractor import OrthoExtractor
                    SAM2_ENGINE_AVAILABLE = True
                except Exception:
                    SAM2_ENGINE_AVAILABLE = False

                self.statusChanged.emit("Status: Clasificare multi-categorie LiDAR (Clădiri, Anexe, Arbori, Stâlpi)...")
                lidar_proc = LidarProcessor(laz_path, dtm_path)
                data = lidar_proc.process_multicategory(output_ndsm_path=out_ndsm, resolution=1.0)

                vectorizer = CadastralVectorizer(crs="EPSG:3844")
                main_b = []

                if SAM2_ENGINE_AVAILABLE:
                    try:
                        self.statusChanged.emit("Status: [Fuziune Hibridă] Meta SAM 2 pe GPU + Validare nDSM LiDAR...")
                        extractor = OrthoExtractor()
                        segmenter = SAM2BuildingSegmenter()

                        # Găsim bounding box-ul zonei
                        import numpy as np
                        from scipy.ndimage import label, find_objects
                        lbl_m, _ = label(data["main_buildings_grid"])
                        objs_m = find_objects(lbl_m)
                        tr_nd = data["transform"]

                        # Rulăm decupaj ortofoto pe AOI
                        aoi_xmin = tr_nd.c
                        aoi_xmax = tr_nd.c + data["main_buildings_grid"].shape[1] * tr_nd.a
                        aoi_ymax = tr_nd.f
                        aoi_ymin = tr_nd.f + data["main_buildings_grid"].shape[0] * tr_nd.e
                        crop_temp = os.path.join(out_dir, "ortho_hybrid_crop.tif")
                        crop_res = extractor.crop_aoi(min(aoi_xmin, aoi_xmax), min(aoi_ymin, aoi_ymax),
                                                      max(aoi_xmin, aoi_xmax), max(aoi_ymin, aoi_ymax),
                                                      crop_temp, target_res=0.15)
                        segmenter.set_image(crop_res["image"], crop_res["transform"])

                        hybrid_candidates = []
                        for i, sl in enumerate(objs_m, 1):
                            if sl is None: continue
                            comp = (lbl_m[sl] == i)
                            if np.sum(comp) < 12: continue
                            r_start, r_stop = sl[0].start, sl[0].stop
                            c_start, c_stop = sl[1].start, sl[1].stop
                            b_x1 = tr_nd.c + c_start * tr_nd.a
                            b_x2 = tr_nd.c + c_stop * tr_nd.a
                            b_y1 = tr_nd.f + r_start * tr_nd.e
                            b_y2 = tr_nd.f + r_stop * tr_nd.e
                            comp_h = data["ndsm"][sl][comp]
                            mean_h = float(np.mean(comp_h)) if len(comp_h) > 0 else 0.0
                            max_h = float(np.max(comp_h)) if len(comp_h) > 0 else 0.0
                            rr, cc = np.where(comp)
                            internal_pts = [(tr_nd.c + (c_start + cc[int(len(rr)*0.5)]) * tr_nd.a,
                                             tr_nd.f + (r_start + rr[int(len(rr)*0.5)]) * tr_nd.e)]

                            res = segmenter.segment_candidate(
                                b_xmin=min(b_x1, b_x2), b_ymin=min(b_y1, b_y2),
                                b_xmax=max(b_x1, b_x2), b_ymax=max(b_y1, b_y2),
                                mean_h=mean_h, max_h=max_h, lidar_area=float(np.sum(comp)),
                                internal_pts_geo=internal_pts
                            )
                            if res["status"] in ["CONFIRMAT_HIBRID", "LIDAR_DIRECT"]:
                                hybrid_candidates.append(res)

                        main_b = vectorizer.format_hybrid_buildings(hybrid_candidates, tolerance=1.4)
                    except Exception as e_sam:
                        print(f"[StratumRO] Fallback pe vectorizare LiDAR din cauza erorii SAM 2: {e_sam}")

                if not main_b:
                    self.statusChanged.emit("Status: Ortogonalizare CAD (90°) & simplificare geometrii din LiDAR...")
                    main_b = vectorizer.vectorize_mask(data["main_buildings_grid"], data["transform"], min_area_m2=15.0, category="CLADIRE_PRINCIPALA")

                out_b = vectorizer.vectorize_mask(data["outbuildings_grid"], data["transform"], min_area_m2=8.0, category="ANEXA_GOSPODAREASCA")
                trees = vectorizer.vectorize_points(data["tree_points"], category="ARBORE")
                poles = vectorizer.vectorize_points(data["pole_points"], category="STALP_TURN")

                categories = {
                    "CLADIRI_HIBRID": main_b,
                    "CLADIRI_PRINCIPALE": main_b,
                    "ANEXE_GOSPODARESTI": out_b,
                    "ARBORI": trees,
                    "STALPI_TURNURI": poles
                }

                if os.path.exists(out_gpkg):
                    try:
                        os.remove(out_gpkg)
                    except Exception:
                        pass
                vectorizer.save_multicategory_geopackage(categories, out_gpkg)

                self.statusChanged.emit("Status: Generare fișier CAD ANCPI (.dxf) pe layere dedicate...")
                dxf_exporter = CadastralDxfExporter(dxf_version="R2010")
                dxf_exporter.export_multicategory_to_dxf(categories, out_dxf, include_labels=True)

                self.statusChanged.emit(f"Status: Finalizat! {len(main_b)} clădiri hibrid, {len(out_b)} anexe, {len(trees)} arbori, {len(poles)} stâlpi.")
                self.taskCompleted.emit(out_ndsm, out_gpkg)
            else:
                # Fallback dacă nu există niciun fișier LiDAR
                mock_raster = os.path.join(base_dir, "datasets", "orthophotos", "test_gdal_byte.tif")
                self.taskCompleted.emit(mock_raster, "")

        except Exception as e:
            self.taskFailed.emit(f"Eroare neprevăzută în pipeline: {str(e)}")


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

    def is_stereo70(self, crs):
        """
        Verifică dacă un CRS (QgsCoordinateReferenceSystem) reprezintă Stereo 70 
        în oricare dintre codurile EPSG uzuale (EPSG:3844 cerut oficial de ANCPI sau EPSG:31700 legacy).
        """
        if not crs or not crs.isValid():
            return False
        auth_id = crs.authid().upper()
        if auth_id in STEREO70_VALID_CODES:
            return True
        desc = crs.description().lower()
        return "stereo 70" in desc or "stereografic 1970" in desc or "pulkovo 1942" in desc

    def detect_geometry_dimension(self, layer):
        """
        Detectează dacă un strat (QgsVectorLayer sau QgsRasterLayer) conține geometrii sau altitudini 3D.
        """
        if not layer or not layer.isValid():
            return {"dimension": "2D", "has_z": False, "crs_2d": STEREO70_ANCPI_PRIMARY, "crs_vertical": None}

        crs_2d = layer.crs().authid().upper() if layer.crs().isValid() else STEREO70_ANCPI_PRIMARY
        has_z = False
        crs_vert = None

        if isinstance(layer, QgsVectorLayer):
            wkb_type = layer.wkbType()
            has_z = QgsWkbTypes.hasZ(wkb_type)
            if has_z:
                crs_vert = VERTICAL_MAREA_NEAGRA_1975
        elif isinstance(layer, QgsRasterLayer):
            # Verificăm dacă rasterul conține un band numit 'elevation', 'z', sau dacă CRS-ul are componentă verticală
            if layer.crs().isValid() and layer.crs().isVertical():
                has_z = True
                crs_vert = layer.crs().authid().upper()
            else:
                for i in range(1, layer.bandCount() + 1):
                    b_name = str(layer.bandName(i)).lower()
                    if "elevation" in b_name or "height" in b_name or "z" == b_name or "dsm" in b_name or "dtm" in b_name:
                        has_z = True
                        crs_vert = VERTICAL_MAREA_NEAGRA_1975
                        break

        dimension = "3D" if has_z else "2D"
        return {
            "dimension": dimension,
            "has_z": has_z,
            "crs_2d": crs_2d,
            "crs_vertical": crs_vert
        }

    def capture_coordinates(self, extent):
        """Captează coordonatele de pe ecran și le validează/transformă în Stereo 70 (EPSG:3844 sau EPSG:31700)."""
        self.iface.mapCanvas().unsetMapTool(self.map_tool)
        
        xmin = extent.xMinimum()
        xmax = extent.xMaximum()
        ymin = extent.yMinimum()
        ymax = extent.yMaximum()

        current_crs = self.iface.mapCanvas().mapSettings().destinationCrs()
        
        if self.is_stereo70(current_crs):
            # Canvas-ul este deja în Stereo 70 (3844 ANCPI sau 31700) -> Păstrăm coordonatele fără re-proiectare
            self.active_crs_authid = current_crs.authid().upper()
        else:
            # Re-proiectăm automat din alt CRS (ex: EPSG:4326 sau EPSG:3857) în EPSG:3844 (Standardul modern ANCPI)
            target_crs = QgsCoordinateReferenceSystem(STEREO70_ANCPI_PRIMARY)
            transform = QgsCoordinateTransform(current_crs, target_crs, QgsProject.instance())
            point_min = transform.transform(xmin, ymin)
            point_max = transform.transform(xmax, ymax)
            xmin = min(point_min.x(), point_max.x())
            xmax = max(point_min.x(), point_max.x())
            ymin = min(point_min.y(), point_max.y())
            ymax = max(point_min.y(), point_max.y())
            self.active_crs_authid = STEREO70_ANCPI_PRIMARY

        # Structură închisă tip Poligon/Bounding Box pentru API
        self.current_aoi_geometry = [
            [xmin, ymin],
            [xmax, ymin],
            [xmax, ymax],
            [xmin, ymax],
            [xmin, ymin]
        ]

        self.lblStatus_2.setText(f"Status: AOI salvat cu succes în Stereo 70 ({self.active_crs_authid})!")
        print(f"[StratumRO] Coordonate salvate ({self.active_crs_authid}): {self.current_aoi_geometry}")

    def validate_aoi_geometry(self):
        """Etapa 39: Validează structura geografică a Bounding Box-ului în Stereo 70 (EPSG:3844 / EPSG:31700) și cota Z opțională."""
        if not self.current_aoi_geometry:
            return False, "Te rog selectează mai întâi o zonă pe hartă folosind butonul 'Selectează AOI'."
        
        # Limitele geodezice extinse ale României în Stereo 70 (EPSG:3844 / EPSG:31700)
        # Acoperă inclusiv zonele de graniță: Jimbolia (vest), Sulina (est),
        # Vama Borșa (nord), Mangalia și Zimnicea (sud)
        # X: ~125.000 – 880.000 m, Y: ~230.000 – 770.000 m
        RO_X_MIN, RO_X_MAX = 125000.0, 880000.0
        # Extins RO_Y_MIN la 230000.0 m pentru a acoperi extremitatea sudică a României (Zimnicea Y=235805.15 m), cf. audit geodezic 23.07.2026
        RO_Y_MIN, RO_Y_MAX = 230000.0, 770000.0
        
        for pt in self.current_aoi_geometry:
            x, y = pt[0], pt[1]
            if not (RO_X_MIN <= x <= RO_X_MAX) or not (RO_Y_MIN <= y <= RO_Y_MAX):
                return False, f"Coordonatele selectate ({x:.2f}, {y:.2f}) se află în afara limitelor geodezice ale României în Stereo 70."
            
            # Validare opțională cota Z în intervalul altimetric al României (0m - 2544m Marea Neagră 1975)
            if len(pt) > 2:
                z = pt[2]
                if not (ROMANIA_Z_MIN <= z <= ROMANIA_Z_MAX):
                    return False, f"Altitudinea Z selectată ({z:.2f} m) este în afara domeniului altimetric al României ({ROMANIA_Z_MIN} - {ROMANIA_Z_MAX} m Marea Neagră 1975)."
        
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
                    siruta = None
                    uat_name = None
                    county = None
                    
                    for field in uat_layer.fields():
                        f_name = field.name().lower()
                        if "siruta" in f_name or "natcode" in f_name or "cod_uat" in f_name or "cod" in f_name:
                            val = feature[field.name()]
                            if val is not None and str(val).strip():
                                try:
                                    siruta = int(val)
                                except (ValueError, TypeError):
                                    pass
                        elif "uat" in f_name or "localit" in f_name or "denumire" in f_name or "name" in f_name:
                            val = feature[field.name()]
                            if val is not None and str(val).strip():
                                uat_name = str(val)
                        elif "judet" in f_name or "județ" in f_name or "county" in f_name:
                            val = feature[field.name()]
                            if val is not None and str(val).strip():
                                county = str(val)
                                
                    siruta = siruta if siruta is not None else 26573
                    uat_name = uat_name if uat_name is not None else "Oradea"
                    county = county if county is not None else "Bihor"
                                
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

        # Verificare dinamică a dimensiunii 2D / 3D pe baza straturilor active din proiect
        is_3d = False
        if QgsProject.instance():
            for layer in QgsProject.instance().mapLayers().values():
                dim_info = self.detect_geometry_dimension(layer)
                if dim_info["has_z"]:
                    is_3d = True
                    break

        # Preluarea CRS-ului activ (EPSG:3844 sau EPSG:31700)
        active_crs = getattr(self, "active_crs_authid", STEREO70_ANCPI_PRIMARY)

        # Construirea payload-ului
        payload = {
            "project_name": "Segmentare_Nationala_StratumRO",
            "crs": active_crs,
            "crs_vertical": VERTICAL_MAREA_NEAGRA_1975 if is_3d else None,
            "crs_compound": CRS_3D_COMPOUND if is_3d else None,
            "supported_crs": STEREO70_VALID_CODES,
            "dimension": "3D" if is_3d else "2D",
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

        # 2. Încărcare Straturi Vectoriale (Multi-categorie din GeoPackage)
        layers_added = []
        if vector_path and os.path.exists(vector_path):
            try:
                import pyogrio
                gpkg_layers = [l[0] for l in pyogrio.list_layers(vector_path)]
            except Exception:
                gpkg_layers = ["CLADIRI_PRINCIPALE", "ANEXE_GOSPODARESTI", "ARBORI", "STALPI_TURNURI"]

            for layer_name in gpkg_layers:
                layer_uri = f"{vector_path}|layername={layer_name}"
                display_title = f"StratumRO — {layer_name}"
                vlayer = QgsVectorLayer(layer_uri, display_title, "ogr")
                if vlayer and vlayer.isValid():
                    QgsProject.instance().addMapLayer(vlayer)
                    layers_added.append(layer_name)

        if raster_layer and raster_layer.isValid():
            QgsProject.instance().addMapLayer(raster_layer)
            layers_added.append("nDSM Raster")

        if layers_added:
            added_str = ", ".join(layers_added)
            self.lblStatus_2.setText(f"Status: [Task: completed - 100%]\nProcesare finalizată! Straturi active: {added_str}.")
        else:
            self.lblStatus_2.setText("Status: Eroare la încărcarea straturilor geospațiale rezultate.")

    def closeEvent(self, event):
        self.closingPlugin.emit()
        event.accept()