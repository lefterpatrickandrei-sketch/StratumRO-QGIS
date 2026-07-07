# Arhitectură Sistem & Contract API — StratumRO

Acest document definește contractul unic de comunicare JSON dintre clientul desktop QGIS și backend-ul FastAPI / MLOps Pipeline.

---

## 1. Endpoint: Inițiere Task Segmentare
* **Metodă HTTP:** POST
* **Cale API:** `/api/v1/segmentation/process`
* **Descriere:** Trimite un singur payload unificat care conține atât datele geometrice (Bounding Box complet România în EPSG:31700), cât și datele administrative (SIRUTA). Dacă una dintre metode nu este activă în UI, cheia respectivă va primi valoarea `null`.

### Payload Unic Cerere (Request Body)
```json
{
  "project_name": "Segmentare_Nationala_StratumRO",
  "crs": "EPSG:31700",
  "aoi_selection_mode": "hybrid",
  "geometry": {
    "type": "Polygon",
    "coordinates": [
      [
        [150000.00, 210000.00],
        [840000.00, 210000.00],
        [840000.00, 770000.00],
        [150000.00, 770000.00],
        [150000.00, 210000.00]
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