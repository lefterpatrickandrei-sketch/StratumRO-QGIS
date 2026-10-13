# StratumRO — Raport Diagnostic și Reparație T10 (Antigravity)

**Dată:** 2026-10-13  
**Autor:** Antigravity (Primary Development & Execution Engine)  
**Status Implementare:** `IMPLEMENTED_AND_EXECUTED` (Executat cu succes pe date locale: SAM2, ortofoto nativ și nor de puncte LiDAR).  
**Status Ipoteză T10:** `PENDING_OWNER_REVIEW` (Conform protocolului, nicio geometrie nouă nu este declarată acceptată fără verdictul proprietarului).  

---

## 1. Context și Verdictul Proprietarului

Conform `workspace/reviews/retry_six_release_20261013/owner_feedback.json` și protocolului decizional `docs/STRATUMRO_AGENT_DECISION_PROTOCOL.md`:
* **Lotul 1 (8 scene / 9 corpuri):** ACCEPTAT integral de proprietar (inclusiv partiționarea corpurilor B5).
* **Lotul suplimentar (T01–T04):** ACCEPTAT.
* **Cele 6 cazuri de retry (`six_before_after.png`):**
  - **T05, T06, T07:** ACCEPTATE (geometrii înghețate și prezervate fără regresii).
  - **T08, T09:** RESPINSE (`NO_SUPPORTED_ROOF_SEED`, fără geometrie forțată).
  - **T10 (`REF_TIER1_006:B00011`):** **PARȚIAL EXECUTAT, NEACCEPTAT CA REZULTAT FINAL** (*"t10 nu e bun am zis ca e partial facut"*).

---

## 2. Diagnoza Concretă a Defectului T10 (Cauze Confirmate vs Ipoteze)

### 2.1 Defectul Observat în `T10:A1`
Geometria parțială anterioară `T10:A1` din `retry_six.gpkg` (layer `CORPURI_RECTIFICATE`):
* Avea **6 noduri** și o suprafață parțială de **115.4 m²**.
* Prezenta o decupare/treaptă falsă pe latura sud-estică a acoperișului.
* Era trunchiată spre sud la coordonata $Y \approx 585661.05$.
* Pe ortofotoplanul nativ (`ortofoto_cluj_usamv_rgb.vrt` / tile `cache_tile_Cluj-1-0_halo.tif`), clădirea T10 este o structură unitară, rectangulară, din țiglă ceramică roșiatică-maronie, cu lățimea de ~10 m și lungimea de ~14.5 m (suprafață reală ~144 m²), mărginită la vest de un corp jos cu acoperiș gri.

### 2.2 Cauzele Reale Confirmate prin Dovezi Senzoriale

1. **Trunchierea ferestrei de căutare (Bounding Box Truncation) în `roof_retry.py`:**
   - Masca istorică respinsă asociată lui T10 avea `ymin = 585666.70`, în timp ce clădirea reală se extinde spre sud până la `ymin = 585657.30`.
   - Formula anterioară `geometry.buffer(4).bounds` extindea doar până la `ymin = 585662.70`.
   - Modulul `sam2_engine.py` decupa crop-ul de inferență la aceste limite, retezând fizic masca la `y = 585661.05` și amputând 3.7 m din clădire.

2. **Filtrarea coroanei de copac pe streașina sud-estică (Tree Canopy Overhang Filter):**
   - Direct deasupra cornișei sud-estice există o coroană de copac care generează puncte LiDAR nDSM înalte (11.4–13.0 m, unde înălțimea medie a clădirii este de 6.86–7.60 m).
   - Deși camera aeriană vede clar textura roșiatică a țiglei sub crengi, condiția `h <= local_h + 4.0` din `trim_retry_roof_surface` decupa acești pixeli, săpând o treaptă artificială în mască.

3. **Efectul în Regularizarea Geometrică:**
   - Cu masca decupată atât la sud cât și la streașină, optimizatorul rectangular nu a putut atinge pragul de suport $\ge 92\%$ pentru un dreptunghi de 4 vârfuri, căzând pe fallback-ul `SUPPORTED_ORTHOGONAL` cu 6 noduri și „înghețând” treapta falsă.

---

## 3. Modificările Implementate în StratumRO

Modificările au fost realizate conform regulilor stricte: fără ramuri `if id == 'T10'`, fără coordonate manuale și fără forțarea nejustificată a formelor geometrice:

