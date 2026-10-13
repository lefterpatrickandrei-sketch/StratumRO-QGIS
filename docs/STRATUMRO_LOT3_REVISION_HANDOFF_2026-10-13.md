# STRATUMRO LOT 3 REVISION HANDOFF — 2026-10-13

## 1. Governance & Object Identity
- **Repository Root:** `C:\Users\lefpa\Downloads\QGIS-AI`
- **Active QGIS Project Path:** `workspace/reviews/body_recovery_20261013/inspectie_corectii.qgs`
- **Synchronized Release Project:** `workspace/reviews/retry_six_release_20261013/inspectie_completa_8_orto_loturi.qgs`
- **Governance Status:** `PENDING_OWNER_REVIEW` (`NECESITA_VERIFICARE_LOT3`) for all revised cases (T11–T20).
- **Core Invariants Preserved:**
  - Lot 1 (8/8) and Lot 2 (T01–T04, T05, T06, T07, T10) remain strictly accepted and preserved.
  - T08 and T09 remain rejected / unrecovered.
  - T10 (`T10:A1`, canonical 4-vertex rectangle, 143.8 m²) and the western adjacent gray building remain strictly independent separate objects.
  - Initial Lot 3 results in `workspace/reviews/lot3_20261013/` remain 100% intact and untouched as historical unaccepted baseline evidence.
  - No synthetic predictions or GMW vector contours were used to fit geometry.

---

## 2. Quantitative Comparison: Initial Lot 3 vs. Revised Lot 3

| Metric | Lot 3 Inițial (`lot3_20261013`) | Lot 3 Revizuit (`lot3_revision_20261013`) | Diferență / Impact |
| :--- | :--- | :--- | :--- |
| **Cazuri evaluate** | 10 (T11–T20) | 10 (T11–T20) | Preflight fail-closed (schema v2, SHA256 verified) |
| **Cazuri cu corpuri extrase** | 2 (T12, T17) | **4** (T11, T12, T13, T17) | **+100% cazuri recuperate valid** |
| **Total corpuri extrase** | 3 (`T12:C1`, `T12:C2`, `T17:C1`) | **6** (`T11:C1`, `T11:C2`, `T12:C1`, `T13:C1`, `T13:C2`, `T17:C1`) | **+100% corpuri recunoscute** |
| **T11 (Vilă rezidențială)** | Nerecuperat (punct pe iarbă) | **2 corpuri** (`T11:C1`: 4v, 129.7 m²; `T11:C2`: 4v, 147.6 m²) | Recuperat canonic pe acoperiș |
| **T12:C1 (Acoperiș principal)** | 12 noduri, **678.0 m²** (parazitat pavaj curte) | **8 noduri, 74.7 m²** (strict acoperiș) | **Eliminat pavajul curții complet** (-603.3 m² zgomot) |
| **T13 (Vecini apropiați)** | Nerecuperat (punct pe alee) | **2 corpuri** (`T13:C1`: 4v, 93.1 m²; `T13:C2`: 4v, 110.8 m²) | Separați în 2 corpuri rectangulare |
| **T17 (Aripă articulată L/T)** | 10 noduri, **725.0 m²** (trunchiată la x=390825) | **8 noduri, 1075.4 m²** (acoperire completă) | **Aripă estică inclusă integral** (+350.4 m²) |
| **Cazuri Nerecuperate** | 8 | **6** (T14, T15, T16, T18, T19, T20) | Diagnosticate fizic, fără măști forțate |

---

## 3. Case-by-Case Diagnostic & Sensor Reality

1. **T11 (SIMPLE_RECTANGULAR_ROOF):**
   - *Problemă inițială:* Punctul de căutare cădea pe iarbă/grădină `(391271.5, 585615.4)` lângă o magazie secundară.
   - *Corecție:* Centrat pe acoperișul rezidențial cu două ape din țiglă ceramică `(391244.0, 585595.5)`.
   - *Rezultat revizuit:* `T11:C1` (4 noduri, 129.7 m², suport 0.938, acoperire 0.921, SAM2 0.823) și `T11:C2` (4 noduri, 147.6 m², suport 0.923). Ambele corpuri sunt rectangulare canonice curate.

