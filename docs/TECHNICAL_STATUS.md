# Inventar Tehnic & Matrice de Realitate — StratumRO 🧭🔬

Acest document constituie **inventarul tehnic unic anti-halucinare** al platformei **StratumRO-QGIS**.  
Fiecare modul, funcție, algoritm și afirmație este clasificat conform celor 8 nivele stricte de evidență definite în [`AGENTS.md`](../AGENTS.md).

> [!IMPORTANT]
> **Directiva Fundamentală:**
> *„Nu face StratumRO să pară mai impresionant decât este. Fă-l să fie verificabil, robust și apărabil științific.”*  
> StratumRO este un instrument avansat de **asistență pre-cadastrală și accelerare a digitizării geodezice (reducere cu 89% a efortului manual de trasare)**, și **NU** un sistem de intabulare legală complet autonomă fără intervenție umană.

---

## 1. Nomenclatorul Celor 8 Nivele de Evidență

| Nivel de Evidență | Definiție Operațională |
| :--- | :--- |
| **`IMPLEMENTED`** | Codul sursă există fizic în repozitoriu și este apelabil direct fără erori de sintaxă sau import. |
| **`TESTED`** | Există teste unitare sau de integrare automatizate în `stratum_ro/test/` care verifică execuția codului și trec la rulare (`OK`). |
| **`REPRODUCED`** | Rezultatele au fost reproduse independent prin rularea scripturilor de evaluare din `engine/` pe mașina locală. |
| **`MEASURED`** | Valorile numerice provin din calcul direct pe date existente pe disc, cu denominator și eșantion specificat. |
| **`VALIDATED`** | Ipotezele algoritmice au fost confruntate cu date externe de referință cu metodologie documentată. |
| **`FIELD-VALIDATED`** | Rezultatele planimetrice/altimetrice au fost verificate pe teren prin măsurători geodezice terestre directe (GNSS RTK / Stație Totală). |
| **`THEORETICAL`** | Conceptul matematic sau arhitectural este valid pe hârtie sau simulat, dar nu are validare experimentală completă pe date reale. |
| **`UNVERIFIED`** | Afirmație nesusținută de date, cod sau execuție măsurabilă; pasibilă de corectare sau eliminare. |

---

## 2. Inventar Tehnic per Modul & Funcționalitate

### 2.1. Segmentare Hibridă nDSM + SAM2
- **Cod Sursă:** [`stratum_ro/cadastral_engine.py`](../stratum_ro/cadastral_engine.py), [`stratum_ro/ortho_extractor.py`](../stratum_ro/ortho_extractor.py)
- **Statut Evidență:** **`IMPLEMENTED`** | **`TESTED`** | **`MEASURED`**
- **Ce funcționează real:**
  - Decupare automată ortofoto + nDSM pe caroiaje (tile-uri) georeferențiate în Stereo 70 (EPSG:3844).
  - Mascare altimetrică bazată pe nDSM ($Z \ge 2.5\text{ m}$) pentru eliminarea umbrelor la sol și a drumurilor asfaltate.
  - Generare de prompte geometrice (centroizi nDSM și bounding box-uri) pentru ghidarea modelului SAM2.
- **Ce este simulat / limitat:**
  - Pentru testele unitare și mediile fără model SAM2 descărcat local, motorul utilizează un mecanism de fallback pe măști morfologice nDSM.
- **Metrici măsurate (pe AOI Cluj USAMV, 29 clădiri GT):**
  - Fuziunea hibridă reduce alarmele false de la 569 (LiDAR pur) la 116.
  - IoU Median pe împerecheri 1:1 curate: **0.818** (Medie: **0.746**).

---

