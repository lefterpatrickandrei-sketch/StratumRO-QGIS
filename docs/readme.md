StratumRO — Sistem Inteligent de Segmentare Cadastrală (QGIS Plugin) 🌍🚀Sistem MLOps integrat pentru descărcarea, filtrarea și procesarea automată a datelor geospațiale (LiDAR și Raster) la nivel național, cu suport nativ pentru selecție geometrică pe canvas și coduri administrative SIRUTA.📝 Descriere Generală / Description / Descripción🇷🇴 RomânăAgentic GIS conectează QGIS la un backend AI local (FastAPI + Ollama LLM + Meta SAM2) pentru extragerea automată a amprentelor clădirilor din ortofotoplanuri și nori de puncte LiDAR. Plugin-ul permite selectarea unei zone de interes (AOI) direct pe hartă, trimiterea ei către backend pentru segmentare și clasificare AI, iar rezultatul revine ca strat vectorial QGIS gata de utilizare (GeoPackage).În spate, un agent bazat pe modelul de ultimă generație NVIDIA Nemotron-3 (rulat complet local prin Ollama) orchestrează fluxul de lucru prin Model Context Protocol (MCP), coordonând segmentarea, curățarea geometrică și validarea topologică înainte ca rezultatele să ajungă pe hartă. Toată procesarea rulează pe hardware local — datele nu părăsesc mașina. Necesită un serviciu backend local activ; inferența AI este accelerată pe GPU (recomandat minimum 8GB VRAM), cu un mod fallback CPU-only, mai lent, pentru cine nu are placă video compatibilă. Este un proiect activ de cercetare aplicată în geomatică și AI geospațial, dezvoltat de o echipă mică de ingineri; rezultatele sunt gândite să accelereze vectorizarea manuală și trebuie verificate înainte de utilizare în depuneri cadastrale oficiale.🇬🇧 EnglishAgentic GIS connects QGIS to a local, privacy-preserving AI backend (FastAPI + Ollama LLM + Meta SAM2) to automate building footprint extraction from orthophotos and LiDAR point clouds. The plugin lets you select an area of interest directly on the map canvas, sends it to the backend for AI-driven segmentation and classification, and returns validated building polygons as a ready-to-use QGIS vector layer (GeoPackage).Under the hood, an AI agent based on the state-of-the-art NVIDIA Nemotron-3 model (running completely locally through Ollama) orchestrates the workflow via the Model Context Protocol (MCP), coordinating segmentation, geometric cleanup, and topology validation before results reach the map. All processing runs on local hardware — no orthophoto or point cloud data leaves the machine. Requires a running local backend service; AI inference is GPU-accelerated (8GB+ VRAM recommended), with a slower CPU-only fallback mode for machines without a compatible GPU. This is an active applied-research project in geomatics and geospatial AI, developed by a small engineering team; outputs are intended to speed up manual vectorization and should be reviewed before use in official cadastral submissions.🇪🇸 EspañolAgentic GIS conecta QGIS con un backend de IA local que preserva la privacidad (FastAPI + Ollama LLM + Meta SAM2) para automatizar la extracción de huellas de edificios a partir de ortofotos y nubes de puntos LiDAR. El plugin permite seleccionar un área de interés directamente sobre el lienzo del mapa, la envía al backend para segmentación y clasificación mediante IA, y devuelve los polígonos de edificios validados como una capa vectorial de QGIS lista para usar (GeoPackage).Internamente, un agente de IA basado en el modelo de última generación NVIDIA Nemotron-3 (ejecutado localmente mediante Ollama) orquesta el flujo de trabajo mediante el Model Context Protocol (MCP), coordinando la segmentación, la limpieza geométrica y la validación topológica antes de que los resultados lleguen al mapa. Todo el procesamiento se ejecuta en hardware local — ningún dato sale de la máquina. Requiere un servicio backend local en ejecución; la inferencia de IA se acelera por GPU (se recomiendan 8GB+ de VRAM), con un modo de respaldo solo-CPU, más lento, para equipos sin GPU compatible. Es un proyecto activo de investigación aplicada en geomática e IA geoespacial, desarrollado por un equipo pequeño de ingenieros; los resultados están pensados para acelerar la vectorización manual y deben revisarse antes de usarse en presentaciones catastrales oficiales.📂 Compoziția și Structura Workspace-uluiWorkspace-ul proiectului este structurat conform standardelor profesionale PyQGIS, decuplând resursele de lucru de logica activă de execuție:QGIS-AI/ (Workspace Principal)
├── docs/
│   ├── architecture.md                 # Specificațiile tehnice și contractul API original
│   └── README.md                       # Acest ghid tehnic unificat (Manualul Proiectului)
├── stratum_ro/                         # Pachetul principal al plugin-ului QGIS
│   ├── __pycache__/
│   ├── scripts/                        # Scripturi auxiliare de procesare
│   ├── test/                           # Suite de teste unitare și utilitare geodezice
│   ├── __init__.py                     # Inițializarea pachetului Python
│   ├── icon.png                        # Pictograma plugin-ului vizibilă în QGIS
│   ├── metadata.txt                    # Informațiile de versiune și categorii pentru managerul QGIS
│   ├── pb_tool.cfg                     # Configurația de compilare a resurselor Qt
│   ├── README.html                     # Versiunea HTML a documentației locale
│   ├── README.txt                      # Versiunea text simplu a documentației locale
│   ├── stratum_ro.py                   # Clasa principală care înregistrează plugin-ul în interfața QGIS
│   ├── stratum_ro_dockwidget_base.ui   # Interfața grafică XML proiectată în Qt Designer
│   ├── stratum_ro_dockwidget_base.py   # Codul Python compilat automat din fișierul .ui
│   └── stratum_ro_dockwidget.py        # Logica operațională, geodezică și de rețea (Pilotul)
├── venv/                               # Mediul virtual Python local
├── .gitignore                          # Excluderea fișierelor temporare și cache-ului din Git
└── AGENTS.md                           # Instrucțiuni și rute operaționale pentru agenți AI