2. **T12 (RESIDENTIAL_WITH_ATTACHED_ANNEX):**
   - *Problemă inițială:* Punctul era pe pavaj în curte la cota 0m, iar `lidar_area` transmis către SAM2 era de 900+ m², umflând masca peste toată curtea pavată (678 m²).
   - *Corecție generică:* Centrat pe coama acoperișului `(391285.5, 585597.0)`, filtrat pavajul prin condiție de elevație pe culori neutre (`counts > 0` sau `h >= 2.5m`), transmis `lidar_area = seed['area_m2']` (~197 m²).
   - *Rezultat revizuit:* `T12:C1` (8 noduri ortogonale, 74.7 m², suport 0.926, acoperire 0.925, fracțiune clădire LiDAR 0.836). Pavajul curții este exclus în totalitate.

3. **T13 (CLOSE_NEIGHBOR_SEPARATION):**
   - *Problemă inițială:* Punctul cădea în aleea dintre case la cota solului.
   - *Corecție:* Relocat pe acoperișul casei A `(391307.0, 585525.0)`.
   - *Rezultat revizuit:* 2 corpuri independente separate: `T13:C1` (4 noduri, 93.1 m², suport 0.930, SAM2 0.667) și `T13:C2` (4 noduri, 110.8 m², suport 0.922).

4. **T14 (GRAY_METAL_ROOF):**
   - *Problemă inițială:* Punct pe gazon.
   - *Corecție:* Centrat pe hala metalică gri `(391136.0, 585508.0)` cu decupaj continuu din VRT (`T14_covering_ortho.tif`).
   - *Rezultat revizuit:* `UNRESOLVED_AFTER_LOCAL_RETRY`. Din cauza contrastului spectral scăzut pe metalul gri și a marginii de acoperiș nedefinite optic, algoritmul raportează onest nerezolvat, fără a inventa un dreptunghi forțat.

5. **T15 (CANOPY_OVERHANG_AND_DEEP_SHADOW):**
   - *Problemă inițială:* Punct la sol în umbră.
   - *Corecție:* Centrat pe pavilionul campusului `(391008.0, 585286.0)`.
   - *Constatare senzorială:* În norul de puncte LiDAR sursă (`NorPuncte_St70_S42.laz`), clasificarea ASPRS Clasa 6 (Building) lipsește complet (`0` puncte clădire în caseta de căutare), deși cota nDSM este 10.1m.
   - *Rezultat revizuit:* `NO_SUPPORTED_ROOF_SEED`. Conform regulilor de evidență, absența clasificării LiDAR nu este mascată prin halucinație.

6. **T16 (DENSE_CLUSTER_MULTIPLE_NEIGHBORS):**
   - *Problemă inițială:* Punct în spațiul dintre streșini.
   - *Corecție:* Centrat pe clădirea principală `(390807.0, 585324.0)` (h=5.2m, 226 puncte clasa 6).
   - *Rezultat revizuit:* `UNRESOLVED_AFTER_LOCAL_RETRY`. Din cauza contiguității streșinilor vecine, poligonul optic nu a trecut pragul de simplificare ortogonală minimă (0.92 suport).

7. **T17 (ARTICULATED_L_T_SHAPE):**
   - *Problemă inițială:* Caseta de căutare se termina la x=390825, tăind masca la jumătatea aripii estice.
   - *Corecție:* Extinsă anvelopa de căutare la x=390850 pentru a cuprinde întreaga aripă.
   - *Rezultat revizuit:* `T17:C1` (8 noduri ortogonale, **1075.4 m²**, suport 0.955, acoperire 0.945, fracțiune clădire LiDAR 0.874). Corpul L/T este extras complet și fidel geometriei reale.

