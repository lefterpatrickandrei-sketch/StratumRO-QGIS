# StratumRO — Raport de Livrare și Handoff: Lotul 3 de Verificare (T11–T20)

> **STATUT GUVERNANȚĂ:** `PENDING_OWNER_REVIEW` pentru toate cele 10 cazuri noi (T11–T20). Niciun caz din Lotul 3 nu este declarat aprobat ca rezultat final. Verdictul proprietarului este suveran și autoritativ.  
> **INVARIANTE PĂSTRATE:** Loturile anterioare rămân intacte conform deciziilor anterioare ale proprietarului: Lot 1 (8/8 acceptate), Lot 2 T01–T04, T05, T06, T07, T10 acceptate; T08 și T09 rămân respinse/nerecuperate. Clădirea maro-roșcată T10 și clădirea gri alăturată la vest rămân strict obiecte independente separate.

---

## 1. Context și Metodologie de Selecție

Conform protocolului de decizie StratumRO (`docs/STRATUMRO_AGENT_DECISION_PROTOCOL.md`) și regulilor de guvernanță din `AGENTS.md`, evaluarea pe cazuri noi s-a desfășurat în două faze strict separate:

1. **Selecție Înghețată Anterior Extracției (`selection_manifest.json`):**  
   Au fost selectate 10 poziții noi (T11–T20) distribuite pe 7 tile-uri ortofoto native din AOI (`cache_tile_*_halo.tif`).  
   Selecția a acoperit o gamă diversă de arhetipuri arhitecturale și niveluri de dificultate vizuală (forme simple, corpuri articulate L/T, clădiri rezidențiale cu anexe, separare pe limite de proprietate, acoperișuri metalice gri, umbre adânci de copertină, clustere dense și depozite industriale la marginea tile-ului). Niciun caz nu a fost înlocuit post-hoc în urma rulării.
2. **Execuție Baseline fără Modificări Algoritmice:**  
   Implementarea curentă de producție (`stratum_ro/roof_retry.py`, Meta SAM2 Hiera, procesare LiDAR nDSM/clasificare LAS) a fost rulată nemodificată pentru a măsura transparent performanța out-of-the-box pe date neîntâlnite anterior.

---

## 2. Rezumatul Metricilor de Rulare (Triada celor Trei Denominatori)

- **Cazuri evaluate (ferestre de căutare / ipoteze de clădire):** 10 (T11–T20)
- **Cazuri cu corpuri extrase:** 2 (T12, T17)
- **Total corpuri extrase:** 3 (`T12:C1`, `T12:C2`, `T17:C1`)
- **Cazuri nerecuperate / fără geometrie acceptabilă:** 8 (T11, T13, T14, T15, T16, T18, T19, T20)
- **Timp total de inferență:** 15.3 secunde

---

## 3. Tablou Sinoptic Caz cu Caz (T11–T20)

| Caz | Tile Ortofoto | Arhetip Vizual | Corpuri Extrase | Suprafață & Formă | Statut Algoritmic | Observație Vizuală & Diagnostic |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **T11** | `Cluj-2-0` | Acoperiș simplu rectangular | 0 | — | `UNRESOLVED_AFTER_LOCAL_RETRY` | Fereastra a vizat o zonă mixtă rezidențială/grădină cu o mică magazie; sămânța a căzut într-un spațiu auxiliar, respins de decuparea optică/spectrală. Clădirea principală din vest a rămas neacoperită de seed. |
| **T12** | `Cluj-2-0` | Rezidențial cu anexă alipită | 2 | `T12:C1`: 678.0 m² (12v)<br>`T12:C2`: 170.8 m² (4v) | `RECTIFIED_HYPOTHESES_PENDING_REVIEW` | **T12:C2** extrage foarte curat acoperișul ceramic roșu principal ca dreptunghi canonic (4 noduri). **T12:C1** a segmentat o zonă adiacentă dar s-a extins eronat peste pavajul curții interioare și parcela vecină. |
| **T13** | `Cluj-2-1` | Separare clădiri apropiate | 0 | — | `UNRESOLVED_AFTER_LOCAL_RETRY` | Clădiri cu streșini foarte apropiate la limita parcelei; semințele au fost identificate dar muchiile optice nu au putut converge la o geometrie regulată separată. |
| **T14** | `Cluj-1-1` | Hală acoperiș metalic gri | 0 | — | `UNRESOLVED_AFTER_LOCAL_RETRY` | Acoperiș metalic neutru/gri; contrast spectral slab față de sol/pavele și pragurile spectrale curente nu au permis stabilizarea conturului. |
| **T15** | `Cluj-1-1` | Copertină cu umbră adâncă | 0 | — | `NO_SUPPORTED_ROOF_SEED` | Structură ușoară parțial umbrită; înălțimea LiDAR nu a generat semințe care să depășească filtrul nDSM de acoperiș. |
| **T16** | `Cluj-0-1` | Cluster dens corpuri joase | 0 | — | `NO_SUPPORTED_ROOF_SEED` | Densitate mare de corpuri joase fără relief LiDAR nDSM distinct peste pragul de 2.0 m. |
| **T17** | `Cluj-0-1` | Corp articulat în L/T | 1 | `T17:C1`: 725.0 m² (10v) | `RECTIFIED_HYPOTHESES_PENDING_REVIEW` | **T17:C1** extrage cu fidelitate aripa gri articulată (10 noduri, unghiuri de 90°), oprindu-se corect la joncțiunea cu aripa roșie alăturată. |
| **T18** | `Cluj-0-0` | Hală în formă de L cu curte | 0 | — | `NEEDS_COMPLETE_IMAGE_COVERAGE` | Corp mare situat la marginea tile-ului ortofoto; marginea ferestrei de căutare a depășit halo-ul tile-ului nativ. |
| **T19** | `Cluj-0-2` | Pavilion utilitar mixt | 0 | — | `UNRESOLVED_AFTER_LOCAL_RETRY` | Sămânță identificată (543 m²), dar masca SAM2 nu s-a putut regulariza într-o formă ortogonală simplă susținută. |
| **T20** | `Cluj-1-2` | Complex mare multi-volum | 0 | — | `NEEDS_COMPLETE_IMAGE_COVERAGE` | Complex instituțional extins; fereastra de context a depășit marginea tile-ului nativ asociat. |

