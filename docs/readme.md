# StratumRO — Sistem Inteligent de Segmentare Cadastrală (QGIS Plugin)

Pipeline MLOps integrat pentru descărcarea, filtrarea și procesarea automată a datelor geospațiale (LiDAR și Raster) la nivel național, cu suport nativ pentru selecție geometrică pe canvas și coduri administrative SIRUTA.

---

## Descriere Generală / Description / Descripción

### 🇷🇴 Română
Agentic GIS conectează QGIS la un backend AI local (**FastAPI + Ollama LLM + Meta SAM2**) pentru extragerea automată a amprentelor clădirilor din ortofotoplanuri și nori de puncte LiDAR. Plugin-ul permite selectarea unei zone de interes (AOI) direct pe hartă, trimiterea ei către backend pentru segmentare și clasificare AI, iar rezultatul revine ca strat vectorial QGIS gata de utilizare (GeoPackage).

În spate, un agent LLM orchestrează fluxul de lucru prin Model Context Protocol (MCP), coordonând segmentarea, curățarea geometrică și validarea topologică înainte ca rezultatele să ajungă pe hartă. Toată procesarea rulează pe hardware local — datele nu părăsesc mașina. Necesită un serviciu backend local activ; inferența AI este accelerată pe GPU (recomandat minimum 8GB VRAM), cu un mod fallback CPU-only, mai lent, pentru cine nu are placă video compatibilă. Este un proiect activ de cercetare aplicată în geomatică și AI geospațial, dezvoltat de o echipă mică de ingineri; rezultatele sunt gândite să accelereze vectorizarea manuală și trebuie verificate înainte de utilizare în depuneri cadastrale oficiale.

### 🇬🇧 English
Agentic GIS connects QGIS to a local, privacy-preserving AI backend (FastAPI + Ollama LLM + Meta SAM2) to automate building footprint extraction from orthophotos and LiDAR point clouds. The plugin lets you select an area of interest directly on the map canvas, sends it to the backend for AI-driven segmentation and classification, and returns validated building polygons as a ready-to-use QGIS vector layer (GeoPackage).

Under the hood, an LLM agent orchestrates the workflow via the Model Context Protocol (MCP), coordinating segmentation, geometric cleanup, and topology validation before results reach the map. All processing runs on local hardware — no orthophoto or point cloud data leaves the machine. Requires a running local backend service; AI inference is GPU-accelerated (8GB+ VRAM recommended), with a slower CPU-only fallback mode for machines without a compatible GPU. This is an active applied-research project in geomatics and geospatial AI, developed by a small engineering team; outputs are intended to speed up manual vectorization and should be reviewed before use in official cadastral submissions.

### 🇪🇸 Español
Agentic GIS conecta QGIS con un backend de IA local que preserva la privacidad (FastAPI + Ollama LLM + Meta SAM2) para automatizar la extracción de huellas de edificios a partir de ortofotos y nubes de puntos LiDAR. El plugin permite seleccionar un área de interés directamente sobre el lienzo del mapa, la envía al backend para segmentación y clasificación mediante IA, y devuelve los polígonos de edificios validados como una capa vectorial de QGIS lista para usar (GeoPackage).

Internamente, un agente LLM orquesta el flujo de trabajo mediante el Model Context Protocol (MCP), coordinando la segmentación, la limpieza geométrica y la validación topológica antes de que los resultados lleguen al mapa. Todo el procesamiento se ejecuta en hardware local — ningún dato sale de la máquina. Requiere un servicio backend local en ejecución; la inferencia de IA se acelera por GPU (se recomiendan 8GB+ de VRAM), con un modo de respaldo solo-CPU, más lento, para equipos sin GPU compatible. Es un proyecto activo de investigación aplicada en geomática e IA geoespacial, desarrollado por un equipo pequeño de ingenieros; los resultados están pensados para acelerar la vectorización manual y deben revisarse antes de usarse en presentaciones catastrales oficiales.

---

## Instalare

**Cerințe:**
- QGIS ≥ 3.28 (LTR recomandat)
- Python 3.9+ (inclus în instalarea QGIS)
- GPU NVIDIA cu minimum 8GB VRAM (opțional — există fallback CPU pentru backend)
- Backend local activ (vezi secțiunea *Cum se rulează*)

**Pași:**
1. Clonează sau descarcă acest repository.
2. Copiază folderul `StratumRO` în directorul de plugin-uri QGIS:
   - Linux/macOS: `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/`
   - Windows: `%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins\`
3. În folderul pluginului, rulează:
   ```bash
   pip install pb_tool
   pb_tool compile
   ```
4. Deschide QGIS → **Plugins → Manage and Install Plugins → Installed** → bifează **StratumRO**.
5. (Opțional, recomandat în dezvoltare) Instalează plugin-ul **Plugin Reloader** din QGIS Plugin Repository pentru reîncărcare rapidă fără restart QGIS.

---

## Cum se rulează local

1. Pornește backend-ul FastAPI (vezi repo-ul echipei de backend / folderul `backend/` dacă e monorepo):
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```
2. Verifică că serverul răspunde la `http://localhost:8000/docs`.
3. Deschide QGIS, activează pluginul StratumRO, selectează un AOI pe canvas și apasă **Run Segmentation**.
4. Dacă backend-ul nu e disponibil, pluginul intră automat în modul **Mock Async Polling** (etichete `[Task: queued]` → `[Task: processing]` → `[Task: completed]`) pentru testarea fluxului UI fără server real.

