# Arhitectură Sistem & Contract API — StratumRO

Acest document definește contractul unic de comunicare JSON dintre clientul desktop QGIS și backend-ul FastAPI / MLOps Pipeline.

---

## 1. Endpoint: Inițiere Task Segmentare
* **Metodă HTTP:** POST
* **Cale API:** `/api/v1/segmentation/process`
* **Descriere:** Trimite un singur payload unificat care conține atât datele geometrice (Bounding Box complet România în Stereo 70 EPSG:3844 / EPSG:31700 + Marea Neagră 1975 EPSG:5781), cât și datele administrative (SIRUTA). Dacă una dintre metode nu este activă în UI, cheia respectivă va primi valoarea `null`.

### Payload Unic Cerere (Request Body)
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
        [125000.00, 245000.00],
        [880000.00, 245000.00],
        [880000.00, 770000.00],
        [125000.00, 770000.00],
        [125000.00, 245000.00]
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

---

## 2. Endpoint: Interogare Status Task (Polling)
* **Metodă HTTP:** GET
* **Cale API:** `/api/v1/tasks/{task_id}`
* **Descriere:** Interogare asincronă periodică (de la 2 în 2 secunde, cu un timeout maxim de 5 minute / 150 de încercări) executată de firul de fundal `SegmentationWorker` (PyQt QThread) pentru a monitoriza stadiul de procesare al task-ului înregistrat pe server.

### Răspuns JSON în Curs de Procesare (HTTP 200)
```json
{
  "status": "processing",
  "progress": 45,
  "results": null,
  "errors": []
}
```

### Răspuns JSON la Finalizare cu Succes (HTTP 200)
```json
{
  "status": "completed",
  "progress": 100,
  "results": {
    "raster_path": "/data/output/Oradea_26573/segmentation.tif",
    "vector_path": "/data/output/Oradea_26573/buildings.gpkg"
  },
  "errors": []
}
```

### Răspuns JSON la Eșec (HTTP 200)
```json
{
  "status": "failed",
  "progress": 0,
  "results": null,
  "errors": [
    "Eroare procesare LiDAR: fișier inaccesibil sau invalid"
  ]
}
```

---

## 3. Algoritmi & Modele AI Validate

| Componentă | Model Ales | Alternativă Evaluată | Verdict |
|------------|-----------|---------------------|---------|
| Segmentare Clădiri | Meta SAM 2 | SAM 3 (batch discovery) | ✅ SAM 2 — precizie pixel cu prompt spatial LiDAR |
| Orchestrator LLM | NVIDIA Nemotron-3 (Ollama) | Llama 4 Maverick/Scout | ✅ Nemotron-3 — raționament agentic superior |
| Ortogonalizare | Minimizare unghiulară 90° | Frame Field Learning | ✅ Suficient pt clădiri standard ANCPI |
| Estimare Monoculară | Depth Anything V2 | Metric3D | ⚠️ Metric3D recomandat — oferă adâncime metrică |
| Procesare LiDAR | PDAL + laspy | - | ✅ Complementare — PDAL pipeline + laspy acces date |