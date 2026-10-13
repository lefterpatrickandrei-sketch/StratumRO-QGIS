# Raport de Predare (Handoff) & Revizuire Independentă de Cod: Simplificare Rectilinie a Acoperișurilor (StratumRO)

> Actualizare Codex după această revizie Antigravity: raportul de continuare autoritativ este [STRATUMRO_SIMPLE_ROOFS_HANDOFF_2026-10-13.md](STRATUMRO_SIMPLE_ROOFS_HANDOFF_2026-10-13.md). Codul final adaugă dreptunghiuri din cuantile, toleranțe până la2.5m și căutare locală de unghi ±4°. Lotul final este în `workspace/reviews/simple_roofs_rectified_20261013/`, cu346 teste (337 trecute,9 omise,0 eșecuri) și proiect QGIS redeschis. Paragrafele de mai jos despre artefacte încă în așteptare descriu momentul reviziei, nu starea finală. Pragurile geometrice sunt de dezvoltare, nu toleranțe legale; nu există contururi terestre oficiale în acest lot.

**Data:** 13 Octombrie 2026  
**Autor:** Antigravity (Motor Principal de Dezvoltare & Execuție StratumRO)  
**Destinatar:** Echipa de Dezvoltare / Codex / Kilo (Adversarial Reviewer)  
**Cadru de Guvernanță:** Conform regulilor din [`AGENTS.md`](../AGENTS.md) (Standardul celor 8 Reguli Științifice bazate pe Evidențe)  
**Statut Execuție:** **IMPLEMENTAT / NEVALIDAT EXPERIMENTAL ÎN RUN COMPLET** (Codex deține responsabilitatea executării testelor și raportului de evidențe)

---

## 1. Context Operațional & Delimitare de Roluri

Codex implementează și testează simplificarea rectilinie a contururilor de acoperiș. În conformitate cu mandatul de audit și handoff:
- **Codul și datele nu au fost modificate** în această iterație de Antigravity.
- **Niciun test unitar sau de regresie nu este revendicat ca rulat** de Antigravity în această sesiune (`0 teste rulate de Antigravity`).
- **Nicio validare vizuală (RGB Ortho Overlay, Quiver Plot, Coridor +/- 10 cm)** nu este revendicată în prezent pentru acest modul.
- **Codex este proprietarul exclusiv** al execuției testelor unitare/de integrare și al raportului formal de evidențe experimentale.

### Domeniul Diagnozei Curente (Scope of Diagnosis)
- Diagnoza curentă vizează strict **8 candidați din zona USAMV (region21)**, dintre care **6 necesită corecție geometrică** (eliminare pinteni, corectare muchii oblice / artefacte SAM2, decuplare terase/părți joase).
- **Avertisment Critic privind Datele de Referință:** Contururile de referință provin din proiectul Global Mapper al proprietarului (`COAJE LUCRU DATE.gmw` / `data/ground_truth/tier1_teren.geojson`). Așa cum a clarificat proprietarul pe 2026-10-13, acestea sunt **obiecte mixte (clădiri și alte suprafețe)** și **NU au statut de măsurători terestre independente sau cadastru oficial**.
- **Regulă de Aur Anti-Leakage:** Aceste referințe **NU trebuie utilizate pentru a desena, ghida sau deriva predicții**. Ele servesc exclusiv ca diagnoză a dezvoltării; nicio geometrie de referință nu este citită ca seed sau prompt în noile module.

---

## 2. Descrierea Algoritmului Implementat

Arhitectura modulară pentru recuperarea și regularizarea acoperișurilor se bazează pe patru componente distincte din [`stratum_ro/`](../stratum_ro/):

### 2.1. [`stratum_ro/roof_simple_geometry.py`](../stratum_ro/roof_simple_geometry.py)
* **Scop:** Generarea de ipoteze rectilinii simple (ortogonale la 90°) strict constrânse de suportul optic observat.
* **Determinare Unghi Dominant:** Calculează unghiul axei principale folosind latura maximă a `minimum_rotated_rectangle` (`_axis_angle`), apoi rotește poligonul pentru alinierea la axe (`aligned`).
* **Fitare Inel Ortogonal (`_orthogonal_ring`):** Identifică segmentele consecutive (runs) pe axele orizontală/verticală, agregă segmentele adiacente ponderate cu lungimea lor și intersectează segmentele alternante pentru a genera colțuri ortogonale la 90°.
* **Scenarii Testate & Ierarhie:**
  1. `SUPPORTED_RECTANGLE`: Dreptunghiul bounding box aliniat cu axa (`box(*aligned.bounds)`).
  2. `SUPPORTED_ORTHOGONAL`: Simplificare Douglas-Peucker la toleranțe metrice succesive (0.35m, 0.5m, 0.75m, 1.0m, 1.25m), urmată de reconstrucție ortogonală prin `_orthogonal_ring`.