---

## Status Proiect: Planul în 75 de Etape

Coordonare între componenta desktop (**Geomatică / Client QGIS**) și cea de server (**Backend / MLOps**):

### 🟨 I. Componenta Client QGIS (Etapele 1 - 36) — [STATUS: ÎN DERULARE]
Structura de bază a pluginului este generată (skeleton via QGIS Plugin Builder); logica UI, captura spațială și integrarea PyQGIS sunt în curs de implementare.
*   **Etapele 1 - 33 (Arhitectură de Bază & UI):** Structurarea pachetului, scrierea metadatelor (`metadata.txt`), configurarea fișierului de resurse, generarea interfeței `.ui` în Qt Designer și separarea logicii în clase decuplate (`stratum_ro_dockwidget_base.py`). *Skeleton generat; UI și separarea logicii în lucru.*
*   **Etapa 34 (Selecție AOI Geodezică):** Integrarea clasei native `QgsMapToolExtent` pentru desenarea bounding-box-ului pe ecran, interceptarea CRS-ului activ și transformarea coordonatelor în proiecția națională **Stereo 70 (EPSG:31700)** via `QgsCoordinateTransform`. *Planificat, neimplementat.*
*   **Etapa 35 (Logică Client Asincronă):** Comportament non-blocking; fallback de *Asynchronous Mock Polling* bazat pe `QtCore.QTimer.singleShot`, cu etichete de status dinamice fără a bloca procesele QGIS. *Planificat, neimplementat.*
*   **Etapa 36 (Auto-Load Layers):** Injectare automată a rezultatului segmentării ca `QgsRasterLayer` în *Layers Panel* la finalizarea task-ului. *Planificat, neimplementat.*

### ⬜ II. Componenta de Integrare Hibridă (Etapele 37 - 40) — [STATUS: NEÎNCEPUT]
*   **Etapa 37 (Conexiunea de Rețea Reală):** Trecerea de la mock local la cereri HTTP reale către backend; se așteaptă activarea endpoint-ului de către echipa de backend.
*   **Etapa 38 (Gestiunea Erorilor & Excepții):** Tratarea codurilor 404/500/timeout și afișare `QMessageBox` la eșec.
*   **Etapele 39 - 40 (Validare Payload local):** Verificarea integrității JSON înainte de trimitere.

### ⬜ III. Componenta Backend & MLOps (Etapele 41 - 75) — [SARCINI ECHIPA BACKEND]
*   **Etapele 41 - 55 (FastAPI & Pipeline Ingestie Date):** server pe portul `8000`, endpoint `POST /api/v1/segmentation/process`, parsare geometrie Stereo 70, interogare pe cod SIRUTA, decupare raster/LiDAR pe bounding box.
*   **Etapele 56 - 68 (Orchestrare LLM & Inferență Meta SAM 2):** agent LLM via MCP/Ollama, inferență SAM 2, accelerare GPU (NVIDIA 8GB+ VRAM) cu fallback CPU.
*   **Etapele 69 - 75 (Post-Procesare Geodezică & Export):** vectorizare, ortogonalizare clădiri, validare topologică, export `.tif`/`.gpkg`, răspuns JSON cu căi/URL-uri către fișiere.

---

## Caracteristici Tehnice Arhitecturale (Client QGIS)

*   **`stratum_ro_dockwidget_base.py` (Mecanicul):** Fișier structural generat automat din Qt Designer (`.ui`). Conține doar dispunerea butoanelor și etichetelor. Nu se modifică manual, pentru a evita suprascrierea la regenerare.
*   **`stratum_ro_dockwidget.py` (Pilotul):** Conține logica geodezică și de rețea scrisă manual — instrumentele PyQGIS și apelurile asincrone.

---

## Contract de Date API Unificat (Specificații pentru Backend)

Endpoint: `POST http://localhost:8000/api/v1/segmentation/process`

### Request JSON (trimis de plugin):
```json
{
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
```

### Response JSON (returnat de backend):
```json
{
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
```

**Coduri de eroare gestionate de client (Etapa 38):**
| Cod | Situație | Comportament client |
|---|---|---|
| 404 | Endpoint indisponibil | `QMessageBox` — server neconfigurat/pornit |
| 500 | Eroare internă backend | `QMessageBox` — detalii din câmpul `errors` |
| Timeout | Server nu răspunde în timp util | `QMessageBox` — sugestie retry / verificare server |

---

## Licență

*(de completat — ex: MIT, GPL-3.0)*

## Contribuții

Proiect dezvoltat de o echipă mică; contribuțiile sunt binevenite via Pull Request. Deschide un Issue înainte de schimbări majore de arhitectură.