💻 Codul Sursă de Referință (stratum_ro_dockwidget.py)Mai jos este prezentat codul sursă complet al nucleului plugin-ului. Acest script reprezintă implementarea tehnică a Etapelor 34, 35 și 36, asigurând interfața asincronă și auto-încărcarea datelor în QGIS:# -*- coding: utf-8 -*-

import os
import json
import requests
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import pyqtSignal
# Importul claselor esențiale PyQGIS pentru reproiectare și de lucru cu straturi
from qgis.core import QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsProject, QgsRasterLayer
from qgis.gui import QgsMapToolExtent

# Moștenim designul structural compilat din Qt Designer
from .stratum_ro_dockwidget_base import Ui_StratumRODockWidgetBase

class StratumRODockWidget(QtWidgets.QDockWidget, Ui_StratumRODockWidgetBase):
    closingPlugin = pyqtSignal()

    def __init__(self, iface, parent=None):
        super(StratumRODockWidget, self).__init__(parent)
        self.iface = iface
        
        # Inițializăm componentele vizuale proiectate
        self.setupUi(self)

        # Variabile interne pentru selecția spațială și rețea
        self.current_aoi_geometry = None
        self.map_tool = None
        self.api_url = "http://localhost:8000/api/v1/segmentation/process"

        # Conectarea elementelor interactive din UI la funcțiile lor
        self.btnSelectAOI.clicked.connect(self.init_map_tool)
        self.btnRunSegmentation.clicked.connect(self.run_segmentation_pipeline)

    def init_map_tool(self):
        """Activează instrumentul nativ QGIS de selecție prin tragerea unui dreptunghi."""
        self.map_tool = QgsMapToolExtent(self.iface.mapCanvas())
        self.map_tool.extentChanged.connect(self.capture_coordinates)
        self.iface.mapCanvas().setMapTool(self.map_tool)
        self.lblStatus_2.setText("Status: Trage un dreptunghi pe hartă...")

    def capture_coordinates(self, extent):
        """Captează coordonatele selectate de pe ecran și le convertește în Stereo 70."""
        self.iface.mapCanvas().unsetMapTool(self.map_tool)
        
        xmin = extent.xMinimum()
        xmax = extent.xMaximum()
        ymin = extent.yMinimum()
        ymax = extent.yMaximum()

        current_crs = self.iface.mapCanvas().mapSettings().destinationCrs()
        stereo70 = QgsCoordinateReferenceSystem("EPSG:31700")

        # Reproiectare dinamică automată dacă harta nu este deja în Stereo 70
        if current_crs.authid() != "EPSG:31700":
            transform = QgsCoordinateTransform(current_crs, stereo70, QgsProject.instance())
            point_min = transform.transform(xmin, ymin)
            point_max = transform.transform(xmax, ymax)
            xmin, ymin = point_min.x(), point_min.y()
            xmax, ymax = point_max.x(), point_max.y()

        # Structură tip Poligon (închis) pregătită pentru standardul GeoJSON / API
        self.current_aoi_geometry = [
            [xmin, ymin],
            [xmax, ymin],
            [xmax, ymax],
            [xmin, ymax],
            [xmin, ymin]
        ]

        self.lblStatus_2.setText("Status: AOI salvat cu succes în Stereo 70!")
        print(f"[StratumRO] Coordonate Stereo 70: {self.current_aoi_geometry}")

    def run_segmentation_pipeline(self):
        """Trmite pachetul JSON către API-ul FastAPI sau intră în modul de fallback simulat."""
        if not self.current_aoi_geometry:
            self.lblStatus_2.setText("Status: Eroare! Selectează mai întâi o zonă pe hartă.")
            return

        self.lblStatus_2.setText("Status: Se trimite payload-ul la FastAPI...")

        # Construirea payload-ului conform contractului tehnic unificat
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
            # Apel HTTP POST real asincron (cu timeout de siguranță pentru a preveni blocarea hărții)
            response = requests.post(self.api_url, json=payload, timeout=3)
            if response.status_code in [200, 201]:
                data = response.json()
                self.lblStatus_2.setText(f"Status: Server conectat!\nTask ID: {data.get('task_id')}")
            else:
                self.lblStatus_2.setText(f"Status: Eroare Server ({response.status_code})")
        except requests.exceptions.RequestException:
            # Backend-ul fiind offline, pornește simularea securizată asincronă (Mock Polling)
            self.execute_mock_polling()

    def execute_mock_polling(self):
        """Simulează asincron stările de procesare din backend fără a îngheța QGIS."""
        QtCore.QTimer.singleShot(2000, lambda: self.lblStatus_2.setText(
            "Status: [Task: queued]\nJob înregistrat în server. Coordonate mapate național."
        ))
        QtCore.QTimer.singleShot(4000, lambda: self.lblStatus_2.setText(
            "Status: [Task: processing - 45%]\nDescărcare date LAKI finalizată. Filtrare în curs..."
        ))
        # La pasul final, declanșează încărcarea automată a stratului rezultat în ecran
        QtCore.QTimer.singleShot(6000, self.load_results_into_qgis)

    def load_results_into_qgis(self):
        """Etapa 36: Injectează stratul raster rezultat direct în panoul de control Layers."""
        self.lblStatus_2.setText("Status: [Task: completed - 100%]\nSe încarcă straturile în QGIS...")
        
        # Sursă XYZ temporară (OSM) folosită ca placeholder pentru demonstrarea mapării automate.
        # În producție, acesta va fi înlocuit cu calea absolută a rasterului generat de SAM2 (.tif).
        url_placeholder = "type=xyz&url=https://tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png"
        
        # Instanțierea stratului raster cu motorul PyQGIS
        result_layer = QgsRasterLayer(url_placeholder, "Rezultat_Segmentare_StratumRO", "wms")
        
        if result_layer.isValid():
            # Înregistrarea și afișarea stratului în harta activă
            QgsProject.instance().addMapLayer(result_layer)
            self.lblStatus_2.setText("Status: [Task: completed - 100%]\nProcesare finalizată! Stratul a fost adăugat.")
        else:
            self.lblStatus_2.setText("Status: Eroare la încărcarea stratului rezultat.")

    def closeEvent(self, event):
        self.closingPlugin.emit()
        event.accept()
