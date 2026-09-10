# Arhitectură Sistem & Evoluție Tehnică — StratumRO

> [!NOTE]
> **Notă Istorică de Versiune:**
> - **Faza 1 (Arhitectură Istorică):** Protocolul client-server REST FastAPI descris în Secțiunile 1–2 reprezintă proiectarea inițială pentru procesare distribuită/headless.
> - **Faza 2 (Arhitectură Curentă Activă):** Platformă integrată nativ în **QGIS Desktop & QGIS Processing Framework**, utilizând procesare locală prin Python (`stratum_ro`), fuziune nDSM + SAM2, motor de inferență ONNX Runtime / DirectML, export direct TopoLT CAD (`1CC`/`2CC`) și extrudare 3D LoD1 (`MultiPolygonZ` & CityJSON v1.1).

---

## 1. [Istoric / Opțional] Endpoint: Inițiere Task Segmentare (FastAPI v1)
* **Metodă HTTP:** POST
* **Cale API:** `/api/v1/segmentation/process`
* **Descriere:** Protocol pentru servere de calcul la distanță. Trimite un payload unificat conținând parametrii geometrici și administrativi.

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

## 2. [Istoric / Opțional] Endpoint: Interogare Status Task (Polling v1)
* **Metodă HTTP:** GET
* **Cale API:** `/api/v1/tasks/{task_id}`
* **Descriere:** Monitorizare asincronă a progresului pentru backend-uri remote.

---

## 3. Algoritmi & Modele AI: Analiză Tehnico-Științifică

| Componentă | Metodă / Model Ales | Alternativă Evaluată | Statut de Evidență & Realitate Tehnică |
| :--- | :--- | :--- | :--- |
| **Segmentare Clădiri** | Fuziune Meta SAM 2 + nDSM | Watershed clasic / SAM 3 | **IMPLEMENTAT & MĂSURAT:** IoU 0.621–0.818 pe setul Tier-1 (29 clădiri). Constrângerea altimetrică elimină umbrele și vegetația joasă. |
| **Inferență Zero-CUDA** | ONNX Runtime + DirectML | PyTorch + CUDA manual | **IMPLEMENTAT (SCHELET):** Wrapper de provider DirectML/CPU funcțional. Conversia și validarea numerică a greutăților SAM2 ONNX sunt în curs. |
| **Post-Procesare** | Ortogonalizare 90° Canonică | Simplificare Ramer-Douglas | **IMPLEMENTAT & TESTAT:** Potrivire dreptunghi rotit (4 noduri) pentru corpuri simple; `buildingregulariser` pentru poligoane complexe. |
| **Aliniere Cadastrală** | Auto-Snap to Boundary (Procrustes SVD) | Măsurători terestre RTK | ⚠️ **TEORETIC / NEVALIDAT PE TEREN:** Procrustes oferă o potrivire matematică pe contururi WFS ANCPI existente. **NU constituie precizie de teren $\pm 1.4\text{ cm}$** în absența unei campanii GNSS RTK independente. |
| **Livrabile Cadastru** | TopoLT (`1CC`, `2CC`, `CP`, `VARFURI`, `NUMERE_PCT`) + PAD | Export DXF generic | **IMPLEMENTAT & TESTAT:** Generare automată tabel PAD (Ordinul 600/2023) și fișier de schimb `.cp` pentru eTerra. |
| **Reconstrucție 3D** | LoD1 Solid Shell (`MultiPolygonZ`) & CityJSON 1.1 | Poligoane 2D plate | **IMPLEMENTAT & TESTAT:** Solide etanșe bazate pe $Z_{\text{sol}}$ și $Z_{\text{cornisa}}$ vizualizabile nativ în QGIS 3D Canvas. RANSAC 3D pentru orientare acoperiș. |
| **Procesare LiDAR** | `laspy` + `scipy.ndimage` | PDAL pipeline extern | **IMPLEMENTAT & TESTAT:** Extragere nDSM și separare pe clase morfologice în Stereo 70 (EPSG:3844). |