---

## 4. Integrarea în Proiectul QGIS Comun

Sesiunea live deschisă în QGIS Desktop (`qgis-bin.exe`) pe portul MCP `127.0.0.1:9876` a fost actualizată și verificată:

- **Proiect activ:** `workspace/reviews/body_recovery_20261013/inspectie_corectii.qgs`
- **Proiect de release sincronizat:** `workspace/reviews/retry_six_release_20261013/inspectie_completa_8_orto_loturi.qgs`
- **Grup nou adăugat în TOC:** `LOT3_T11_T20_IN_VERIFICARE`
  1. `LOT3_CORPURI_EXTRASE` (linie cian neon `#00e5ff`, lățime 0.7mm, etichetat cu `id`, font bold cu buffer alb);
  2. `LOT3_CAZURI_NERECUPERATE` (simbol cruce roșie `#ff1744`, 4.0mm, etichetat cu `test_id || ' (NERECUPERAT)'`);
  3. `LOT3_FERESTRE_SELECTIE` (poligon transparent cu linie întreruptă aurie `#ffd700`, etichetat cu `test_id`).

### Capturi Reale din Canvasul Live QGIS
- **Planșă de ansamblu:** `workspace/reviews/lot3_20261013/qgis_canvas_lot3.png`
- **Detaliu live T12:** `workspace/reviews/lot3_20261013/qgis_canvas_lot3_t12_closeup.png`

---

## 5. Pachetul Vizual Livrat (`workspace/reviews/lot3_20261013/`)

1. **Planșa de contact comparativă:**  
   `lot3_contact_sheet.png` (conține toate cele 10 cazuri ordonate, fiecare cu panou curat RGB în stânga și suprapunere cu rezultat în dreapta).
2. **Panouri individuale de înaltă rezoluție:**  
   `T11.png` până la `T20.png`.
3. **Pachet vectorial:**  
   `lot3_results.gpkg` (straturile `CORPURI_EXTRASE_LOT3`, `FERESTRE_SELECTIE_LOT3`, `CAZURI_NERECUPERATE_LOT3`).
4. **Metadate și raport mașină:**  
   `selection_manifest.json`, `lot3_report.json`, `lot3_execution.log`.

---

## 6. Observații Tehnice pentru Următorul Pas de Dezvoltare

1. **Tratarea Clădirilor de la Limita Tile-urilor (T18, T20):**  
   Verificarea strictă `0 <= c < width and 0 <= r < height` pe tile-ul individual trimite direct la `NEEDS_COMPLETE_IMAGE_COVERAGE`. Pentru clădiri mari sau aflate pe marginea tile-ului, extragerea trebuie să citească din VRT-ul complet (`ortofoto_cluj_usamv_rgb.vrt`) sau să îmbine cele două tile-uri adiacente.
2. **Robustizarea Căutării pentru Acoperișuri Gri/Metalice (T14):**  
   Pragurile spectrale optimizate pentru acoperișuri ceramice roșiatice/maronii (ca la T10) resping suprafețele metalice gri dacă gradientul nDSM pe margine este moderat.
3. **Delimitarea Părților Pavate de Clădiri (T12:C1):**  
   La T12, corpul principal (`T12:C2`) a fost extras excelent, dar corpul alăturat (`T12:C1`) s-a extins în curte pe pavaj din cauza reflectanței similare.