📊 Status Detaliat: Planul în 75 de Etape al ProiectuluiPlanul de implementare este structurat pe 10 faze tehnice, definind cu precizie ce membru al echipei este responsabil pentru fiecare pas:Membru 1 (Andrei - Lead Developer): QGIS Client, PyQGIS, interfață, comunicare locală, documentație și testare integrată.Membru 2 (Backend & Database Engineer): FastAPI backend, PostGIS SQL, procesare GIS locală (GDAL, PDAL, Docker).Membru 3 (AI/ML Engineer): Model local NVIDIA Nemotron-3 pe Ollama, încărcare model Meta SAM 2, optimizare nuclee CUDA, generare măști.🟩 Faza A: Structură & UI Client (Etapele 1 - 33) — $$STATUS: FINALIZAT 100%$$Etapa 1: Configurare structură directoare (docs, stratum_ro, venv, test). [Membru 1 - FINALIZAT]Etapa 2: Elaborare fișier manifest de înregistrare metadata.txt. [Membru 1 - FINALIZAT]Etapa 3: Configurare fișier resurse Qt (resources.qrc). [Membru 1 - FINALIZAT]Etapa 4: Configurare script de compilare și publicare resurse pb_tool.cfg. [Membru 1 - FINALIZAT]Etapa 5: Inițializare repository Git local și definire reguli excludere în .gitignore. [Membru 1 - FINALIZAT]Etapa 6: Creare fișier de inițializare Python __init__.py pentru structurare pachet. [Membru 1 - FINALIZAT]Etapa 7: Integrare și randare pictogramă oficială plugin (icon.png). [Membru 1 - FINALIZAT]Etapa 8: Redactare documentație primară locală (README.txt și README.html). [Membru 1 - FINALIZAT]Etapa 9: Configurare mediu virtual izolat Python (venv) în folderul principal. [Membru 1 - FINALIZAT]Etapa 10: Legare script principal de încărcare QGIS (stratum_ro.py). [Membru 1 - FINALIZAT]Etapa 11: Proiectare fișier interfață stratum_ro_dockwidget_base.ui în Qt Designer. [Membru 1 - FINALIZAT]Etapa 12: Configurare layout principal vertical (Vertical Layout) cu distanțare dinamică (Spacers). [Membru 1 - FINALIZAT]Etapa 13: Integrare buton selectare AOI (btnSelectAOI) cu iconiță și tooltip. [Membru 1 - FINALIZAT]Etapa 14: Integrare buton acțiune pipeline (btnRunSegmentation). [Membru 1 - FINALIZAT]Etapa 15: Implementare etichetă status principală (lblStatus). [Membru 1 - FINALIZAT]Etapa 16: Implementare etichetă status secundară de progres (lblStatus_2). [Membru 1 - FINALIZAT]Etapa 17: Adăugare dropdown vizualizare CRS în fereastra principală. [Membru 1 - FINALIZAT]Etapa 18: Definire stylesheet custom pentru menținere contrast în Dark Mode/Light Mode. [Membru 1 - FINALIZAT]Etapa 19: Compilare automată interfață XML .ui în cod Python (stratum_ro_dockwidget_base.py). [Membru 1 - FINALIZAT]Etapa 20: Mapare elemente Qt compilate în clasa principală de widget. [Membru 1 - FINALIZAT]Etapa 21: Încărcare resurse grafice compilate în memoria grafică QGIS. [Membru 1 - FINALIZAT]Etapa 22: Definire clasă centrală StratumRO în stratum_ro.py pentru managementul plugin-ului. [Membru 1 - FINALIZAT]Etapa 23: Instanțiere obiect DockWidget la încărcarea interfeței QGIS. [Membru 1 - FINALIZAT]Etapa 24: Creare și adăugare buton rapid în bara de unelte QGIS. [Membru 1 - FINALIZAT]Etapa 25: Legare acțiuni sub-meniu în secțiunea globală Plugins -> StratumRO. [Membru 1 - FINALIZAT]Etapa 26: Suprascriere eveniment închidere widget (closeEvent) pentru eliberare corectă resurse. [Membru 1 - FINALIZAT]Etapa 27: Curățare elemente adăugate în UI la dezactivarea din managerul de module. [Membru 1 - FINALIZAT]Etapa 28: Conectare semnal PyQt5 closingPlugin pentru notificare instanță superioară. [Membru 1 - FINALIZAT]Etapa 29: Creare conexiune consolă QGIS pentru logg-uire mesaje de sistem. [Membru 1 - FINALIZAT]Etapa 30: Configurare scripturi rulare teste automate în folderul test/. [Membru 1 - FINALIZAT]Etapa 31: Definire mediu virtual mock pentru rulare headless a testelor de interfață. [Membru 1 - FINALIZAT]Etapa 32: Înregistrare în sistemul QGIS a suportului de reîncărcare dinamică (Plugin Reloader). [Membru 1 - FINALIZAT]Etapa 33: Validare conformitate arhitecturală PEP8 și rezolvare importuri relative interne. [Membru 1 - FINALIZAT]🟩 Faza B: Gestiune Geodezică & Map Canvas (Etapele 34 - 36) — $$STATUS: FINALIZAT 100%$$Etapa 34: Integrare QgsMapToolExtent pentru desenare interactivă AOI pe ecran (Click stânga lung + tragere dreptunghi). [Membru 1 - FINALIZAT]Etapa 35: Citire automată CRS canvas activ și transformare geodezică instantanee în Stereo 70 (EPSG:31700) prin QgsCoordinateTransform dacă coordonatele diferă. [Membru 1 - FINALIZAT]Etapa 36: Integrare script auto-încărcare straturi. Instanțiere obiect QgsRasterLayer și randarea sa în arborele de straturi direct la finalizarea simulării (stadiu 100%). [Membru 1 - FINALIZAT]🟨 Faza C: Conectivitate Hibridă (Etapele 37 - 40) — $$STATUS: ÎN DERULARE$$Etapa 37: Înlocuire mecanism simulare (Mock) cu cerere HTTP asincronă reală de tip POST utilizând librăria requests. [Membru 1 - ÎN DERULARE]Etapa 38: Tratare excepții de rețea, erori de tip 404/500 și Timeout prin ferestre native de eroare PyQt5 (QMessageBox). [Membru 1 - ÎN DERULARE]Etapa 39: Validare structurală a obiectului GeoJSON înainte de expedierea pachetului către server. [Membru 1 - ÎN DERULARE]Etapa 40: Sincronizare fire de execuție client cu statusul asincron (Polling la /tasks/{id}). [Membru 1 - ÎN DERULARE]🟦 Faza D: Ingestie Date & Database MLOps (Etapele 41 - 50) — $$SARCINI COLEGII BACKEND$$Etapa 41: Configurare mediu backend și ridicare instanță FastAPI pe portul local 8000. [Membru 2 - NEÎNCEPUT]Etapa 42: Definire și expunere endpoint unificat de procesare POST /api/v1/segmentation/process. [Membru 2 - NEÎNCEPUT]Etapa 43: Validare date de intrare (Request payload) folosind scheme riguroase Pydantic. [Membru 2 - NEÎNCEPUT]Etapa 44: Extragere geometrie AOI Stereo 70 și conversie în obiecte geometrice spatiale (Shapely/GeoPandas). [Membru 2 - NEÎNCEPUT]Etapa 45: Mapare cod administrativ SIRUTA primit de la plugin pentru interogarea limitelor administrative. [Membru 2 - NEÎNCEPUT]Etapa 46: Validare topologică de bază (verificarea încadrării corecte a geometriei AOI pe teritoriul României). [Membru 2 - NEÎNCEPUT]Etapa 47: Localizare depozit local de date raster (Ortofotoplanuri multispectrale stocate local). [Membru 2 - NEÎNCEPUT]Etapa 48: Localizare depozit local nori de puncte LiDAR (format .laz / .las). [Membru 2 - NEÎNCEPUT]Etapa 49: Calculare intersecție spațială pentru identificarea automată a fișierelor raster/LiDAR corespunzătoare selecției. [Membru 2 - NEÎNCEPUT]Etapa 50: Decupare dinamică raster (Raster clipping) pe limitele bounding-box-ului din payload. [Membru 2 - NEÎNCEPUT]🟦 Faza E: Preprocesare LiDAR & Aliniere Date (Etapele 51 - 60) — $$SARCINI COLEGII BACKEND$$Etapa 51: Generare ortofotoplan de înaltă rezoluție decupat la nivel de zonă de interes (AOI). [Membru 2 - NEÎNCEPUT]Etapa 52: Încărcare nor de puncte LiDAR în fluxul de procesare local folosind biblioteci specializate (PDAL sau laspy). [Membru 2 - NEÎNCEPUT]Etapa 53: Aplicare filtre de reducere a zgomotului LiDAR și curățare date aberante. [Membru 2 - NEÎNCEPUT]Etapa 54: Clasificare nor de puncte LiDAR în elemente de tip "Sol" (Ground) și "Non-Sol". [Membru 2 - NEÎNCEPUT]Etapa 55: Generare Model Digital al Solului (DSM - Digital Surface Model) din punctele clasificate. [Membru 2 - NEÎNCEPUT]Etapa 56: Generare Model Digital al Terenului (DTM - Digital Terrain Model). [Membru 2 - NEÎNCEPUT]Etapa 57: Calculare Model Normalizat al Înălțimii ($nDSM = DSM - DTM$) pentru izolarea structurilor supraterane. [Membru 2 - NEÎNCEPUT]Etapa 58: Execuție operațiune de potrivire spațială și aliniere pixel-la-pixel între nDSM (LiDAR) și Ortofotoplan (Raster). [Membru 2 - NEÎNCEPUT]Etapa 59: Normalizare valori spectrale și înălțimi (pe scară de la $0$ la $1$) pentru optimizare pipeline rețea. [Membru 2 - NEÎNCEPUT]Etapa 60: Salvare matrice hibridă preprocesată în format binar numpy (.npy) pentru acces rapid. [Membru 2 - NEÎNCEPUT]🟦 Faza F: Orchestrare LLM local & Model Context Protocol (Etapele 61 - 65) — $$SARCINI COLEGII BACKEND / AI$$Etapa 61: Inițializare instanță locală Ollama cu modelul avansat de orchestrare NVIDIA Nemotron-3 pe stația de calcul locală. [Membru 3 - NEÎNCEPUT]Etapa 62: Configurare server Model Context Protocol (MCP) pentru legarea LLM direct la fișierele de sistem ale serverului local. [Membru 2 & 3 - NEÎNCEPUT]Etapa 63: Elaborare prompt de sistem structurat pentru evaluarea datelor de intrare (UAT, SIRUTA, coordonate). [Membru 3 - NEÎNCEPUT]Etapa 64: Analiză și decizie contextuală luată de LLM (ex: determinarea densității vegetației în AOI pentru ajustarea pragurilor de segmentare). [Membru 3 - NEÎNCEPUT]Etapa 65: Transmitere instrucțiuni structurate din agentul LLM către rețeaua neuronală de inferență. [Membru 2 & 3 - NEÎNCEPUT]🟦 Faza G: Inferență Rețea Neuronală Meta SAM 2 (Etapele 66 - 70) — $$SARCINI COLEGII AI$$Etapa 66: Încărcare în memorie a modelului Meta SAM 2 (Segment Anything 2). [Membru 3 - NEÎNCEPUT]Etapa 67: Alocare dinamică memorie GPU (NVIDIA CUDA), verificând menținerea resurselor sub pragul critic (minimum 8GB VRAM). [Membru 3 - NEÎNCEPUT]Etapa 68: Rulare encoder de imagine SAM 2 pe ortofotoplanul decupat pentru extragerea hărților de caracteristici. [Membru 3 - NEÎNCEPUT]Etapa 69: Generare de indicii spațiale (points/bounding box prompts) folosind zonele cu înălțimi ridicate din nDSM (LiDAR) pentru ghidare SAM 2. [Membru 3 - NEÎNCEPUT]Etapa 70: Execuție decoder SAM 2 și generare măști de segmentare binare la nivel de clădire. [Membru 3 - NEÎNCEPUT]🟦 Faza H: Post-procesare, Vectorizare & Validare Cadastrală (Etapele 71 - 75) — $$SARCINI COLEGII BACKEND / AI$$Etapa 71: Conversie măști binare raster în structuri poligonale vectoriale (GDAL polygonize). [Membru 2 - NEÎNCEPUT]Etapa 72: Aplicare algoritm de ortogonalizare a colțurilor clădirilor (reducere poligoane neregulate la unghiuri de $90^\circ$). [Membru 2 & 3 - NEÎNCEPUT]Etapa 73: Filtrare poligoane pe baza ariei minime utile și a pragului de încredere probabilistic (confidence threshold). [Membru 2 - NEÎNCEPUT]Etapa 74: Execuție validare topologică cadastrală (eliminare suprapuneri clădiri, corectare granițe UAT). [Membru 2 - NEÎNCEPUT]Etapa 75: Salvare fișiere finale în formate standardizate: Raster GeoTIFF (.tif) și Vector GeoPackage (.gpkg), generare ID unic de task și returnare răspuns JSON de succes ce va declanșa Etapa 36 în QGIS. [Membru 2 - NEÎNCEPUT]🚀 InstalareCerințe:QGIS ≥ 3.28 (versiune LTR recomandată pentru stabilitate geodezică)Python 3.9+ (instalat nativ împreună cu suita QGIS)GPU NVIDIA cu minimum 8GB VRAM (opțional — există fallback CPU pentru serverul de backend)Backend local activ (vezi secțiunea Cum se rulează local)Pași de instalare:Clonează sau descarcă arhiva acestui repozitoriu privat.Copiază folderul stratum_ro în directorul dedicat pentru plugin-uri externe din QGIS:Windows: %APPDATA%\QGIS\QGIS3\profiles\default\python\plugins\Linux/macOS: ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/În folderul plugin-ului instalat, rulează:pip install pb_tool
pb_tool compile
Deschide QGIS, mergi la meniul de sus: Plugins ➔ Manage and Install Plugins ➔ Installed ➔ bifează căsuța aferentă StratumRO.(Opțional, recomandat în faza de dezvoltare) Instalează plugin-ul Plugin Reloader din depozitul oficial QGIS pentru a reîncărca rapid codul Python după modificări, fără a reporni manual interfața grafică QGIS.💻 Cum se rulează localPornește serverul local de backend scris în FastAPI (urmărește instrucțiunile din repozitoriul dedicat pentru backend sau accesează folderul backend/ dacă rulezi pe o structură monorepo):uvicorn main:app --host 0.0.0.0 --port 8000
Verifică stabilitatea și funcționarea corectă a serverului prin documentația Swagger interactivă: http://localhost:8000/docs.Deschide QGIS, lansează plugin-ul StratumRO din bara laterală/meniu, apasă pe Selectează AOI, definește o zonă pe hartă trăgând un dreptunghi (apasă Click stânga lung și eliberează) și acționează butonul Rulează segmentare.Mod Fallback (Mock Async Polling): În cazul în care serverul de backend nu este pornit sau rețeaua este inaccesibilă, plugin-ul prinde automat excepțiile și inițiază un flux de simulare securizat ([Task: queued] ➔ [Task: processing - 45%] ➔ [Task: completed - 100%]) pentru a putea testa interfața și a simula încărcarea straturilor în mod independent.🔌 Contract de Date API Unificat (Specificații pentru Backend)Endpoint:POST http://localhost:8000/api/v1/segmentation/processRequest JSON (trimis de plugin):{
  "project_name": "Segmentare_Nationala_StratumRO",
  "crs": "EPSG:31700",
  "aoi_selection_mode": "hybrid",
  "geometry": {
    "type": "Polygon",
    "coordinates": [
      [
        [xmin, ymin],
        [xmax, ymin],
        [xmax, ymax],
        [xmin, ymax],
        [xmin, ymin]
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
Response JSON (returnat de backend):{
  "status": "success",
  "task_id": "b3f1c2a4-0e9d-4a7b-9c1e-2f6d8a5e7c10",
  "project_name": "Segmentare_Nationala_StratumRO",
  "results": {
    "raster_path": "/data/output/Oradea_26573/segmentation.tif",
    "vector_path": "/data/output/Oradea_26573/buildings.gpkg",
    "crs": "EPSG:31700",
    "feature_count": 482
  },
  "processing": {
    "model_version": "v1.0-default",
    "confidence_threshold": 0.5,
    "duration_seconds": 47.3
  },
  "errors": []
}
Coduri de eroare gestionate de client (Etapa 38):CodSituațieComportament client404Endpoint indisponibilQMessageBox — server neconfigurat sau oprit500Eroare internă backendQMessageBox — detalii de depanare din campul errorsTimeoutServerul nu răspundeQMessageBox — recomandare retry / verificare server📄 LicențăProiect privat dezvoltat în regim intern de inginerie. Toate drepturile rezervate autorilor (Proprietary / Private code).👥 ContribuțiiProiect dezvoltat de o echipă mică de ingineri; contribuțiile sunt acceptate exclusiv prin Pull Request pe branch-urile de dezvoltare dedicate. Deschideți un Issue înainte de orice propunere de modificare majoră adusă arhitecturii existente.