* **Praguri de Acceptare (Dezvoltare):**
  - Număr maxim noduri: `max_vertices = 12`
  - Lungime minimă latură: `min_edge = 0.8m`
  - Suport optic minim: `min_support = 0.92` (suprafața ipotezei rectilinii conținută în masca optică observată >= 92%)
  - Acoperire minimă: `min_coverage = 0.90` (aria de intersecție raportată la aria observată >= 90%)
* **Politica de Fallback:** Dacă niciun candidat nu satisface pragurile, funcția returnează geometria optică inițială cu marcajul `{'method': 'NEEDS_REVIEW', 'reason': 'NO_SUPPORTED_SIMPLE_FIT'}`. **Nu se forțează niciodată un dreptunghi fără suport.**

### 2.2. [`stratum_ro/optical_roof_edges.py`](../stratum_ro/optical_roof_edges.py)
* **Scop:** Rafinarea conturului spectral și altimetric (`refine_roof_color`) prin tăierea teraselor neutre joase sau urmărirea acoperișurilor atipice din sticlă (teal).
* **Heuristica Acoperișurilor Roșii (`RED_ROOF_RELATIVE_HEIGHT`):** Dacă masca conține >= 30% pixeli roșii (`r - g > 25` și `r - b > 15`), se eșantionează cotele nDSM din nucleul central (`affinity.scale(0.4, 0.4)`). Se decupează suprafețele adiacente care se află sub cota mediană a nucleului (`median - 2.0m`).
* **Heuristica Acoperișurilor Verzi/Teal (`TEAL_ROOF_COLOR`):** Detectează sticla / acoperișurile din cupru oxidat unde canalul G și B domină canalul R (`g > 1.04*r` și `b > 1.02*r`).
* **Constrângeri Geometrice:** Poligonul rezultat trebuie să păstreze între 60% și 125% din aria inițială (`0.60 <= result.area / geometry.area <= 1.25`), altfel se revine la geometria originală (`method = 'NONE'`).

### 2.3. [`stratum_ro/roof_body_recovery.py`](../stratum_ro/roof_body_recovery.py)
* **Scop:** Orchestrează generarea ipotezelor locale SAM 2 pentru corpuri individuale fără a folosi referințe externe.
* **Flux de Procesare:**
  1. Extrage propuneri prin [`stratum_ro/roof_body_proposals.py`](../stratum_ro/roof_body_proposals.py) (spectru optic pe masca clasei 6 LiDAR) și [`stratum_ro/building_proposals.py`](../stratum_ro/building_proposals.py).
  2. Pentru fiecare propunere, deduce un punct intern prin distanță euclidiană maximă (`distance_transform_edt`) și solicită prompt SAM 2.
  3. În cazul activării parametrului `simple_edges=True`, aplică secvențial `refine_roof_color` urmat de `simple_roof_geometry`. Dacă `simple_edges=False`, aplică fallback-ul existent `rectangle_core` ([`stratum_ro/roof_rectangle_core.py`](../stratum_ro/roof_rectangle_core.py)).
  4. Atribuie atributele de formă (`clasa_forma`, `edge_method`, `edge_support`, `edge_coverage`).
  5. Rutează fiecare candidat prin `route_roof_candidate` ([`stratum_ro/roof_candidate_routing.py`](../stratum_ro/roof_candidate_routing.py)). Orice eșec de simplificare (`edge_method == 'NEEDS_REVIEW'`) este trimis automat în coada `REVIZUIRE_COMPLEXA`.

### 2.4. Integrarea în Pipeline-ul Complet [`run_hybrid_full_aoi.py`](../run_hybrid_full_aoi.py)
* **Configurare CLI:**
  - Valori implicite: `--proposal-policy legacy` (păstrează fluxul clasic v3).
  - Activare opțională:
    ```powershell
    python run_hybrid_full_aoi.py --proposal-policy roof_bodies --simple-roof-edges --output-dir workspace/reviews/your_new_run
    ```
  - Validare argumente: Flag-ul `--simple-roof-edges` este strict dependent de `--proposal-policy roof_bodies`; utilizarea sa izolată declanșează eroare `parser.error`.
* **Discipline de Export GPKG:**
  - Candidații prioritari sunt direcționați în stratul `PROPUNERI_SELECTATE`.
  - Toate corpurile evaluate rămân în `CORPURI_TOATE` și `REVIZUIRE_SENZORI` (salvate exclusiv în `.gpkg` pentru a nu contamina planșa CAD `.dxf`).

---

## 3. Riscuri Algoritmice Majore Identificate (Technical Red Flags)

1. **Acoperiș ≠ Amprentă la Sol (`Roof Footprint != Ground Footprint`):**
   - Algoritmul simplifică muchiile vizibile ale învelitorii acoperișului (streșini, cornișe, console).
   - În standardul ANCPI (Ordinul 600/2023), stratul `1CC` reprezintă conturul la sol al construcției (`CLADIRI_SOL_ANCPI`). Un decalaj sistematic de streașină (30–80 cm) sau retrageri la fațade nu pot fi rezolvate doar printr-o simplificare rectilinie a muchiei foto.
   - Deplasarea radială datorată unghiului de perspectivă al ortofotoplanului distorsionează alinierea fațadei față de sol.