8. **T18 (L_SHAPED_WAREHOUSE_OPEN_YARD):**
   - *Problemă inițială:* Hala traversa cusătura tile-ului în NoData.
   - *Corecție:* Generat GeoTIFF acoperitor continuu (`T18_covering_ortho.tif`) din mozaicul VRT.
   - *Rezultat revizuit:* `UNRESOLVED_AFTER_LOCAL_RETRY`. Masca brută SAM2 a fost înregistrată în GPKG (`MASCA_BRUTA_SAM2`), dar regularizarea ortogonală a respins forma din cauza convexității complexe.

9. **T19 (LOW_UTILITY_MIXED_MATERIAL):**
   - *Problemă inițială:* Punct pe liziera tile-ului.
   - *Corecție:* Centrat pe pavilion `(390784.0, 585117.0)` cu decupaj continuu (`T19_covering_ortho.tif`).
   - *Rezultat revizuit:* `UNRESOLVED_AFTER_LOCAL_RETRY`.

10. **T20 (LARGE_MULTIVOLUME_COMPLEX):**
    - *Problemă inițială:* Punct în NoData/vegetație.
    - *Corecție:* Centrat pe corpul principal al complexului sportiv `(391027.0, 585182.0)` cu decupaj continuu (`T20_covering_ortho.tif`).
    - *Constatare senzorială:* Complexul sportiv are cota nDSM 24.8m, dar norul LAS nu conține puncte de Clasa 6 în această zonă (`0` puncte clădire).
    - *Rezultat revizuit:* `NO_SUPPORTED_ROOF_SEED`.

---

## 4. QGIS Desktop Live Integration
- **Grup TOC Activ:** `LOT3_REVIZIE_T11_T20` (vizibil, expandat în vârful arborelui de straturi)
  - `LOT3_REV_CORPURI_EXTRASE` (Cian neon `#00e5ff`, contur solid 0.7mm, etichete albastre `#00b0ff` cu buffer alb) — 6 corpuri
  - `LOT3_REV_CAZURI_NERECUPERATE` (Cruce roșie `#ff1744`, 4.0mm, etichete roșii `#d50000`) — 6 puncte
  - `LOT3_REV_FERESTRE_SELECTIE` (Linie galbenă întreruptă `#ffd700`, 0.4mm, etichete portocalii `#e65100`) — 10 casete
  - `LOT3_REV_MASCA_BRUTA` (Linie violet punctată `#9c27b0`, 0.3mm, debifat implicit) — 10 măști brute SAM2
- **Grup TOC Istoric:** `LOT3_ISTORIC_INITIAL_NEACCEPTAT` (debifat implicit, `visible=False`)
- **Proiect Comun Salvat & Sincronizat:**
  - `workspace/reviews/body_recovery_20261013/inspectie_corectii.qgs` (739.7 KB)
  - `workspace/reviews/retry_six_release_20261013/inspectie_completa_8_orto_loturi.qgs` (739.7 KB)

---

## 5. Visual Artifacts on Disk
1. **Planșă de contact generală (10 cazuri):**
   `workspace/reviews/lot3_revision_20261013/results/lot3_revision_contact_sheet.png`
2. **Panouri comparative individuale 3-panou (A: Curat, B: Istoric, C: Revizuit):**
   `workspace/reviews/lot3_revision_20261013/results/T11.png` până la `T20.png`
3. **Capturi de verificare din canvasul live QGIS Desktop:**
   - Prezentare generală: `workspace/reviews/lot3_revision_20261013/qgis_canvas_lot3_revision.png`
   - Detaliu T11/T12: `workspace/reviews/lot3_revision_20261013/qgis_canvas_lot3_t11_t12_closeup.png`
   - Detaliu T17: `workspace/reviews/lot3_revision_20261013/qgis_canvas_lot3_t17_closeup.png`
4. **GeoPackage livrabil:**
   `workspace/reviews/lot3_revision_20261013/results/lot3_revision_results.gpkg`
5. **Raport detaliat mașină:**
   `workspace/reviews/lot3_revision_20261013/results/lot3_revision_report.json`
