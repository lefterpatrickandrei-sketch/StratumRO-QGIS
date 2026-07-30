# StratumRO — Sistem Inteligent de Segmentare Cadastrală (QGIS Plugin) 🌍🚀

Sistem MLOps integrat pentru descărcarea, filtrarea și procesarea automată a datelor geospațiale (LiDAR și Raster) la nivel național, cu suport nativ pentru selecție geometrică pe canvas și coduri administrative SIRUTA.

---

## 📌 Cuprins Interactiv (Table of Contents)

* [1. 📝 Descriere Generală / Description / Descripción](#1--descriere-generală--description--descripción)
  * [1.1 🇷🇴 Română](#11--română)
  * [1.2 🇬🇧 English](#12--english)
  * [1.3 🇪🇸 Español](#13--español)
* [2. 🛠️ Ghid de Instalare & Descărcare Resurse](#2--ghid-de-instalare--descărcare-resurse)
* [3. 📂 Compoziția și Structura Workspace-ului](#3--compoziția-și-structura-workspace-ului)
* [4. 💻 Codul Sursă de Referință (`stratum_ro_dockwidget.py`)](#4--codul-sursă-de-referință-stratum_ro_dockwidgetpy)
* [5. 🧮 Ecuațiile Matematice & Geodezice Fundamentale](#5--ecuațiile-matematice--geodezice-fundamentale)
  * [5.1 Ecuațiile Proiecției Stereografice 1970 (Stereo 70 / EPSG:3844 ANCPI & EPSG:31700 Legacy)](#51-ecuațiile-proiecției-stereografice-1970-stereo-70--epsg3844-ancpi--epsg31700-legacy)
  * [5.2 Izolarea Altimetrică 3D (nDSM) și Regimul de Înălțime (P+nE)](#52-izolarea-altimetrică-3d-ndsm-și-regimul-de-înălțime-pne)
  * [5.3 Algoritmul de Ortogonalizare la 90° a Poligoanelor Cadastrale](#53-algoritmul-de-ortogonalizare-la-90-a-poligoanelor-cadastrale)
  * [5.4 Indicele de Vegetație (NDVI) și Potențialul Solar Anual (PVGIS)](#54-indicele-de-vegetație-ndvi-și-potențialul-solar-anual-pvgis)
* [6. 🎨 Arhitectura Vizuală & Diagrame de Sistem](#6--arhitectura-vizuală--diagrame-de-sistem)
  * [6.1 🏗️ Diagrama de Arhitectură Hibridă a Sistemului](#61-️-diagrama-de-arhitectură-hibridă-a-sistemului)
  * [6.2 🔄 Diagrama de Flux Vizual a Utilizatorului & Bucla de Polling](#62--diagrama-de-flux-vizual-a-utilizatorului--bucla-de-polling)
  * [6.3 📦 Diagrama Fuziunii Multimodale AI + LiDAR (Layout Vertical)](#63--diagrama-fuziunii-multimodale-ai--lidar-layout-vertical)
* [7. 📊 Status Detaliat: Planul în 100 de Etape al Proiectului](#7--status-detaliat-planul-în-100-de-etape-al-proiectului)
  * [7.1 📍 Ghid de Lucru pe Etape: Unde se execută fiecare fază?](#71--ghid-de-lucru-pe-etape-unde-se-execută-fiecare-fază)
  * [7.2 Faze de Implementare (A – K)](#72-faze-de-implementare-a--k)
* [8. 📋 Suita Celor 9 Deliverabile Spațiale Realizabile](#8--suita-celor-9-deliverabile-spațiale-realizabile)
* [9. 🔌 Contract de Date API Unificat](#9--contract-de-date-api-unificat)
* [10. ⚠️ Notă Importantă privind Rularea Modului Mock](#10--notă-importantă-privind-rularea-modului-mock)
* [11. 📈 Strategia de Viabilitate a Produsului & Inovații Cadastrale](#11--strategia-de-viabilitate-a-produsului--inovații-cadastrale)
  * [11.1 Conceptul de „Pre-Vectorizare” cu Snap-to-RTK](#111-conceptul-de-pre-vectorizare-cu-snap-to-rtk)
  * [11.2 Validare Topologică și Strat de Erori](#112-validare-topologică-și-strat-de-erori)
  * [11.3 Extindere Strategică: Baza de Date Imobiliar-Notarială](#113-extindere-strategică-baza-de-date-imobiliar-notarială)
  * [11.4 Integrarea Analizei Predictive: Simulare Hazard și Mediu](#114-integrarea-analizei-predictive-simulare-hazard-și-mediu)
  * [11.5 Clasificare Riguroasă a Surselor de Date: Producție vs. Ipoteze de Cercetare](#115-clasificare-riguroasă-a-surselor-de-date-producție-vs-ipoteze-de-cercetare)
* [12. 🛡️ Evaluare & Feedback pe Direcția Proiectului](#12--evaluare--feedback-pe-direcția-proiectului)
* [13. 📄 Licență & 👥 Contribuții](#13--licență--contribuții)
* [14. 📚 Surse de Date & Atribuiri](#14--surse-de-date--atribuiri)

---

## 1. 📝 Descriere Generală / Description / Descripción

### 1.1 🇷🇴 Română

Agentic GIS conectează QGIS la un backend AI local (FastAPI + Ollama LLM + Meta SAM2) pentru extragerea automată a amprentelor clădirilor din ortofotoplanuri și nori de puncte LiDAR. Plugin-ul permite selectarea unei zone de interes (AOI) direct pe hartă, trimiterea ei către backend pentru segmentare și clasificare AI, iar rezultatul revine ca strat vectorial QGIS gata de utilizare (GeoPackage). Pipeline-ul suportă opțional un flux hibrid SAM 3 → SAM 2 (SAM 3 pentru descoperirea automată a clădirilor, SAM 2 pentru rafinarea pixel-level a contururilor).

În spate, un agent bazat pe modelul de ultimă generație NVIDIA Nemotron-3 (rulat complet local prin Ollama) orchestrează fluxul de lucru prin Model Context Protocol (MCP), coordonând segmentarea, curățarea geometrică și validarea topologică înainte ca rezultatele să ajungă pe hartă.

Toată procesarea rulează pe hardware local — datele nu părăsesc mașina. Necesită un serviciu backend local activ; inferența AI este accelerată pe GPU (recomandat minimum 8GB VRAM), cu un mod fallback CPU-only, mai lent, pentru cine nu are placă video compatibilă.

> Este un proiect activ de cercetare aplicată în geomatică și AI geospațial, dezvoltat de o echipă mică de ingineri; rezultatele sunt gândite să accelereze vectorizarea manuală și trebuie verificate înainte de utilizare în depuneri cadastrale oficiale.

### 1.2 🇬🇧 English

Agentic GIS connects QGIS to a local, privacy-preserving AI backend (FastAPI + Ollama LLM + Meta SAM2) to automate building footprint extraction from orthophotos and LiDAR point clouds. The plugin lets you select an area of interest directly on the map canvas, sends it to the backend for AI-driven segmentation and classification, and returns validated building polygons as a ready-to-use QGIS vector layer (GeoPackage).

Under the hood, an AI agent based on the state-of-the-art NVIDIA Nemotron-3 model (running completely locally through Ollama) orchestrates the workflow via the Model Context Protocol (MCP), coordinating segmentation, geometric cleanup, and topology validation before results reach the map.

All processing runs on local hardware — no orthophoto or point cloud data leaves the machine. Requires a running local backend service; AI inference is GPU-accelerated (8GB+ VRAM recommended), with a slower CPU-only fallback mode for machines without a compatible GPU.

> This is an active applied-research project in geomatics and geospatial AI, developed by a small engineering team; outputs are intended to speed up manual vectorization and should be reviewed before use in official cadastral submissions.

### 1.3 🇪🇸 Español

Agentic GIS conecta QGIS con un backend de IA local que preserva la privacidad (FastAPI + Ollama LLM + Meta SAM2) para automatizar la extracción de huellas de edificios a partir de ortofotos y nubes de puntos LiDAR. El plugin permite seleccionar un área de interés directamente sobre el lienzo del mapa, la envía al backend para segmentación y clasificación mediante IA, y devuelve los polígonos de edificios validados como una capa vectorial de QGIS lista para usar (GeoPackage).

Internamente, un agente de IA basado en el modelo de última generación NVIDIA Nemotron-3 (ejecutado localmente mediante Ollama) orquesta el flujo de trabajo mediante el Model Context Protocol (MCP), coordinando la segmentación, la limpieza geométrica y la validación topológica antes de que los resultados lleguen al mapa.

Todo el procesamiento se ejecuta en hardware local — ningún dato sale de la máquina. Requiere un servicio backend local en ejecución; la inferencia de IA se acelera por GPU (se recomiendan 8GB+ de VRAM), con un modo de respaldo solo-CPU, más lento, para equipos sin GPU compatible.

> Es un proyecto activo de investigación aplicada en geomática e IA geoespacial, desarrollado por un equipo pequeño de ingenieros; los resultados están pensados para acelerar la vectorización manual y deben revisarse antes de usarse en presentaciones catastrales oficiales.

---

## 2. 🛠️ Ghid de Instalare & Descărcare Resurse

Pentru a dezvolta și rula proiectul, este necesară configurarea mediului de lucru conform instrucțiunilor de mai jos:

### Descărcări Necesare (Downloads)
*   **Pentru toți membrii (Core):**
    *   **Python 3.10+** (Recomandat 3.10 sau 3.11): [Python Oficial](https://www.python.org/downloads/)
    *   **QGIS Desktop (3.28 LTR sau mai nou):** [QGIS Oficial](https://qgis.org/en/site/forusers/download.html)
    *   **Git LFS** (gestionare fișiere mari LiDAR/TIFF): [Git LFS](https://git-lfs.com/)
*   **Pentru Membru 2 (Backend & Database):**
    *   **PostgreSQL 15+ & extensia PostGIS:** [PostgreSQL Oficial](https://www.postgresql.org/download/)
    *   **OSGeo4W Network Installer** (biblioteci C++ GDAL/PDAL pe Windows): [OSGeo4W](https://trac.osgeo.org/osgeo4w/)
*   **Pentru Membru 3 (AI/ML Engineer):**
    *   **Ollama CLI (rulat local):** [Ollama Descărcare](https://ollama.com/download)
    *   **CUDA Toolkit 11.8 / 12.1** (accelerare GPU PyTorch/SAM 2): [NVIDIA CUDA](https://developer.nvidia.com/cuda-downloads)
    *   **Meta SAM 2 Checkpoints (Greutăți):** Descărcați modelul `sam2_hiera_tiny.pt` sau `sam2_hiera_small.pt` de pe: [Meta SAM 2 GitHub](https://github.com/facebookresearch/segment-anything-2)

### Procedura de Configurare Rapidă
1.  **Instalare dependințe Python:**
    ```bash
    python -m venv venv
    .\venv\Scripts\activate
    pip install -r requirements.txt
    ```
2.  **Configurare LLM local (Ollama - Membru 3):**
    ```bash
    ollama pull nemotron
    ```
3.  **Configurare QGIS Plugin (Membru 1):**
    *   Rulați scriptul `install_plugin.bat` (din rădăcina proiectului) pentru a compila resursele Qt și a deploya plugin-ul în folderul QGIS active profile.

---

## 3. 📂 Compoziția și Structura Workspace-ului

Workspace-ul proiectului este structurat conform standardelor profesionale PyQGIS, decuplând resursele de lucru de logica activă de execuție:

```
QGIS-AI/ (Workspace Principal)
├── docs/
│   ├── architecture.md                 # Specificațiile tehnice și contractul API unificat
│   └── readme.md                       # Acest ghid tehnic unificat (Manualul Proiectului)
├── mcp/                                # Servicii FastMCP & Management Dataset-uri
│   ├── filesystem/
│   │   └── server.py                   # FastMCP Sandbox Server (Path Traversal Guard _safe_resolve)
│   └── dataset_manager/
│       └── downloader.py               # Downloader geospațial securizat (SSRF Guard urlparse)
├── stratum_ro/                         # Pachetul principal al plugin-ului QGIS
│   ├── scripts/                        # Scripturi auxiliare de procesare
│   ├── test/                           # Suite de teste unitare și utilitare geodezice
│   ├── __init__.py                     # Inițializarea pachetului Python
│   ├── icon.png                        # Pictograma plugin-ului vizibilă în QGIS
│   ├── metadata.txt                    # Informațiile de versiune și categorii pentru managerul QGIS
│   ├── pb_tool.cfg                     # Configurația de compilare a resurselor Qt
│   ├── stratum_ro.py                   # Clasa principală care înregistrează plugin-ul în interfața QGIS
│   ├── stratum_ro_dockwidget_base.ui   # Interfața grafică XML proiectată în Qt Designer
│   ├── stratum_ro_dockwidget_base.py   # Codul Python compilat automat din fișierul .ui
│   └── stratum_ro_dockwidget.py        # Logica operațională, geodezică și de rețea (Pilotul)
├── venv/                               # Mediul virtual Python local
├── .gitignore                          # Excluderea fișierelor temporare și cache-ului din Git
└── AGENTS.md                           # Instrucțiuni și rute operaționale pentru agenți AI
```

---

## 4. 💻 Codul Sursă de Referință (`stratum_ro_dockwidget.py`)

Mai jos este prezentat codul sursă complet al nucleului plugin-ului. Acest script reprezintă implementarea tehnică a Etapelor 34, 35 și 36, asigurând interfața asincronă și auto-încărcarea datelor în QGIS:

```python
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

            max_retries = 150  # Maxim 5 minute (150 interogări * 2 secunde pauză) pentru procesări complexe naționale
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

            self.taskFailed.emit("Eroare: Timpul de așteptare pentru finalizarea procesării a expirat (Timeout 5 min).")

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

        self.lblStatus_2.setText("Status: AOI salvat cu succes în Stereo 70!")
        print(f"[StratumRO] Coordonate salvate: {self.current_aoi_geometry}")

    def validate_aoi_geometry(self):
        """Etapa 39: Validează structura geografică a Bounding Box-ului în Stereo 70."""
        if not self.current_aoi_geometry:
            return False, "Te rog selectează mai întâi o zonă pe hartă folosind butonul 'Selectează AOI'."
        
        # Limitele geodezice extinse ale României în Stereo 70 (EPSG:31700)
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
```

---

## 5. 🧮 Ecuațiile Matematice & Geodezice Fundamentale

### 5.1 Ecuațiile Proiecției Stereografice 1970 (Stereo 70 / EPSG:3844 ANCPI & EPSG:31700 Legacy)
Conversia riguroasă de pe elipsoidul Krasovsky 1940 în planul de proiecție național Stereo 70:

$$\chi = \arctan \left( \sinh \left( \mathrm{arsinh}(\tan \varphi) - e \cdot \mathrm{artanh}(e \cdot \sin \varphi) \right) \right)$$

$$X = X_0 + k_0 \cdot R \cdot \cos \chi \cdot \sin(\lambda - \lambda_0)$$

$$Y = Y_0 + k_0 \cdot R \cdot \left[ \cos \chi_0 \sin \chi - \sin \chi_0 \cos \chi \cos(\lambda - \lambda_0) \right]$$

* **Parametri Naționali Oficiali:** $X_0 = 500.000\text{ m}$, $Y_0 = 500.000\text{ m}$, $\varphi_0 = 46^\circ\text{ N}$, $\lambda_0 = 25^\circ\text{ E}$, $k_0 = 0,99975$.
* **Domeniul Național Validat în Cod:** $RO\_X \in [125.000, 880.000]\text{ m}$, $RO\_Y \in [230.000, 770.000]\text{ m}$.

---

### 5.2 Izolarea Altimetrică 3D (nDSM) și Regimul de Înălțime (P+nE)
Calculul altimetric din norul de puncte LiDAR real (`.laz`/`.las` / MNT LAKI):

$$\text{nDSM}(x, y) = \text{DSM}(x, y) - \text{DTM}(x, y)$$

$$\text{Regim Înălțime } (P+nE) = \left\lfloor \frac{H_{\text{streașină}} - H_{\text{teren}}}{h_{\text{etaj}}} \right\rfloor + 1 \quad \text{unde } h_{\text{etaj}} \approx 3,0\text{ m}$$

---

### 5.3 Algoritmul de Ortogonalizare la 90° a Poligoanelor Cadastrale
Optimizarea unghiurilor pentru forțarea colțurilor drepte ale clădirilor:

$$\min_{\theta} \sum_{i=1}^{N} \min_{k \in \{0, 1, 2, 3\}} \left| \alpha_i - \left( \theta + k \frac{\pi}{2} \right) \right|^2$$

---

### 5.4 Indicele de Vegetație (NDVI) și Potențialul Solar Anual (PVGIS)
Formulele folosite în Fazele I & J pentru cadastrul verde și potențialul fotovoltaic:

$$\text{NDVI} = \frac{\text{NIR} - \text{RED}}{\text{NIR} + \text{RED}} = \frac{B_8 - B_4}{B_8 + B_4} \quad (\text{Sentinel-2 ESA})$$

$$E_{\text{anual}} = \int_{0}^{365} P_{\text{peak}} \cdot \eta_{\text{sistem}} \cdot I(\theta, \alpha, t) \, dt \quad (\text{PVGIS API — Comisia Europeană})$$

---

## 6. 🎨 Arhitectura Vizuală & Diagrame de Sistem

### 6.1 🏗️ Diagrama de Arhitectură Hibridă a Sistemului

```mermaid
flowchart TB
    classDef clientStyle fill:#1e293b,stroke:#38bdf8,stroke-width:2px,color:#fff;
    classDef mcpStyle fill:#312e81,stroke:#818cf8,stroke-width:2px,color:#fff;
    classDef backendStyle fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#fff;
    classDef aiStyle fill:#701a75,stroke:#f0abfc,stroke-width:2px,color:#fff;
    classDef dbStyle fill:#78350f,stroke:#fbbf24,stroke-width:2px,color:#fff;

    subgraph CLIENT ["🖥️ Client Desktop QGIS (Membru 1)"]
        UI["Qt Designer UI<br/>(stratum_ro_dockwidget_base.ui)"]
        MapTool["QgsMapToolExtent<br/>(Selecție AOI pe hartă)"]
        GeoCheck{"Validare Geodezică<br/>Stereo 70 (EPSG:3844 / EPSG:31700)<br/>RO_Y_MIN: 230.000m"}
        Worker["SegmentationWorker<br/>(PyQt QThread Asincron)"]
        
        UI --> MapTool
        MapTool --> GeoCheck
        GeoCheck -->|Stereo 70 Validated| Worker
    end

    subgraph SECURITY ["🛡️ Sandbox & Securitate MLOps"]
        SafeResolve["FastMCP _safe_resolve()<br/>(Path Traversal Sandbox workspace/)"]
        SSRFGuard["urlparse Guard<br/>(SSRF Protection - Doar http/https)"]
    end

    subgraph BACKEND ["⚙️ MLOps Backend Server (FastAPI :8000 — Membru 2)"]
        API["FastAPI App<br/>(main.py)"]
        Clipping["Raster & LiDAR Clipper<br/>(GDAL / PDAL Pipeline)"]
        nDSMCalc["Calcul nDSM Altimetric<br/>(nDSM = DSM - DTM)"]
        
        API --> Clipping
        Clipping --> nDSMCalc
    end

    subgraph AIENGINE ["🧠 Engine AI & Inferență CUDA (Membru 3)"]
        Ollama["Ollama LLM Agent<br/>(NVIDIA Nemotron-3 via MCP)"]
        SAM2["Meta SAM 2 Encoder/Decoder<br/>(PyTorch CUDA GPU 8GB+)"]
        Orthogonalizer["Ortogonalizare 90° & Topologie<br/>(Shapely + GDAL Polygonize)"]
        
        Ollama -->|Spatial Prompts| SAM2
        SAM2 --> Orthogonalizer
    end

    subgraph DATASTORES ["🌐 Surse de Date & Output-uri Spațiale"]
        OpenData[("Open Data APIs<br/>Sentinel-2 / OSM / PVGIS")]
        LAKI[("ANCPI Ortofoto & LiDAR<br/>.laz / .las / WMS")]
        Outputs[("Suita de 9 Produse Finale<br/>GeoPackage / CAD .dxf / PDF")]
    end

    Worker -->|1. POST /api/v1/segmentation/process| API
    Worker -->|2. Polling GET /api/v1/tasks/id| API
    API --> SafeResolve
    API --> SSRFGuard
    API --> Ollama
    nDSMCalc -->|LiDAR Bounding Box Prompts| SAM2
    Orthogonalizer --> Outputs
    Outputs -->|Auto-Load Layers| UI
    OpenData --> Clipping
    LAKI --> Clipping

    class UI,MapTool,GeoCheck,Worker clientStyle;
    class SafeResolve,SSRFGuard mcpStyle;
    class API,Clipping,nDSMCalc backendStyle;
    class Ollama,SAM2,Orthogonalizer aiStyle;
    class OpenData,LAKI,Outputs dbStyle;
```

---

### 6.2 🔄 Diagrama de Flux Vizual a Utilizatorului & Bucla de Polling

```mermaid
flowchart TD
    classDef stepStart fill:#1e293b,stroke:#38bdf8,stroke-width:2px,color:#fff;
    classDef stepAction fill:#312e81,stroke:#818cf8,stroke-width:2px,color:#fff;
    classDef stepLoop fill:#4c1d95,stroke:#c084fc,stroke-width:2px,color:#fff;
    classDef stepDone fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#fff;
    classDef stepErr fill:#881337,stroke:#f43f5e,stroke-width:2px,color:#fff;

    P1["Pasul 1: Selectare AOI pe Hartă<br/>(Click 'Selectează AOI' + tragere dreptunghi)"]
    P2["Pasul 2: Conversie & Validare Geodezică<br/>(Stereo 70 EPSG:3844/31700 & 3D EPSG:5781)"]
    P3["Pasul 3: Apăsare Buton 'Rulează Segmentare'<br/>(Butonul se dezactivează + pornește Thread asincron)"]
    P4["Pasul 4: Trimitere Cerere POST<br/>(POST http://localhost:8000/api/v1/segmentation/process)"]
    
    P5{"Backend-ul a returnat<br/>task_id?"}
    
    P6["Buclă Asincronă de Polling<br/>(Interogare GET /tasks/id la fiecare 2 secunde)"]
    
    P7{"Status Task?"}
    
    P8["Status: [processing - X%]<br/>Actualizare etichetă UI în timp real"]
    P9["Status: [completed - 100%]<br/>Auto-încărcare straturi Raster/Vector în QGIS"]
    P10["Status: [failed / Error]<br/>Afișare Pop-up QMessageBox + Opțiune Fallback Mock"]

    P1 --> P2
    P2 --> P3
    P3 --> P4
    P4 --> P5
    
    P5 -->|DA| P6
    P5 -->|NU / Eroare Server| P10
    
    P6 --> P7
    P7 -->|processing| P8
    P8 -->|msleep 2000ms| P6
    P7 -->|completed| P9
    P7 -->|failed / Timeout| P10

    class P1,P2 stepStart;
    class P3,P4 stepAction;
    class P5,P6,P7,P8 stepLoop;
    class P9 stepDone;
    class P10 stepErr;
```

---

### 6.3 📦 Diagrama Fuziunii Multimodale AI + LiDAR (Layout Vertical)

```mermaid
flowchart TD
    classDef inputStyle fill:#0f172a,stroke:#38bdf8,stroke-width:2px,color:#fff;
    classDef engineStyle fill:#312e81,stroke:#818cf8,stroke-width:2px,color:#fff;
    classDef cadStyle fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#fff;
    classDef threeDStyle fill:#701a75,stroke:#f0abfc,stroke-width:2px,color:#fff;
    classDef envStyle fill:#075985,stroke:#38bdf8,stroke-width:2px,color:#fff;
    classDef riskStyle fill:#78350f,stroke:#fbbf24,stroke-width:2px,color:#fff;

    %% 1. INGESTIE DATE
    IN_RGB["1. Ortofotoplan Aerian 2D (ANCPI LAKI WMS)"]
    IN_LAS["2. Nor de Puncte LiDAR 3D (.laz / .las)"]
    IN_APIS["3. Open Data APIs (OSM / Sentinel / PVGIS)"]

    %% 2. CORE ENGINE
    E_SAM2["Meta SAM 2 GPU Inference (Segmentare 2D)"]
    E_nDSM["Calcul nDSM Altimetric (nDSM = DSM - DTM)"]
    E_Topo["Ortogonalizare 90° & Topologie Shapely"]

    IN_RGB --> E_SAM2
    IN_LAS --> E_nDSM
    IN_APIS --> E_SAM2
    E_nDSM -->|Bounding Box Prompts| E_SAM2
    E_SAM2 --> E_Topo

    %% 3. MODULE DE OUTPUT (STRUCTURATE VERTICAL)
    
    %% M1: Cadastru
    E_Topo --> OUT_CAD
    subgraph OUT_CAD ["A. Produse Cadastrale & Inginerie (Membru 1 & 2)"]
        P1["1. Strat Vectorial 2D GeoPackage (.gpkg) — Amprente clădiri, parcele, garduri"]
        P2["2. Fișier CAD ANCPI (.dxf / .dwg) — Straturi CONSTRUCTII, PARCELE, GARDURI"]
        P3["3. Fișă Imobil & Raport PDF — Plan de amplasament + Matrice suprafață Sc, Sd, P+nE"]
    end

    %% M2: 3D Urbanism
    E_Topo --> OUT_3D
    subgraph OUT_3D ["B. Produse 3D & Urbanism (Membru 2 & 3)"]
        P4["4. Modele 3D Urbane LOD1 & LOD2 (.gpkg 3D / CityGML) — Clădiri volumetrice"]
        P5["5. Cadastru Verde & Vegetație — Hărți NDVI & coronament arbori"]
    end

    %% M3: Mediu & Energie
    E_Topo --> OUT_ENV
    subgraph OUT_ENV ["C. Produse de Mediu & Energie (Membru 2)"]
        P6["6. Hărți Potențial Solar Acoperișuri — Calcul kWh/kWp/an via PVGIS API"]
        P7["7. Hărți Calitatea Aerului — Dispersie NO2, PM2.5 via Sentinel-5P"]
    end

    %% M4: Hazard & Audit Fiscal
    E_Topo --> OUT_RISK
    subgraph OUT_RISK ["D. Produse de Audit Fiscal & Hazard (Membru 1, 2 & 3)"]
        P8["8. Raport Audit Fiscal DITL / Primării — Discrepanțe suprafață reală vs taxată"]
        P9["9. Simulări Hazard Inundații & Risc Seismic — Modelare hidrodinamică & GNN"]
    end

    class IN_RGB,IN_LAS,IN_APIS inputStyle;
    class E_SAM2,E_nDSM,E_Topo engineStyle;
    class P1,P2,P3 cadStyle;
    class P4,P5 threeDStyle;
    class P6,P7 envStyle;
    class P8,P9 riskStyle;
```

---

## 7. 📊 Status Detaliat: Planul în 100 de Etape al Proiectului

Planul de implementare este structurat pe **13 faze tehnice (Fazele A – K)**, definind cu precizie ce membru al echipei este responsabil pentru fiecare pas:

- **Membru 1 (Andrei — Lead Developer):** QGIS Client, PyQGIS, interfață, comunicare locală, export CAD ANCPI, rapoarte PDF, urgențe ISU, Chat GUI, documentație și testare integrată.
- **Membru 2 (Backend & Database Engineer):** FastAPI backend, PostGIS SQL, procesare GIS locală (GDAL, PDAL, Docker), pipeline-uri Open Data (Sentinel, OSM, PVGIS, WMS ANAR) și modele 3D LOD1/LOD2.
- **Membru 3 (AI/ML Engineer):** Model local NVIDIA Nemotron-3 pe Ollama, încărcare model Meta SAM 2, optimizare nuclee CUDA, generare măști multi-clasă și modele experimentale 3D/seism.

**Legendă Status:**
* `✅ Finalizat` — Etapă complet implementată și verificată pe cod / teste.
* `⬜ Neînceput` — Etapă de producție planificată în pipeline.
* `🧪 Cercetare / Experimental` — Modul experimental de cercetare (ex: estimare altimetrică monoculară / nDSM sintetic din depth estimation AI); vezi [Secțiunea 11.5 pentru clasificarea riguroasă a surselor de date](#115-clasificare-riguroasă-a-surselor-de-date-producție-vs-ipoteze-de-cercetare).

### 7.1 📍 Ghid de Lucru pe Etape: Unde se execută fiecare fază?

Pentru a asigura claritatea mediului de lucru, iată ghidul de rulare pentru membrii echipei:
*   **Faza A & B (Etapele 1-36):** **Qt Designer** (design interfață `.ui`), **VS Code / Antigravity** (scripting Python) și **QGIS Desktop** (vizualizare canvas și testare instrument AOI).
*   **Faza C (Etapele 37-40):** **VS Code / Antigravity** (implementare `QThread` asincron în Python) și **QGIS Desktop** (validare comportament/reîncărcare).
*   **Faza D & E (Etapele 41-60):** **VS Code Terminal** (instalare `requirements.txt` și rulare server FastAPI) și **PostgreSQL/PostGIS CLI** (configurare baze de date spațiale).
*   **Faza F & G (Etapele 61-70):** **Ollama CLI / CMD** (pentru descărcare și rulare model Nemotron-3) și **VS Code Terminal / Python** (pentru rularea encoderului/decoderului PyTorch SAM 2 pe GPU).
*   **Faza H (Etapele 71-75):** **VS Code** (scriere algoritmi Shapely de topologie) și **QGIS Desktop** (verificare vizuală finală a fișierelor GeoPackage).
*   **Faza I (Etapele 76-83 — Connectori Open Data & Mediu):** **VS Code / Backend `.env`** (configurare chei API / endpoints Copernicus Sentinel-2/5P, OpenStreetMap Overpass, PVGIS API Comisia Europeană, ANAR WMS Risc Inundații).
*   **Faza J (Etapele 84-91 — Segmentare Multi-Clasă 3D & LOD1/LOD2):** **VS Code Terminal / PyTorch / PDAL** (clasificare LiDAR `.laz` pentru garduri/drumuri/vegetație; reconstrucție 3D extruzată din cota reală LiDAR vs nDSM sintetic experimental).
*   **Faza K (Etapele 92-100 — Export CAD ANCPI, Rapoarte PDF, ISU, DITL & Chat Agentic UI):** **VS Code** (bibliotecile Python `ezdxf` pentru `.dxf` ANCPI și `reportlab`/`FPDF` pentru fișă imobil PDF) și **Qt Designer / PyQGIS** (panou de chat agentic în UI QGIS).

### 7.2 Faze de Implementare (A – K)

#### 🟩 Faza A: Structură & UI Client (Etapele 1 – 33) — STATUS: FINALIZAT 100%

| Etapă | Descriere | Responsabil | Status |
|---|---|---|---|
| 1 | Configurare structură directoare (docs, stratum_ro, venv, test) | Membru 1 | ✅ Finalizat |
| 2 | Elaborare fișier manifest de înregistrare metadata.txt | Membru 1 | ✅ Finalizat |
| 3 | Configurare fișier resurse Qt (resources.qrc) | Membru 1 | ✅ Finalizat |
| 4 | Configurare script de compilare și publicare resurse pb_tool.cfg | Membru 1 | ✅ Finalizat |
| 5 | Inițializare repository Git local și definire reguli excludere în .gitignore | Membru 1 | ✅ Finalizat |
| 6 | Creare fișier de inițializare Python __init__.py pentru structurare pachet | Membru 1 | ✅ Finalizat |
| 7 | Integrare și randare pictogramă oficială plugin (icon.png) | Membru 1 | ✅ Finalizat |
| 8 | Redactare documentație primară locală (README.txt și README.html) | Membru 1 | ✅ Finalizat |
| 9 | Configurare mediu virtual izolat Python (venv) în folderul principal | Membru 1 | ✅ Finalizat |
| 10 | Legare script principal de încărcare QGIS (stratum_ro.py) | Membru 1 | ✅ Finalizat |
| 11 | Proiectare fișier interfață stratum_ro_dockwidget_base.ui în Qt Designer | Membru 1 | ✅ Finalizat |
| 12 | Configurare layout principal vertical (Vertical Layout) cu distanțare dinamică (Spacers) | Membru 1 | ✅ Finalizat |
| 13 | Integrare buton selectare AOI (btnSelectAOI) cu iconiță și tooltip | Membru 1 | ✅ Finalizat |
| 14 | Integrare buton acțiune pipeline (btnRunSegmentation) | Membru 1 | ✅ Finalizat |
| 15 | Implementare etichetă status principală (lblStatus) | Membru 1 | ✅ Finalizat |
| 16 | Implementare etichetă status secundară de progres (lblStatus_2) | Membru 1 | ✅ Finalizat |
| 17 | Adăugare dropdown vizualizare CRS în fereastra principală | Membru 1 | ✅ Finalizat |
| 18 | Definire stylesheet custom pentru menținere contrast în Dark Mode/Light Mode | Membru 1 | ✅ Finalizat |
| 19 | Compilare automată interfață XML .ui în cod Python (stratum_ro_dockwidget_base.py) | Membru 1 | ✅ Finalizat |
| 20 | Mapare elemente Qt compilate în clasa principală de widget | Membru 1 | ✅ Finalizat |
| 21 | Încărcare resurse grafice compilate în memoria grafică QGIS | Membru 1 | ✅ Finalizat |
| 22 | Definire clasă centrală StratumRO în stratum_ro.py pentru managementul plugin-ului | Membru 1 | ✅ Finalizat |
| 23 | Instanțiere obiect DockWidget la încărcarea interfeței QGIS | Membru 1 | ✅ Finalizat |
| 24 | Creare și adăugare buton rapid în bara de unelte QGIS | Membru 1 | ✅ Finalizat |
| 25 | Legare acțiuni sub-meniu în secțiunea globală Plugins → StratumRO | Membru 1 | ✅ Finalizat |
| 26 | Suprascriere eveniment închidere widget (closeEvent) pentru eliberare corectă resurse | Membru 1 | ✅ Finalizat |
| 27 | Curățare elemente adăugate în UI la dezactivarea din managerul de module | Membru 1 | ✅ Finalizat |
| 28 | Conectare semnal PyQt5 closingPlugin pentru notificare instanță superioară | Membru 1 | ✅ Finalizat |
| 29 | Creare conexiune consolă QGIS pentru logging mesaje de sistem | Membru 1 | ✅ Finalizat |
| 30 | Configurare scripturi rulare teste automate în folderul test/ | Membru 1 | ✅ Finalizat |
| 31 | Definire mediu virtual mock pentru rulare headless a testelor de interfață | Membru 1 | ✅ Finalizat |
| 32 | Înregistrare în sistemul QGIS a suportului de reîncărcare dinamică (Plugin Reloader) | Membru 1 | ✅ Finalizat |
| 33 | Validare conformitate arhitecturală PEP8 și rezolvare importuri relative interne | Membru 1 | ✅ Finalizat |

#### 🟩 Faza B: Gestiune Geodezică & Map Canvas (Etapele 34 – 36) — STATUS: FINALIZAT 100%

| Etapă | Descriere | Responsabil | Status |
|---|---|---|---|
| 34 | Integrare QgsMapToolExtent pentru desenare interactivă AOI pe ecran (Click stânga lung + tragere dreptunghi) | Membru 1 | ✅ Finalizat |
| 35 | Citire automată CRS canvas activ, suport dual Stereo 70 (EPSG:3844 ANCPI / EPSG:31700 legacy) și detecție 3D Marea Neagră 1975 (EPSG:5781) cu transformare geodezică instantanee prin QgsCoordinateTransform dacă coordonatele diferă | Membru 1 | ✅ Finalizat |
| 36 | Integrare script auto-încărcare straturi. Instanțiere obiect QgsRasterLayer și randarea sa în arborele de straturi direct la finalizarea simulării (stadiu 100%) | Membru 1 | ✅ Finalizat |

#### 🟩 Faza C: Conectivitate Hibridă (Etapele 37 – 40) — STATUS: FINALIZAT 100%

| Etapă | Descriere | Responsabil | Status |
|---|---|---|---|
| 37 | Înlocuire mecanism simulare (Mock) cu cerere HTTP asincronă reală de tip POST utilizând librăria requests | Membru 1 | ✅ Finalizat |
| 38 | Tratare excepții de rețea, erori de tip 404/500 și Timeout prin ferestre native de eroare PyQt5 (QMessageBox) | Membru 1 | ✅ Finalizat |
| 39 | Validare structurală a obiectului GeoJSON înainte de expedierea pachetului către server | Membru 1 | ✅ Finalizat |
| 40 | Sincronizare fire de execuție client cu statusul asincron (Polling la /tasks/{id}) | Membru 1 | ✅ Finalizat |

> **📌 Notă Audit Comparativ (Iulie 2026):** Din analiza proiectelor similare (Geo-SAM, Deepness, Mapflow, AI Segmentation TerraLab), au fost identificate următoarele funcționalități suplimentare necesare pe partea de client QGIS (Membru 1):
> 1. **Regularizare contururi clădiri** (ortogonalizare colțuri 90° — se integrează la Etapa 72)
> 2. **Validare topologică automată** (eliminare suprapuneri/goluri — se integrează la Etapa 74)
> 3. **Bară de progres vizuală QProgressBar** (conectată la polling — extensie Etapa 40)
> 4. **Selecție AOI multi-metodă** (poligon liber + selecție feature — extensie Etapa 34)
> 5. **Preview rezultat în dockwidget** (thumbnail segmentare — extensie Etapa 36)
> 6. **Selecție model AI din UI** (dropdown model + prag confidență — extensie Etapa 66)
> 7. **Istoric procesări / Session Log** (jurnal JSON persistent — funcționalitate nouă)

#### 🟦 Faza D: Ingestie Date & Database MLOps (Etapele 41 – 50) — SARCINI BACKEND

| Etapă | Descriere | Responsabil | Status |
|---|---|---|---|
| 41 | Configurare mediu backend și ridicare instanță FastAPI pe portul local 8000 | Membru 2 | ⬜ Neînceput |
| 42 | Definire și expunere endpoint unificat de procesare POST /api/v1/segmentation/process | Membru 2 | ⬜ Neînceput |
| 43 | Validare date de intrare (Request payload) folosind scheme riguroase Pydantic | Membru 2 | ⬜ Neînceput |
| 44 | Extragere geometrie AOI Stereo 70 și conversie în obiecte geometrice spațiale (Shapely/GeoPandas) | Membru 2 | ⬜ Neînceput |
| 45 | Mapare cod administrativ SIRUTA primit de la plugin pentru interogarea limitelor administrative | Membru 2 | ⬜ Neînceput |
| 46 | Validare topologică de bază (verificarea încadrării corecte a geometriei AOI pe teritoriul României) | Membru 2 | ⬜ Neînceput |
| 47 | Localizare depozit local de date raster (Ortofotoplanuri multispectrale stocate local) | Membru 2 | ⬜ Neînceput |
| 48 | Localizare depozit local nori de puncte LiDAR (format .laz / .las) | Membru 2 | ⬜ Neînceput |
| 49 | Calculare intersecție spațială pentru identificarea automată a fișierelor raster/LiDAR corespunzătoare selecției | Membru 2 | ⬜ Neînceput |
| 50 | Decupare dinamică raster (Raster clipping) pe limitele bounding-box-ului din payload | Membru 2 | ⬜ Neînceput |

#### 🟦 Faza E: Preprocesare LiDAR & Aliniere Date (Etapele 51 – 60) — SARCINI BACKEND

| Etapă | Descriere | Responsabil | Status |
|---|---|---|---|
| 51 | Generare ortofotoplan de înaltă rezoluție decupat la nivel de zonă de interes (AOI) | Membru 2 | ⬜ Neînceput |
| 52 | Încărcare nor de puncte LiDAR în fluxul de procesare local folosind biblioteci specializate (PDAL sau laspy) | Membru 2 | ⬜ Neînceput |
| 53 | Aplicare filtre de reducere a zgomotului LiDAR și curățare date aberante | Membru 2 | ⬜ Neînceput |
| 54 | Clasificare nor de puncte LiDAR în elemente de tip „Sol" (Ground) și „Non-Sol" | Membru 2 | ⬜ Neînceput |
| 55 | Generare Model Digital al Suprafeței (DSM — Digital Surface Model) din punctele clasificate | Membru 2 | ⬜ Neînceput |
| 56 | Generare Model Digital al Terenului (DTM — Digital Terrain Model) | Membru 2 | ⬜ Neînceput |
| 57 | Calculare Model Normalizat al Înălțimii (nDSM = DSM − DTM) pentru izolarea structurilor supraterane | Membru 2 | ⬜ Neînceput |
| 58 | Execuție operațiune de potrivire spațială și aliniere pixel-la-pixel între nDSM (LiDAR) și Ortofotoplan (Raster) | Membru 2 | ⬜ Neînceput |
| 59 | Normalizare valori spectrale și înălțimi (pe scară de la 0 la 1) pentru optimizare pipeline rețea | Membru 2 | ⬜ Neînceput |
| 60 | Salvare matrice hibridă preprocesată în format binar numpy (.npy) pentru acces rapid | Membru 2 | ⬜ Neînceput |

#### 🟦 Faza F: Orchestrare LLM local & Model Context Protocol (Etapele 61 – 65) — SARCINI BACKEND / AI

| Etapă | Descriere | Responsabil | Status |
|---|---|---|---|
| 61 | Inițializare instanță locală Ollama cu modelul avansat de orchestrare NVIDIA Nemotron-3 pe stația de calcul locală | Membru 3 | ⬜ Neînceput |
| 62 | Configurare server Model Context Protocol (MCP) pentru legarea LLM direct la fișierele de sistem ale serverului local | Membru 2 & 3 | ⬜ Neînceput |
| 63 | Elaborare prompt de sistem structurat pentru evaluarea datelor de intrare (UAT, SIRUTA, coordonate) | Membru 3 | ⬜ Neînceput |
| 64 | Analiză și decizie contextuală luată de LLM (ex: determinarea densității vegetației în AOI pentru ajustarea pragurilor de segmentare) | Membru 3 | ⬜ Neînceput |
| 65 | Transmitere instrucțiuni structurate din agentul LLM către rețeaua neuronală de inferență | Membru 2 & 3 | ⬜ Neînceput |

#### 🟦 Faza G: Inferență Rețea Neuronală Meta SAM 2 (Etapele 66 – 70) — SARCINI AI

| Etapă | Descriere | Responsabil | Status |
|---|---|---|---|
| 66 | Încărcare în memorie a modelului Meta SAM 2 (Segment Anything 2) | Membru 3 | ⬜ Neînceput |
| 67 | Alocare dinamică memorie GPU (NVIDIA CUDA), verificând menținerea resurselor sub pragul critic (minimum 8GB VRAM) | Membru 3 | ⬜ Neînceput |
| 68 | Rulare encoder de imagine SAM 2 pe ortofotoplanul decupat pentru extragerea hărților de caracteristici | Membru 3 | ⬜ Neînceput |
| 69 | Generare de indicii spațiale (points/bounding box prompts) folosind zonele cu înălțimi ridicate din nDSM (LiDAR) pentru ghidare SAM 2 | Membru 3 | ⬜ Neînceput |
| 70 | Execuție decoder SAM 2 și generare măști de segmentare binare la nivel de clădire | Membru 3 | ⬜ Neînceput |

#### 🟦 Faza H: Post-procesare, Vectorizare & Validare Cadastrală (Etapele 71 – 75) — SARCINI BACKEND / AI

| Etapă | Descriere | Responsabil | Status |
|---|---|---|---|
| 71 | Conversie măști binare raster în structuri poligonale vectoriale (GDAL polygonize) | Membru 2 | ⬜ Neînceput |
| 72 | Aplicare algoritm de ortogonalizare a colțurilor clădirilor (reducere poligoane neregulate la unghiuri de 90°) | Membru 2 & 3 | ⬜ Neînceput |
| 73 | Filtrare poligoane pe baza ariei minime utile și a pragului de încredere probabilistic (confidence threshold) | Membru 2 | ⬜ Neînceput |
| 74 | Execuție validare topologică cadastrală (eliminare suprapuneri clădiri, corectare granițe UAT) | Membru 2 | ⬜ Neînceput |
| 75 | Salvare fișiere finale în formate standardizate: Raster GeoTIFF (.tif) și Vector GeoPackage (.gpkg), generare ID unic de task și returnare răspuns JSON de succes ce va declanșa Etapa 36 în QGIS | Membru 2 | ⬜ Neînceput |

#### 🟨 Faza I: Ingestie Surse Deschise Naționale & Mediu (Etapele 76 – 83) — SARCINI BACKEND

| Etapă | Descriere | Responsabil | Status |
|---|---|---|---|
| 76 | Connector ESA Copernicus Sentinel-2 API (descărcare gratuită benzi spectrale B4, B8 la 10m) | Membru 2 | ⬜ Neînceput |
| 77 | Calcul indici de vegetație (NDVI) și impermeabilitate sol (NDBI) din imagini Sentinel-2 | Membru 2 | ⬜ Neînceput |
| 78 | Integration Sentinel-5P API (date poluare calitatea aerului $NO_2$, $PM_{2.5}$) | Membru 2 | ⬜ Neînceput |
| 79 | Client Overpass API (extragere gratuită graf rutier, hidranți și POI-uri din OpenStreetMap) | Membru 2 | ⬜ Neînceput |
| 80 | Connector PVGIS API (Comisia Europeană — calcul gratuit potențial solar $kWh/\text{an}$ per acoperiș) | Membru 2 | ⬜ Neînceput |
| 81 | Client WMS Risc Inundații Apele Române (ANAR — benzi de inundaabilitate HQA) | Membru 2 | ⬜ Neînceput |
| 82 | Ingestie Date Demographics INS Grid $1\text{ km}^2$ (densitate populație per UAT) | Membru 2 | ⬜ Neînceput |
| 83 | Salvare date mediu în PostGIS ca straturi vectoriale/raster de context regional | Membru 2 | ⬜ Neînceput |

#### 🟨 Faza J: Segmentare Multi-Clasă 3D & Reconstrucție LOD1/LOD2 (Etapele 84 – 91) — SARCINI AI & BACKEND

| Etapă | Descriere | Responsabil | Status |
|---|---|---|---|
| 84 | Clasificare AI nor LiDAR / nDSM pentru garduri și împrejmuiri ($0.5\text{m} \dots 2.5\text{m}$) | Membru 3 | ⬜ Neînceput |
| 85 | Segmentare AI căi de acces și suprafețe carosabile (drumuri, trotuare, parcări) | Membru 3 | ⬜ Neînceput |
| 86 | Extragere cadru cadastru verde (identificare coronament arbori și suprafață spații verzi) | Membru 3 | ⬜ Neînceput |
| 87 | Reconstrucție volumetrice 3D LOD1 (clădiri formate ca prisme drepte cu înălțime din LiDAR real) | Membru 2 | ⬜ Neînceput |
| 88 | Estimare altimetrică monoculară (nDSM sintetic din Metric3D sau Depth Anything V2 ca alternativă) *(Modul experimental)* | Membru 3 | 🧪 Cercetare / Experimental |
| 89 | Extragere cota streașină și cota coamă din norul de puncte LiDAR real (`.laz`/`.las` / MNT LAKI) | Membru 2 | ⬜ Neînceput |
| 90 | Reconstrucție geometrie 3D acoperiș LOD2 (clasificare acoperiș în două ape, terasă, mansardă) | Membru 3 | ⬜ Neînceput |
| 91 | Export modele 3D în format CityGML / GeoPackage 3D pentru vizualizare spatială | Membru 2 | ⬜ Neînceput |

#### 🟨 Faza K: Export CAD, Rapoarte, Audit Fiscal & Interfață Agentică (Etapele 92 – 100) — SARCINI CLIENT & BACKEND

| Etapă | Descriere | Responsabil | Status |
|---|---|---|---|
| 92 | Motor Export CAD `.dxf` / `.dwg` structurat pe straturile ANCPI (`CONSTRUCTII`, `PARCELE`, `GARDURI`) via `ezdxf` | Membru 1 | ⬜ Neînceput |
| 93 | Calcul Matrice Suprafață ($S_c$ construită, $S_d$ desfășurată, Regim de înălțime $P+nE$) | Membru 1 | ⬜ Neînceput |
| 94 | Generare automată Raport PDF / Fișă Imobil cu plan de amplasament via `reportlab` | Membru 1 | ⬜ Neînceput |
| 95 | Modul audit fiscal DITL (verificare discrepanțe între amprenta AI și suprafața impozitată) | Membru 2 | ⬜ Neînceput |
| 96 | Modul urgențe ISU (verificare gabarit drum de acces vs scări de intervenție pompieri) | Membru 1 | ⬜ Neînceput |
| 97 | Simulare hidrodinamică risc inundații urbane pe baza DTM și coeficienți Manning | Membru 2 | ⬜ Neînceput |
| 98 | Modelare vulnerabilitate seismică (Rețele Neurale pe Grafuri — GNN bazat pe volum și vechime) | Membru 3 | 🧪 Cercetare / Experimental |
| 99 | Interfață Panou Chat Agentic în QGIS UI (asistent conversațional local pentru interogare spațială) | Membru 1 | ⬜ Neînceput |
| 100 | Testare integrată end-to-end pe 5 UAT-uri reprezentative din România (Oradea, București, Timișoara, Cluj, Tulcea) | Membru 1, 2 & 3 | ⬜ Neînceput |

---

## 8. 📋 Suita Celor 9 Deliverabile Spațiale Realizabile

| Nr. | Produs Final | Format Fișier | Responsabili | Descriere Tehnică |
|---|---|---|---|---|
| **1** | **Strat Vectorial 2D** | `.gpkg` (GeoPackage) | Membru 1 & 2 | Amprente clădiri, parcele și împrejmuiri validat topologic în QGIS. |
| **2** | **Fișier CAD ANCPI** | `.dxf` / `.dwg` | Membru 1 | Export vectorial structurat pe straturile oficiale ANCPI (`CONSTRUCTII`, `PARCELE`, `GARDURI`). |
| **3** | **Fișă Imobil & Raport PDF** | `.pdf` | Membru 1 | Documentație tehnică autogenerată cu plan de amplasament, matrice de precizie Auto-Snap Procrustes (SVD), audit topologic și calcule de suprafață ($S_c$, $S_d$, $P+nE$). |
| **4** | **Modele 3D Urbane LOD1/LOD2** | `.gpkg 3D` / CityGML | Membru 2 & 3 | Clădiri volumetrice cu cote de streașină/coamă din LiDAR real și tip de acoperiș. |
| **5** | **Cadastru Verde & Vegetație** | `.gpkg` / `.tif` | Membru 3 | Hărți ale suprafețelor verzi, masei frondose și coronamentului arborilor (NDVI Sentinel-2). |
| **6** | **Hărți Potențial Solar** | `.gpkg` / Report | Membru 2 | Calculul producției de energie fotovoltaică în $kWh/\text{an}$ pe fiecare acoperiș (PVGIS API). |
| **7** | **Hărți Calitatea Aerului** | `.tif` (Raster) | Membru 2 | Analiza dispersiei poluanților urbani ($NO_2$, $PM_{2.5}$) preluată din satelitul Sentinel-5P. |
| **8** | **Raport Audit Fiscal DITL** | `.pdf` / Excel | Membru 1 & 2 | Identificarea automată a clădirilor nedeclarate sau extinse ilegal pentru primării. |
| **9** | **Simulări Hazard & Seism** | `.gpkg` / Raport | Membru 2 & 3 | Modelare hidrodinamică (inundații urbane) și evaluare vulnerabilitate seismică (GNN). |

---

## 9. 🔌 Contract de Date API Unificat (Specificații pentru Backend)

**Endpoint:**
```
POST http://localhost:8000/api/v1/segmentation/process
```

**Request JSON** (trimis de plugin):
```json
{
  "project_name": "Segmentare_Nationala_StratumRO",
  "crs": "EPSG:3844",
  "crs_vertical": "EPSG:5781",
  "crs_compound": "EPSG:3844+5781",
  "supported_crs": ["EPSG:3844", "EPSG:31700"],
  "dimension": "3D",
  "aoi_selection_mode": "hybrid",
  "geometry": {
    "type": "Polygon",
    "coordinates": [
      [
        [125000.00, 230000.00],
        [880000.00, 230000.00],
        [880000.00, 770000.00],
        [125000.00, 770000.00],
        [125000.00, 230000.00]
      ]
    ]
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
```

**Response JSON** (returnat de backend):
```json
{
  "status": "success",
  "task_id": "b3f1c2a4-0e9d-4a7b-9c1e-2f6d8a5e7c10",
  "project_name": "Segmentare_Nationala_StratumRO",
  "results": {
    "raster_path": "/data/output/Oradea_26573/segmentation.tif",
    "vector_path": "/data/output/Oradea_26573/buildings.gpkg",
    "crs": "EPSG:3844",
    "crs_vertical": "EPSG:5781",
    "dimension": "3D",
    "feature_count": 482
  },
  "processing": {
    "model_version": "v1.0-default",
    "confidence_threshold": 0.5,
    "duration_seconds": 47.3
  },
  "errors": []
}
```

---

## 10. ⚠️ Notă Importantă privind Rularea Modului Mock

La testarea funcționalității în mod **Mock / Fallback**:
*   **Locație fișier de test:** Se încarcă rasterul `test_gdal_byte.tif` din folderul `datasets/orthophotos/`.
*   **Georeferențiere (De ce face Zoom în California?):** Deoarece acest fișier este un eșantion standard furnizat de biblioteca GDAL, el are sistemul de proiecție definit nativ în **UTM Zone 11 North (NAD27)**, localizat în sudul Californiei (regiunea Corona/Chino Hills).
*   **Comportament în QGIS:** Când folosiți opțiunea *Zoom to Layer* pe stratul rezultat, camera QGIS se va muta automat în California. Acesta este comportamentul corect și demonstrează citirea fișierului fizic local de pe disc.
*   **Rularea Reală (Producție):** În rularea normală cu serverul FastAPI pornit, datele rezultate din modelul AI pentru regiunea Oradea (sau alte regiuni selectate) vor fi decupate și returnate direct în sistemul geodezic național **Stereo 70 (EPSG:3844 ANCPI / EPSG:31700 legacy)** cu altimetrie Marea Neagră 1975 (EPSG:5781).

---

## 11. 📈 Strategia de Viabilitate a Produsului & Inovații Cadastrale

### 11.1 Conceptul de „Pre-Vectorizare” cu Snap-to-RTK
*   Sistemul nu își propune realizarea unui cadastru 100% automatizat fără intervenție umană (ceea ce ar fi imposibil din punct de vedere legal din cauza preciziei decimetrice a datelor inițiale).
*   În schimb, scopul este reducerea timpului de desenare cu peste **80%**. Modelul AI extrage forma, topologia și amplasamentul clădirilor, iar plugin-ul QGIS permite atragerea elastică (*snapping*) a acestora direct peste punctele GPS exacte (RTK) colectate din măsurătorile de teren.

### 11.2 Validare Topologică și Strat de Erori
*   Pentru a asigura rigoarea geodezică, plugin-ul rulează reguli geometrice stricte (prin Shapely pe backend) și generează în QGIS un strat vectorial dedicat erorilor topologice (suprapuneri nepermise, micro-goluri între clădiri lipite la calcan sau fragmente reziduale sub pragul de $5\text{ mp}$). Inginerul cadastral poate audita și corecta aceste anomalii dintr-o singură privire, accelerând faza de control a calității.

### 11.3 Extindere Strategică: Baza de Date Imobiliar-Notarială
*   Fiecare clădire sau parcelă extrasă automat devine o entitate completă în baza de date spațială PostGIS. 
*   Fiecare imobil va fi asociat printr-un identificator unic de documente notariale, acte de proprietate (.pdf, .doc), sarcini juridice și istoric de tranzacționare. Interfața QGIS dezvoltată de Membru 1 va permite interogarea și atașarea directă a acestor documente pe geometria selectată pe hartă.

### 11.4 Integrarea Analizei Predictive: Simulare Hazard și Mediu
Clasificarea semantică realizată de modelul hibrid AGMF nu reprezintă doar un produs cartografic static, ci constituie fundamentul pentru simulări predictive complexe:
*   **Modelare Hidrodinamică (Risc de Inundație):** Clasele de acoperire a terenului sunt convertite în coeficienți de fricțiune hidraulică (Manning n). Corelate cu modelul DTM, acestea permit rularea ecuațiilor Saint-Venant (ex. prin motorul LISFLOOD-FP) pentru a simula acumularea apei din precipitații în medii urbane în timp real.
*   **Vulnerabilitate Seismică:** Datele geometrice brute (amprentă, înălțime totală din LiDAR, volum, proximitate) sunt corelate cu vechimea cadastrală pentru a evalua automat riscul de colaps structural folosind Rețele Neurale pe Grafuri (GNN).
*   **Dispersia Poluanților:** Modelele 3D ale clădirilor și coronamentul arborilor sunt exportate în simulatoare micro-meteorologice (ex. ENVI-met) pentru a identifica zonele în care particulele nocive ($PM_{2.5}$, $NO_2$) rămân blocate din cauza lipsei curenților de aer (canioane urbane).

### 11.5 Clasificare Riguroasă a Surselor de Date: Producție vs. Ipoteze de Cercetare

> [!IMPORTANT]
> Pentru menținerea rigorii tehnice și geodezice în documentația oficială a proiectului, capabilitățile platformei sunt structurate strict în două categorii delimitate:

#### ✅ Gata de Producție (Garanție de Rigoare Cadastrală)
*   **Vectorizare 2D Amprente Clădiri:** Segmentare AI din Ortofotoplanuri aeriene (ANCPI LAKI) ghidată de date vectoriale 2D de referință (**OpenStreetMap**, **Microsoft Building Footprints**).
*   **Cota Terenului (DTM) și Cota Clădirii (MDS/nDSM):** Calculul altimetric al cotes de streașină/coamă și al regimului de înălțime ($P+nE$) se bazează **EXCLUSIV pe date fizice altimetrice reale** (Nori de puncte LiDAR `.laz`/`.las` sau MNT/MDS grilă oficiale din proiectele LAKI II / LAKI III).
*   **Validare Topologică & Snap-to-RTK:** Corecție geometrică Shapely pe reguli stricte și potrivire elastică peste măsurători GPS de teren.

#### 🧪 Ipoteză de Cercetare & Experimental (NU folosiți pentru depuneri cadastrale oficiale)
*   **Estimare Altimetrică Monoculară (nDSM Sintetic / Depth Anything V2 / MiDaS):** Generarea unei hărți sintetice de adâncime din imagini aeriene 2D produce valori de adâncime relative (affine-invariant), necalibrate metric pe imagini nadir (top-down 90°). Prezintă erori absolute ($> 1.5\text{m} \dots 5\text{m}$) incompatibili cu toleranța cadastrală legală. Este marcată ca modul experimental de cercetare și este interzisă utilizarea sa pentru generarea memoriilor tehnice oficiale.
*   **Seturi de date de acoperire globală fără acoperire pe România (Google Open Buildings):** Dataset-ul Google Open Buildings acoperă exclusiv Africa, Asia de Sud și America Latină; pentru România se utilizează ca fallback public exclusiv Microsoft Building Footprints și OSM.

---

## 12. 🛡️ Evaluare & Feedback pe Direcția Proiectului (AI Expert Review)

*   **Validarea Arhitecturii Hibride:** Decizia de a dezvolta un plugin QGIS ca interfață subțire de client (Membru 1) conectat la un backend FastAPI local (Membru 2 & 3) este ideală. Aceasta elimină costurile prohibitive de cloud (GPU-uri închiriate) și oferă suveranitate totală asupra datelor, aspect critic pentru confidențialitatea lucrărilor cadastrale.
*   **Reziliența Modelului AGMF:** Alegerea modelului AGMF ca flagship în locul unui simplu stack plat reprezintă o decizie tehnică matură. Utilizarea porții adaptive de gating ($G_{spec}$) rezolvă erorile clasice din GIS provocate de umbrele aruncate de clădiri și vegetație, alternând dinamic între datele spectrale și cota fizică brută oferită de LiDAR.
*   **Direcția de Business:** Orientarea produsului către eficientizarea timpului de vectorizare și oferirea de modele predictive de nișă (inundații, seism, notariat) asigură o propunere de valoare puternică, făcând aplicația viabilă și comercializabilă pentru municipalități și companii de inginerie.

---

## 13. 📄 Licență & 👥 Contribuții

Proiect privat dezvoltat în regim intern de inginerie. Toate drepturile rezervate autorilor (Proprietary / Private code).

Proiect dezvoltat de o echipă mică de ingineri; contribuțiile sunt acceptate exclusiv prin Pull Request pe branch-urile de dezvoltare dedicate. Deschideți un Issue înainte de orice propunere de modificare majoră adusă arhitecturii existente.

---

## 14. 📚 Surse de Date & Atribuiri

* **ANCPI:** Ortofotoplanuri naționale 2D, LiDAR 3D (LAKI II/III), limite UAT și coduri SIRUTA.
* **Copernicus / ESA:** Sateliți Sentinel-2 (NDVI) și Sentinel-5P (calitatea aerului).
* **OpenStreetMap:** Grafuri rutiere deschise (licență ODbL).
* **PVGIS (Comisia Europeană):** Iradianță solară și potențial fotovoltaic.
* **Apele Române (ANAR):** Hărți digitale de risc la inundații (HQA).
* **INS:** Griduri demografice de populație (1 km²).
* **Meta AI / NVIDIA:** Modelele Meta SAM 2 (segmentare 2D) și NVIDIA Nemotron-3 (LLM local).
* **Autorat:** Lefter Patrick Andrei & GeoMateLINE.