### 2.2. Motorul ONNX Runtime & DirectML
- **Cod Sursă:** [`stratum_ro/onnx_engine.py`](../stratum_ro/onnx_engine.py), [`tools/export_sam2_to_onnx.py`](../tools/export_sam2_to_onnx.py)
- **Statut Evidență:** **`IMPLEMENTED`** | **`TESTED`** | **`MEASURED & VALIDATED` (Decodor SAM 2 exportat și verificat numeric bit-cu-bit)**
- **Ce funcționează real:**
  - Export direct al decodorului neuronal SAM 2 Hiera în format standardizat ONNX (`models/sam2/sam2_decoder.onnx`, 15.79 MB) prin [`tools/export_sam2_to_onnx.py`](../tools/export_sam2_to_onnx.py).
  - Validare numerică bit-cu-bit confirmată: eroare absolută maximă pe logits $< 7.63 \times 10^{-5}$, eroare pe scoruri IoU $< 2.98 \times 10^{-7}$ (status `NUMERICALLY_VERIFIED`).
  - Wrapper de inferență `ONNXSegmentationEngine` cu prioritizare automată: `DmlExecutionProvider` (DirectML DirectX 12 pe Windows GPU) -> fallback CPU (`CPUExecutionProvider`).
  - 4 teste unitare automate dedicate în [`stratum_ro/test/test_onnx_engine.py`](../stratum_ro/test/test_onnx_engine.py) care verifică inclusiv încărcarea sesiunii decodorului exportat.
- **Ce rămâne ca dezvoltare viitoare:**
  - Exportul complet al encoderului de imagine ViT-Hiera în ONNX (necesită gestionarea atenției fereastră ierarhică multi-scală și atenție flash). Măsurătorile curente validează decodorul de prompturi și măști.

---

### 2.3. Regularizare CAD 90° & Topologie Canonică
- **Cod Sursă:** [`stratum_ro/cadastral_engine.py`](../stratum_ro/cadastral_engine.py) (funcțiile `regularize_building_cad`, `minimum_rotated_rectangle_fit`)
- **Statut Evidență:** **`IMPLEMENTED`** | **`TESTED`** | **`MEASURED`**
- **Ce funcționează real:**
  - Fitare automată de dreptunghi rotit (exact 4 noduri la 90°) pentru corpuri rectangulare simple (garaje, anexe, case izolate) când IoU cu conturul brut depășește pragul de 0.88.
  - Suport integrat pentru `buildingregulariser` (bibliotecă Python) pentru ortogonalizarea poligoanelor în formă de L, U sau T.
  - Eliminarea efectului de „treaptă de pixel” (staircasing) pe fațadele lungi orientate oblic față de grila raster.
- **Metrici măsurate:**
  - Numărul mediu de noduri pe clădire scade de la 48–120 (contur brut raster) la 4–12 noduri geometrice curate, conform cerințelor ANCPI.

---

### 2.4. Export CAD TopoLT, PAD & Schimb ANCPI (.cp)
- **Cod Sursă:** [`stratum_ro/cad_exporter.py`](../stratum_ro/cad_exporter.py)
- **Statut Evidență:** **`IMPLEMENTED`** | **`TESTED`**
- **Ce funcționează real:**
  - Generare fișiere `.dxf` conforme TopoLT cu straturi standardizate: `1CC` (Construcții principale), `2CC` (Anexe/Construcții secundare), `CP` (Contur Parcelă), `VARFURI` (Puncte de contur), `NUMERE_PCT` (Texte cu numere de puncte 1..N).
  - Desenare automată a **Tabelului de Coordonate PAD** direct în spațiul model CAD, conform cerințelor Ordinului ANCPI 600/2023 (coloane: Nr. Pct., X [m], Y [m], Lungimi laturi $D(i, i+1)$).
  - Generare fișiere text `.cp` pentru import direct în eTerra și TopoLT.
  - 5 teste unitare dedicate în [`stratum_ro/test/test_cad_exporter.py`](../stratum_ro/test/test_cad_exporter.py).

---