1. **Padding adaptiv bazat pe anvergură minimă în `retry_roof_geometry` ([`stratum_ro/roof_retry.py`](file:///C:/Users/lefpa/Downloads/QGIS-AI/stratum_ro/roof_retry.py)):**
   ```python
   span_x = max(geometry.bounds[2] - geometry.bounds[0], 1.0)
   span_y = max(geometry.bounds[3] - geometry.bounds[1], 1.0)
   pad_x = max(4.0, (24.0 - span_x) / 2.0)
   pad_y = max(4.0, (24.0 - span_y) / 2.0)
   ```
   * Această formulă generică oferă o fereastră minimă de 24 m pentru fragmente retezate, fără a afecta clădirile mari deja complete (T05, T06, T07 rămân neatinse).

2. **Gestionarea suprapunerilor de vegetație pe acoperișuri roșiatice în `trim_retry_roof_surface` ([`stratum_ro/roof_retry.py`](file:///C:/Users/lefpa/Downloads/QGIS-AI/stratum_ro/roof_retry.py)):**
   ```python
   reddish = (r - g > 14) & (r - b > 14) & (r > 55)
   high_overhang = (seed['red_fraction'] >= 0.50) & (brown | reddish) & ~vegetation
   height_ceiling = np.where(high_overhang, local_h + 8.0, local_h + 4.0)
   ```
   * Permite recuperarea versantului de țiglă de sub ramuri, menținând totodată plafonul strict de înălțime pe acoperișuri neutre (protejând separarea corpurilor la T05).

---

## 4. Teste de Regresie și Verificare

1. **Teste unitare în [`stratum_ro/test/test_roof_retry.py`](file:///C:/Users/lefpa/Downloads/QGIS-AI/stratum_ro/test/test_roof_retry.py):**
   * S-a reparat fixture-ul `_build_lidar_data` adăugând câmpurile `'observed'` și `'vegetation'`.
   * Testul `test_trim_retry_roof_surface_retains_previously_excluded_reddish_tile_and_rejects_vegetation` validează pixelul de țiglă `[110, 76, 75]` la $h=11.5$m sub crengi, demonstrând eșecul pe codul vechi și succesul pe codul nou, respingând totodată vegetația pură.
   * Rularea suitei `stratum_ro/test/test_roof_retry.py`: **10 teste rulate, 10 trecute, 0 eșuate**.
   * Rularea pachetului complet de geometrie (`test_roof_retry.py`, `test_roof_retry_integration.py`, `test_roof_body_recovery_partition.py`, `test_roof_simple_geometry.py`): **24 teste rulate, 24 trecute, 0 eșuate**.

2. **Verificarea non-regresiei pe toate cele 6 cazuri:**
   * **T05:** 2 corpuri păstrate (1094.8 m² cu 6 noduri; 184.0 m² cu 4 noduri) — identic cu starea aprobată.
   * **T06:** 1 corp păstrat (211.5 m² cu 6 noduri) — identic cu starea aprobată.
   * **T07:** 1 corp păstrat (363.3 m² cu 10 noduri) — identic cu starea aprobată.
   * **T08 & T09:** 0 corpuri (`NO_SUPPORTED_ROOF_SEED`) — identic cu starea aprobată.
   * **T10:** 1 corp rectangular recuperat cu 4 noduri (`SUPPORTED_CORE_RECTANGLE`, 143.8 m², suport 0.950, acoperire 0.973, IoU 0.925).

---

## 5. Artefacte Livrate

Directorul de livrare dedicat: [`workspace/reviews/t10_antigravity_20261013/`](file:///C:/Users/lefpa/Downloads/QGIS-AI/workspace/reviews/t10_antigravity_20261013)

* **Planșa comparativă ÎNAINTE / DUPĂ:**
  - [`t10_before_after.png`](file:///C:/Users/lefpa/Downloads/QGIS-AI/workspace/reviews/t10_antigravity_20261013/t10_before_after.png): Panou stânga cu geometria parțială anterioară `T10:A1` (portocaliu) și masca istorică decupată (magenta); Panou dreapta cu noua ipoteză calculată cu 4 noduri (verde aprins, 143.8 m²) și conturul anterior estompat.
* **Pachetul GeoPackage:**
  - [`t10_repair.gpkg`](file:///C:/Users/lefpa/Downloads/QGIS-AI/workspace/reviews/t10_antigravity_20261013/t10_repair.gpkg) conținând 4 straturi distincte:
    - `NOI_IPOTEZE_T10`: Poligonul nou rectificat (4 vârfuri, atribute scalare complete, `owner_verdict=PENDING_OWNER_REVIEW`).
    - `INCERCARI_OPTICE_RAW`: Masca optică SAM2 brută (scor 0.722).
    - `INAINTE_PARTIAL_T10_A1`: Geometria parțială anterioară nesatisfăcătoare (6 vârfuri).
    - `MASCA_ISTORICA_RESPINSA`: Conturul istoric inițial.
* **Raport JSON:**
  - [`t10_report.json`](file:///C:/Users/lefpa/Downloads/QGIS-AI/workspace/reviews/t10_antigravity_20261013/t10_report.json): Metadate, seed-uri, scoruri, atribute și statut `PENDING_OWNER_REVIEW`.
* **Loguri de testare:**
  - [`test_results.txt`](file:///C:/Users/lefpa/Downloads/QGIS-AI/workspace/reviews/t10_antigravity_20261013/test_results.txt) și [`unit_tests.log`](file:///C:/Users/lefpa/Downloads/QGIS-AI/workspace/reviews/t10_antigravity_20261013/unit_tests.log).

---

## 6. Limite Rămase și Recomandări

1. **Contur de streașină vs Amprentă la sol:**
   - Geometria calculată urmărește marginea vizibilă a acoperișului în ortofotoplan și LiDAR. Pentru o amprentă la sol cadastrală, dacă este cerută, se aplică o retragere sistematică a streșinii (tipic 0.3–0.5 m).
2. **Statutul livrabilului:**
   - Rămâne strict `PENDING_OWNER_REVIEW` până la confirmarea vizuală de către utilizator. Nu a fost suprascris niciun strat de bază din proiectul principal.

---

## 7. Feedback privind Instrucțiunile din Documentația Comună

* **Ce a ajutat:**
  - Distincția clară dintre geometrii acceptate (T05–T07) și cazul în lucru (T10).
  - Interdicția explicită a hardcodării sau a forțării arbitrare de dreptunghiuri.
  - Regula de a folosi geometria parțială curentă ca „ÎNAINTE”, nu doar masca istorică greșită.
* **Ce a fost ambiguu sau s-a corectat în cursul investigației:**
  - Ipoteza inițială presupunea că decuparea era strict o problemă de formulă spectrală (maro vs roșiatic). Analiza detaliată a senzorilor a arătat că factorul determinant era trunchierea crop-ului la `y = 585661.05` și tăierea copacului de streașină. Documentarea cauzei reale în acest raport clarifică definitiv problema pentru alți agenți.