2. **Ambiguitatea Unghiului Dominant (`Dominant Angle Ambiguity`):**
   - Funcția `_axis_angle` se bazează exclusiv pe cea mai lungă latură a dreptunghiului minim rotit (`minimum_rotated_rectangle`).
   - În cazul clădirilor cvasi-pătrate, al fațadelor cu bovindouri/anexe sau al acoperișurilor în L/U cu aripi simetrice, orientarea laturii maxime poate varia brusc (flip de 90° sau deviație de câteva grade determinată de zgomotul de contur).
   - Rotirea greșită a axei duce la o rețea ortogonală complet eronată și declanșează respingerea prematură către `NEEDS_REVIEW`.

3. **Lipsa Dovezii de Generalizare (`No Generalization Proof`):**
   - Pragurile stricte (`min_support=0.92`, `min_coverage=0.90`, praguri spectrale de roșu/verde) sunt calibrate empiric pe o mână de exemple din Cluj USAMV.
   - Nu există nicio dovadă de robustețe pe tipologii constructive diferite (hale industriale cu luminatoare, clădiri rezidențiale neregulate, acoperișuri din tablă zincată gri/ruginie sau terase balcanice).

4. **Dependența de Măști Spectre Specifice:**
   - Heuristica din `refine_roof_color` funcționează strict dacă acoperișul este roșu aprins sau sticlă teal. Pentru țiglă din beton gri, șindrilă neagră sau tablă albastră, algoritmul returnează `NONE` și sare peste decuparea teraselor joase.

---

## 4. Distincție Arhitecturală: Cod Integrat vs. Experimente pe Cele 8 Tile-uri

Este imperativ să distingem starea curentă a codului de starea execuției experimentale:

| Aspect | Stare Actuală în Depozit | Notă de Conformitate |
| :--- | :--- | :--- |
| **Integrarea în Pipeline-ul Complet** | **IMPLEMENTATĂ** în [`run_hybrid_full_aoi.py`](../run_hybrid_full_aoi.py#L73-L82) prin flag-urile opționale CLI | Codul există pe disc, este structurat fără regresie pentru fluxul `legacy`. |
| **Rularea Experimentului pe cele 8 Tile-uri USAMV** | **NEEXECUTATĂ (Not yet run)** | Niciun run cu `--proposal-policy roof_bodies --simple-roof-edges` nu a fost procesat integral pe cele 8 tile-uri. |
| **Setul de Date de Diagnoză (Region21)** | **8 candidați izolați** | Reprezintă un studiu preliminar local de dezvoltare, **nu un benchmark complet**. |
| **Statutul Livrabilelor din `workspace/reviews/`** | **PENDING EXECUȚIE CODEX** | Directorul țintă pentru noul run nu conține încă artefactele finale semnate de Codex. |

---

## 5. Recomandări Reproductibile de Urmat (Follow-Up)

Pentru a asigura o tranziție sigură și defensibilă către faza de evaluare:

1. **Rularea Izolată a Testelor de Unitate (Responsabilitate Codex):**
   Executarea suitei complete în mediul Python dedicat:
   ```powershell
   venv\Scripts\python -m unittest discover stratum_ro/test
   ```
   *Notă: Se va raporta numărul exact de teste rulate, trecute, omise și eșuate conform regulii de aur din `AGENTS.md`.*

2. **Lansarea unui Run Diagnostic Reproductibil într-un Director Nou:**
   Executarea comenzii fără a suprascrie producția anterioară:
   ```powershell
   venv\Scripts\python run_hybrid_full_aoi.py --proposal-policy roof_bodies --simple-roof-edges --output-dir workspace/reviews/your_new_run
   ```

3. **Evaluare Vizuală Obligatorie în QGIS conform Porții 3.1 din `AGENTS.md`:**
   - Încărcarea stratului `CORPURI_TOATE` și `PROPUNERI_SELECTATE` din `workspace/reviews/your_new_run/cladiri_stereo70.gpkg`.
   - Compararea suprapunerii RGB ortofoto pentru cei 8 candidați din region21.
   - Verificarea manuală a modului în care au fost tratate cele 6 cazuri defectuoase inițiale (dacă au fost corectate sau dirijate defensiv în `REVIZUIRE_COMPLEXA`).

4. **Păstrarea Imutabilității Referințelor:**
   - Nu modificați și nu suprascrieți [`data/ground_truth/tier1_teren.geojson`](../data/ground_truth/tier1_teren.geojson).
   - Orice etichetare semantică a obiectelor mixte din Global Mapper trebuie menținută în fișiere sidecar independente.