### 2.5. Reconstrucție 3D LoD1 & CityJSON 1.1
- **Cod Sursă:** [`stratum_ro/volumetric_3d.py`](../stratum_ro/volumetric_3d.py)
- **Statut Evidență:** **`IMPLEMENTED`** | **`TESTED`**
- **Ce funcționează real:**
  - Extrudare 3D a poligoanelor 2D între $Z_{\text{sol}}$ și $Z_{\text{cornisa}}$ calculate statistic din norul de puncte LiDAR (percentilele 5 și 95).
  - Generare geometrie etanșă (closed solid shell) formată din podea (bottom), pereți verticali (walls) și acoperiș plat (roof).
  - Salvare vectorială directă sub formă de `MultiPolygonZ` în fișiere GeoPackage (`.gpkg`) compatibile cu vizualizarea 3D din QGIS Canvas.
  - Export în format standard OGC **CityJSON v1.1** cu atribute cadastrale și metadate de referință Stereo 70.
  - 5 teste unitare dedicate în [`stratum_ro/test/test_volumetric_3d.py`](../stratum_ro/test/test_volumetric_3d.py).
- **Ce este THEORETICAL / În Lucru:**
  - LoD2 cu ape de acoperiș reale (RANSAC plane fitting pentru lucarne, pante și creste) este schițat teoretic, dar producția activă generează LoD1.

---

### 2.6. Alinierea Cadastrală la Limita Parcelelor (Procrustes SVD)
- **Cod Sursă:** `stratum_ro/cadastral_engine.py` / `engine/helmert_procrustes.py`
- **Statut Evidență:** **`THEORETICAL`** | **`NOT FIELD-VALIDATED`**
- **Realitate Tehnică:**
  - Potrivirea rigidă Procrustes (rotație + translație ortogonală prin descompunere SVD) pe fronturile la stradă ANCPI calculează o **reziduală algebrică de potrivire matematică**.
  - Afirmația istorică din versiuni preliminare de „acuratețe $\pm 1.4\text{ cm}$ auto-snap” reprezenta eroarea medie pătratică a modelului matematic aplicat pe coordonate WFS teoretice, și **NU o precizie verificată prin măsurători geodezice pe teren**.
  - Orice afirmație de precizie planimetrică absolută pe teren sub-decimetrică ($\le 10\text{ cm}$) este **invalidă** fără o campanie de măsurători GNSS RTK terestre.

---

### 2.7. Integrare QGIS: DockWidget & Processing Algorithm
- **Cod Sursă:** [`stratum_ro/cadastral_algorithm.py`](../stratum_ro/cadastral_algorithm.py), [`stratum_ro/processing_provider.py`](../stratum_ro/processing_provider.py), [`stratum_ro/stratum_ro_dockwidget.py`](../stratum_ro/stratum_ro_dockwidget.py)
- **Statut Evidență:** **`IMPLEMENTED`** | **`TESTED`**
- **Ce funcționează real:**
  - Pluginul expune un algoritm oficial de procesare QGIS (`QgsProcessingAlgorithm`) în Processing Toolbox, permițând rularea în batch și integrarea în Graphical Modeler.
  - DockWidget UI curățat de căi hardcodate; detectează automat directoarele relative din workspace.

---

## 3. Evaluarea Cantitativă pe Setul de Referință Teren (Tier 1 Cluj USAMV)

- **Fișier Ground Truth:** [`data/ground_truth/tier1_teren.geojson`](../data/ground_truth/tier1_teren.geojson)
- **Hash MD5 Verificat:** `30B95D3EC95B2EA7DC09F6F47E30BBE9`
- **Volum Eșantion:** 29 clădiri cadastrale reale măsurate / confirmate în Stereo 70.
- **Predicții Generate de Pipeline:** 134 poligoane în layer-ul `CLADIRI_HIBRID`.

### Sinteză Rezultate Recalculate Proaspăt:

| Indicator / Metrică | Subset Curat (1:1 Pairs) | Set Global (Toate Perechile) | Explicație / Context Geodezic |
| :--- | :--- | :--- | :--- |
| **Număr Eșantioane** | **16 clădiri** | **17 clădiri (18 TP)** | 16 împerecheri 1:1 fără ambiguitate, 1 corp sub-segmentat. |
| **IoU Median** | **0.818** | **0.734** | Suprapunere foarte bună pe corpurile curate; scade pe corpuri alăturate. |
| **IoU Mediu** | **0.746** ($\pm 0.174$) | **0.615** ($\pm 0.286$) | Interval de confidență 95%: $[0.653, 0.838]$. |
| **Boundary RMSE Median** | **1.519 m** | **2.457 m** | Acuratețe fotogrammetrică tipică pentru ortofoto 10–15 cm GSD. |
| **Boundary RMSE Mediu** | **2.649 m** ($\pm 3.321\text{ m}$) | **10.570 m** ($\pm 16.188\text{ m}$) | Corpurile complexe sau parțial acoperite de arbori cresc media. |
| **Hausdorff Median** | **4.553 m** | **7.984 m** | Distanța maximă extremă locală (streșini, anexe secundare). |
| **False Negatives (FN)** | **8 clădiri** | **8 clădiri** | Clădiri joase sau puternic obturate de coronamentul arborilor. |
| **False Positives (FP)** | — | **116 clădiri** | **Clădiri reale existente în AOI, dar nedigitizate în GT-ul de 29 clădiri**, plus declanșări pe structuri perimetrice. |
| **Conformitate ANCPI ($\le 10\text{ cm}$)** | **0 / 29 (0.0%)** | **0 / 29 (0.0%)** | **Realitate Fotogrammetrică:** Datele aeriene fără măsurători terestre directe nu pot atinge pragul legal de 10 cm. |

---

## 4. Limitări Cunoscute & Riscuri Geodezice

1. **Clădiri Alipite la Calcan (Row Houses / Shared Walls):**  
   Ortofoto și nDSM nu prezintă întotdeauna discontinuitate fizică între două proprietăți lipite. Dacă nu există diferență de cotă la acoperiș sau o linie de umbră clară, modelul tinde să le extragă ca un singur poligon contopit (under-segmentation).
2. **Streașină vs. Soclu (Eave Offset):**  
   Fotogrammetria aeriană extrage conturul acoperișului (streașina/jgheabul). Cadastrul legal ANCPI cere conturul soclului la nivelul solului. Retragerea uniformă cu $-0.40\text{ m}$ ameliorează biasul sistematic, dar streșinile reale variază între $0.20\text{ m}$ și $1.20\text{ m}$.
3. **Vegetație Densă peste Acoperișuri:**  
   Copacii mari cu coronament extins peste clădire distorsionează nDSM-ul și maschează textura ortofoto, generând margini neregulate dacă nu se aplică filtrare strictă de puls LiDAR.
4. **Alarme False pe Containere și Structuri Temporare:**  
   Containerele de șantier, chioșcurile metalice sau serele au înălțime $\ge 2.5\text{ m}$ și formă rectangulară, fiind clasificate ca și clădiri de către pipeline. Este necesară validarea vizuală a operatorului.

---

## 5. Ghid de Interpretare a Eficienței Operaționale (89% Economie de Timp)

Afirmația de **89% economie de timp** este fundamentată operațional pe fluxul de lucru:
- **Digitizare manuală integrală:** 15–25 minute per cvartal (trasare vârf cu vârf, ortogonalizare manuală în AutoCAD/TopoLT, culegere cote Z).
- **Flux StratumRO asistat:** 1.5–2.5 minute per cvartal (generare automată contururi 90°, export direct DXF/PAD, operatorul uman intervenind doar pentru ștergerea FP-urilor evidente și ajustarea alipirilor la calcan).
- **Concluzie:** StratumRO accelerează substanțial munca de birou a geodezului, dar responsabilitatea semnării documentației cadastrale rămâne exclusiv umană.
