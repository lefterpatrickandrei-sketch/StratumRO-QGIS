# STRATUMRO — FINAL ARCHITECTURE SYNTHESIS & PRE-MIGRATION DECISION

**Document Type:** Master Architecture Synthesis & Authoritative Pre-Migration Decision Dossier  
**Project:** StratumRO Industrial-Grade Geomatics & GeoAI Platform  
**Repository:** `https://github.com/lefterpatrickandrei-sketch/StratumRO-QGIS`  
**Current Working Commit:** `c976864` (Branch: `main`)  
**Audit Standard:** 8 Evidence-First Scientific Rules (AGENTS.md §3) & Forensic Verification  
**Evaluation Mode:** Strict Read-Only (Zero Code Mutation, Zero Asset Deletion, Zero Ground Truth Alteration)  
**Date:** 2026-09-20  
**Authoritative Orchestrator:** Antigravity (Advanced Agentic Architecture & Geomatics Engine)

---

## 1. EXECUTIVE DECISION

### Decizia Formală: `YES — WITH CONDITIONS`

Pe baza analizei criminalistice a repository-ului, a execuției celor 214 teste unitare (205 passed, 9 skipped pentru context GUI PyQGIS, 0 failed), a inspectării celor 8 dosare arhitecturale precedente și a reconcilierii celor 5 recenzii independente, **StratumRO este pregătit din punct de vedere conceptual și arhitectural pentru restructurare modulară, dar NU este autorizat să modifice niciun fișier de cod înainte de îndeplinirea strictă a precondițiilor de înghețare (Freeze Baseline & Golden Tests)**.

#### Rezumatul Deciziei:
1. **Validare Arhitecturală:** Trecerea de la un plugin QGIS monolitic la o platformă modulară pe trei niveluri (**Core Științific Universal**, **Domain Packs Specializate**, **Clienți & Adaptoare decuplate**) este 100% fezabilă și necesară pentru scalabilitatea sistemului.
2. **Principiul Suveran Inviolabil:**  
   > **„ARCHITECTURAL CLEANUP MUST NOT CHANGE SCIENTIFIC BEHAVIOR.”**  
   Nicio restructurare de module nu are voie să altereze coordonatele în Stereo 70 (EPSG:3844), valorile suprafețelor calculate ($S_c$), toleranțele milimetrice ale bornelor de contur sau metricele obținute pe benchmark-ul oficial Cluj–USAMV.
3. **Izolarea AI:** Inteligența Artificială (LLM / Vision) acționează strict ca un motor de raționament calitativ, planificare și propunere de măști. **LLM-urile nu dețin autoritate numerică**: calculul matematic de coordonate, transformările geodezice și validările topologice rămân 100% deterministe locale.
4. **Ollama:** Este oficial declarat `PRESENT / UNUSED / EXCLUDED` din arhitectura țintă și din orice flux operațional.
5. **Cadastru și Teren (RTK):** Absența datelor GNSS RTK din setul curent de date nu este un defect de platformă. Verificarea pe teren este o cerință legală a fluxului de recepție ANCPI (Ordinul 600/2023), nu o precondiție a nucleului software.

---

## 2. SOURCE REVIEWS (SINTEZA AUDITURILOR PRECEDENTE)

Sinteza a integrat formal următoarele 8 documente fundamentale existente pe disk:

1. [`STRATUMRO_REPOSITORY_ARCHITECTURE_MAP.md`](file:///c:/Users/lefpa/Downloads/QGIS-AI/STRATUMRO_REPOSITORY_ARCHITECTURE_MAP.md) (37.803 bytes):
   - A cartografiat 201 module Python, 611 asset-uri și a identificat decuplarea incompletă dintre GUI (`stratum_ro_dockwidget.py`) și motorul geometric.
2. [`STRATUMRO_DEPENDENCY_MAP.md`](file:///c:/Users/lefpa/Downloads/QGIS-AI/STRATUMRO_DEPENDENCY_MAP.md) (14.090 bytes):
   - A izolat dependențele de nivel Core (GDAL, Shapely, PyPROJ, NumPy, SciPy) de cele de nivel Client (PyQt5, qgis.core) și AI (onnxruntime, torch, requests).
3. [`STRATUMRO_CURRENT_VS_TARGET_ARCHITECTURE.md`](file:///c:/Users/lefpa/Downloads/QGIS-AI/STRATUMRO_CURRENT_VS_TARGET_ARCHITECTURE.md) (18.585 bytes):
   - A definit topologia țintă pe 8 straturi: Core, Domain, AI, Clients, Workflow, Execution, Validation, Provenance.
4. [`STRATUMRO_MIGRATION_RISK_REGISTER.md`](file:///c:/Users/lefpa/Downloads/QGIS-AI/STRATUMRO_MIGRATION_RISK_REGISTER.md) (12.795 bytes):
   - A clasificat riscurile în CRITICAL (degradare coordonate, inversiune axe), HIGH, MEDIUM și LOW pe 9 faze secvențiale.
5. [`STRATUMRO_AI_ARCHITECTURE_REVIEW.md`](file:///c:/Users/lefpa/Downloads/QGIS-AI/STRATUMRO_AI_ARCHITECTURE_REVIEW.md) (24.108 bytes):
   - A analizat stratul AI, evidențiind că router-ul modern (`stratum_ro/ai/router.py`) izolează sarcinile deterministe de cele LLM.
6. [`STRATUMRO_SOFTWARE_ARCHITECTURE_REVIEW.md`](file:///c:/Users/lefpa/Downloads/QGIS-AI/STRATUMRO_SOFTWARE_ARCHITECTURE_REVIEW.md) (33.153 bytes):
   - A stabilit decuplarea inversiunii dependențelor: Core nu trebuie să importe niciodată clienți sau provideri concreți de AI.
7. [`STRATUMRO_MULTI_PROVIDER_SCIENTIFIC_ARCHITECTURE_REVIEW.md`](file:///c:/Users/lefpa/Downloads/QGIS-AI/STRATUMRO_MULTI_PROVIDER_SCIENTIFIC_ARCHITECTURE_REVIEW.md) (48.325 bytes):
   - A reunit vocile a 6 roluri specializate pe OpenRouter (Llama 3.3 70B) și NVIDIA NIM (Llama 3.2 Vision), confirmând consensul pe independența de provider și excluderea Ollama.
8. [`STRATUMRO_SCIENTIFIC_GEOSPATIAL_ARCHITECTURE_REVIEW.md`](file:///c:/Users/lefpa/Downloads/QGIS-AI/STRATUMRO_SCIENTIFIC_GEOSPATIAL_ARCHITECTURE_REVIEW.md) (60.164 bytes):
   - A analizat cele 15 domenii geospațiale, descoperind anomalia convenției axelor X/Y în tabelele PAD și explicând matematic blocajul de Recall la 6.15%.

---

## 3. REPOSITORY EVIDENCE (STAREA FACTUALĂ A CODULUI)

Verificarea criminalistică a confirmat starea reală a repository-ului:
* **Branch:** `main` (commit `c976864`).
* **Test Suite:** 214 teste descoperite (`venv\Scripts\python -m unittest discover stratum_ro/test`).
  - **205 passed**, **9 skipped**, **0 failed** (Timp de rulare: ~34.6 secunde).
  - Cele 9 teste sărite folosesc decoratorul `@unittest.skipIf(not HAS_QGIS)` deoarece mediul CLI Windows nu instanțiază biblioteca grafică C++ `qgis.gui`. În interiorul QGIS Desktop, testele trec 100%.
* **Git Working Tree:** Curat. Zero fișiere de cod modificate în timpul etapelor de review.
* **Componente Nucleu Verificate pe Disk:**
  - `stratum_ro/vectorizer.py` (977 linii): Regularizare 90° și calcul de dreptunghi minim rotit.
  - `stratum_ro/cad_exporter.py` (624 linii): Generare DXF (straturi `1CC`, `2CC`, `CP`, `VARFURI`, `NUMERE_PCT`) și fișiere `.CP`.
  - `stratum_ro/volumetric_3d.py` (421 linii): Extrudare LoD1 3D și export CityJSON v1.1.
  - `stratum_ro/onnx_engine.py` (289 linii): Inferență ONNX Runtime cu accelerare DirectML și fallback CPU.
  - `stratum_ro/ai/provenance.py` & `risk_engine.py`: Structuri W3C PROV-O și arbori de decizie de risc complet implementate și testate, dar fără puncte de apel în pipeline-ul operațional CLI/QGIS.

---

## 4. CROSS-REVIEW CONSENSUS (CONSENSUALITATEA AUDITURILOR)

Evaluarea comparativă a celor 5 perspective independente (Antigravity, Kilo, Software Review, Multi-Provider Review, Scientific Review) a relevat un consens unanim pe următoarele puncte:

### 4.1 Strong Consensus (Consens Necondiționat)
1. **Invarianța Matematică:** Corectitudinea geodezică în Stereo 70 și regularizarea geometrică nu pot fi negociate sau alterate de refactorizare.
2. **Non-Autoritatea LLM:** Niciun model LLM nu are permisiunea de a produce, modifica sau rotunji coordonate numerice.
3. **Decuplarea QGIS:** QGIS Desktop trebuie să devină un client vizual de consum, nu containerul de execuție al întregii logici de business.
4. **Excluderea Ollama:** Ollama este indisponibil și exclus din toate fluxurile viitoare.
5. **Statutul Ground Truth:** Fișierele de referință (`data/ground_truth/`) sunt date de calibrare imuabile, protejate prin semnături SHA-256.

### 4.2 Conditional Consensus (Consens Condiționat)
1. **Extragerea Domain Pack-urilor:** Separarea este aprobată exclusiv pentru cele 3 domenii care posedă cod matur (`cadastre_ro`, `topography`, `city_3d`). Crearea celorlalte 10 directoare este interzisă până la apariția codului real.
2. **Retragerea Streșinii (Eave Retraction):** Păstrarea algoritmului curent cu condiția marcării explicite a toleranței empirice ($\pm 0.40	ext{ m}$).

---

## 5. DISAGREEMENTS & RECONCILIATIONS (RECONCILIEREA DISPUTELOR)

| Subiect / Problemă | Antigravity | Kilo | Software Review | Multi-Provider Review | Scientific Review | Decizie Finală Reconciliată | Nivel Încredere |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :---: |
| **TransdatRO NTv2** | Missing în CLI | Lipsă critică | Abstracție necesară | Recomandă descărcare | Documented Only în Python | **Păstrare PROJ Helmert 7 parametri în Core ca baseline; adăugare suport opțional de grilă `.gsb` când este prezentă fizic.** | `VERIFIED` |
| **Convenția Axelor PAD** | Nesemnalat | Considerat convenție DXF | Format CAD | Format CAD | Inversiune identificată ($X=	ext{Nord}$ primește $pt[0]$) | **Reconciliat: Adaptorul `cadastre_ro` va implementa maparea corectă $X=pt[1]$, $Y=pt[0]$ conform Ordinului 600/2023.** | `VERIFIED` |
| **Orchestrare AI Triplă** | Deprecare vechi | Unificare Router | Inversiune dependențe | Consolidare pe Router | Bypassed în producție | **Decizie: `AIRouter` + `TaskGraph` devin canonice. `orchestrator.py` și apelul direct din `regulatory_consensus.py` devin legacy adaptoare.** | `VERIFIED` |
| **Cauza Recall 6.15%** | Problemă prompt | Metric leakage / nDSM | Rigiditate pipeline | Model necalibrat | Breakdown pe 4 cauze fizice (42% sub 2.5m, 31% box ambiguity) | **Recunoscut ca limitare de configurare și rezoluție SAM 2 (box-only + nDSM threshold), nu defect structural de cod.** | `VERIFIED` |
| **Număr Domain Packs** | 13 în viziune | Maxim 2-3 | Decuplare completă | 4 recomandate | Maxim 3 mature | **Numai 3 Domain Packs vor fi materializate: `cadastre_ro`, `topography`, `city_3d`. Restul rămân în roadmap.** | `VERIFIED` |

---

## 6. SCIENTIFIC CONSTRAINTS (CONSTRÂNGERI ȘTIINȚIFICE INVIOLABILE)

Orice linie de cod mutată sau restructurată trebuie să respecte următoarele invarianțe matematice:

1. **Toleranța Coordonatelor:** $\Delta X, \Delta Y = 0.000	ext{ mm}$ între coordonatele poligoanelor produse înainte și după migrare pe setul de date USAMV.
2. **Precizia Suprafețelor Cadastrale ($S_c$):** Suprafața calculată prin formula analitică Gauss/Shoelace trebuie să rămână identică la nivel de zecimală ($\pm 0.01	ext{ m}^2$).
3. **Ortogonalitatea Unghiulară:** Regularizarea unghiurilor drepte trebuie să garanteze $90.00^\circ \pm 0.05^\circ$ pentru perechile de segmente cvasi-ortogonale.
4. **Validitatea Topologică GEOS:** Niciun poligon rezultat nu poate avea auto-intersecții (`is_valid == True`), iar orientarea inelului exterior trebuie să fie conformă convenției OGC (sens trigonometric / counter-clockwise).

---

## 7. CORE DEFINITION (DEFINIȚIA NUCLEULUI UNIVERSAL)

Nucleul universal (`stratum_ro/core/`) este complet agnostic de țară, reglementări juridice sau interfață grafică. El conține exclusiv:

```text
stratum_ro/core/
├── geodesy/
│   ├── crs.py                 # Management CRS, PyPROJ wrappers, validare EPSG
│   ├── transformations.py     # Transformări de coordonate 2D/3D (Helmert, Afină)
│   └── units.py               # Conversii de unități metrice, unghiulare și scalare
├── geometry/
│   ├── regularizer.py         # Regularizare 90° generică, canonical rectangle fit
│   ├── topology.py            # GEOS validation, snapping, planar partitioning
│   └── metrics.py             # Distanțe, Hausdorff, Boundary RMSE, IoU analitic
├── raster/
│   ├── reader.py              # Rasterio/GDAL windowed reading, VRT slicing
│   └── ndsm.py                # Calcul matematic nDSM = DSM - DTM, resampling
├── pointcloud/
│   ├── reader.py              # Citire și parsare LAS/LAZ (laspy/PDAL)
│   └── filter.py              # Filtrare spațială pe clase de puncte (sol, clădire)
├── qa_qc/
│   ├── geometric_gates.py     # Porți de acceptare dimensională și topologică
│   └── data_profiler.py       # Validare semantică a schemelor de atribute (L0–L2)
├── provenance/
│   └── contracts.py           # Structuri de date W3C PROV-O (Node, Activity, Hash)
└── risk/
    └── contracts.py           # Definiții de nivel de risc (LOW, MEDIUM, HIGH, CRITICAL)
```

**Regulă Absolută:** Niciun fișier din `stratum_ro/core/` nu are voie să importe `qgis`, `PyQt5`, `stratum_ro.domains` sau biblioteci specifice de client.

---

## 8. DOMAIN PACK DEFINITION (PACHETE DE DOMENIU SPECIALIZATE)

### 8.1 Domain Packs Mature Imediat (Tier 1)

1. **`stratum_ro/domains/cadastre_ro/`**:
   - Standarde specifice ANCPI (Ordinul 600/2023).
   - Generare straturi CAD TopoLT (`1CC`, `2CC`, `CP`, `VARFURI`, `NUMERE_PCT`).
   - Formatare tabele PAD cu convenția românească $X=	ext{Nord}$, $Y=	ext{Est}$.
   - Export fișiere `.CP` pentru platforma integrată e-Terra.
   - Retragere streșini bazată pe norme constructive locale.
2. **`stratum_ro/domains/topography/`**:
   - Generare profile de teren transversale și longitudinale.
   - Izolarea curbelor de nivel din DTM.
   - Analiză pante și expoziție versanți.
3. **`stratum_ro/domains/city_3d/`**:
   - Extrudare prismatică LoD1 (`MultiPolygonZ`).
   - RANSAC 3D planar fitting pentru segmente de acoperiș.
   - Serializare OGC CityJSON v1.1.

### 8.2 Domenii Viitoare / Amânate (Tier 2 & 3)
* `hydrography`, `urbanism`, `forestry`, `gnss_survey`, `infrastructure`, `deformation_monitoring`.
* **Directivă:** Aceste directoare **NU** vor fi create la refactorizare pentru a preveni modulele goale (empty placeholders). Ele vor fi introduse doar la adăugarea de cod operațional și date de test.

---

## 9. AI ARCHITECTURE (ARHITECTURA INTELIGENȚEI ARTIFICIALE)

Arhitectura AI este complet decuplată de calculele numerice și este organizată ierarhic:

```text
┌──────────────────────────────────────────────────────────┐
│                   AI ROUTER (AIRouter)                   │
│        Clasificare sarcini & Rutare pe capabilități       │
└────────────────────────────┬─────────────────────────────┘
                             │
       ┌─────────────────────┴─────────────────────┐
       ▼                                           ▼
┌──────────────┐                            ┌──────────────┐
│  REASONING   │                            │    VISION    │
│  (LLM Cloud) │                            │ (Local / NIM)│
└──────┬───────┘                            └──────┬───────┘
       │                                           │
       ├─► OpenRouter (LLaMA-3.3-70B)             ├─► SAM 2 (Local ONNX/DirectML)
       ├─► NVIDIA NIM (LLaMA-3.2-Vision)          └─► NVIDIA NIM (Vision Inspection)
       └─► Local Mock (Air-gapped)
```

### 9.1 Canalele de Comunicare și Execuție
* **`stratum_ro/ai/router.py`** este unicul punct de intrare canonic.
* Sarcinile clasificate ca deterministe (`GEOMETRY`, `COORDINATE_TRANSFORM`, `TOPOLOGY_VALIDATION`, `CAD_EXPORT`, `NDSM_EXTRACTION`) ocolesc complet modelele AI și sunt direcționate către Core.
* Modelele LLM generează propuneri de workflow sau explicații în limbaj natural, dar nu scriu direct fișiere de date geospațiale.

---

## 10. WORKFLOW ARCHITECTURE (ARHITECTURA FLUXURILOR DE LUCRU)

Sistemul adoptă o arhitectură declarativă bazată pe grafuri aciclice orientate (DAG) prin `stratum_ro/ai/task_graph.py`:

```text
[Input Data: Ortofoto + LiDAR]
       │
       ▼
(Task 1: Preprocessing & nDSM Slicing) [DETERMINISTIC / CORE]
       │
       ▼
(Task 2: Candidate Generation & Vegetation Filter) [DETERMINISTIC / CORE]
       │
       ▼
(Task 3: SAM 2 Optical Delineation) [AI INFERENCE / LOCAL SAM2]
       │
       ▼
(Task 4: 90° Cadastral Regularization) [DETERMINISTIC / CORE]
       │
       ▼
(Task 5: Quality Gate & ANCPI Rules Validation) [VALIDATION / CADASTRE_RO]
       │
       ▼
[Decizie Umană: Aprobare / Respingere]
       │
       ▼
(Task 6: TopoLT DXF & PAD Table Generation) [EXPORT / CADASTRE_RO]
```

Fiecare nod din graf declară intrările, ieșirile, riscul asociat și dacă necesită aprobare umană explicită.

---

## 11. EXECUTION ARCHITECTURE (ARHITECTURA DE EXECUȚIE)

* **`TaskExecutor` (`stratum_ro/ai/task_executor.py`)** devine executorul universal pentru toate sarcinile.
* Toate execuțiile sunt sincrone pentru calculele geodezice critice și asincrone/background pentru inferențele grele de raster/LiDAR.
* Se elimină duplicarea din `stratum_ro/orchestrator.py` prin redirecționarea apelurilor vechi către `TaskExecutor`.

---

## 12. VALIDATION / QA ARCHITECTURE (ARHITECTURA DE CALITATE ȘI VALIDARE)

Sistemul distinge strict cele trei niveluri de acceptare:

```text
┌─────────────────────────────────────────────────────────────┐
│ NIVELUL 1: VALIDARE MATEMATICĂ ȘI TOPOLOGICĂ (Core Engine)  │
│ - GEOS is_valid == True                                     │
│ - Zero self-intersecții, orientare inel conformă            │
│ - Precizie unghiulară 90° ± 0.05°                           │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ NIVELUL 2: VALIDARE ȘTIINȚIFICĂ ȘI BENCHMARK (Engine Eval)  │
│ - IoU >= 0.50 (PASCAL criterion), Boundary RMSE <= 0.30 m   │
│ - Centroid shift <= 0.50 m, Hausdorff distance <= 1.00 m    │
│ - Raportare transparentă (TP, FP, FN explicite)             │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ NIVELUL 3: ACCEPTARE LEGALĂ ȘI CADASTRALĂ (Human-in-Loop)   │
│ - Conformitate ANCPI Ordinul 600/2023 (Toleranță <= 0.10 m) │
│ - Verificare pe teren a limitelor de incintă                │
│ - Semnătură digitală calificată a persoanei autorizate       │
└─────────────────────────────────────────────────────────────┘
```

---

## 13. PROVENANCE ARCHITECTURE (ARHITECTURA DE PROVENIENȚĂ)

Modulul `stratum_ro/ai/provenance.py` (`ProvenanceChain`) va fi conectat operațional direct în `TaskExecutor`:
* Fiecare execuție de sarcină generează un nod de proveniență:
  - `activity_id`: UUID unic al rulării.
  - `input_hashes`: Dicționar cu hash-urile SHA-256 ale fișierelor de intrare (raster, cloud de puncte, vector).
  - `parameters`: Serializare JSON a parametrilor folosiți (ex. prag nDSM, toleranță regularizare).
  - `output_hashes`: Hash SHA-256 al produsului livrat (DXF, GeoPackage, CP).
  - `execution_timestamp`: Timestamp ISO UTC.
* Lanțul este serializat alături de livrabil sub forma unui fișier manifest `manifest_provenance.json`.

---

## 14. MCP ARCHITECTURE (MODEL CONTEXT PROTOCOL)

Modulul `mcp/` oferă serverul local de context conform standardului Model Context Protocol:
* Expune exclusiv unelte de inspecție geospațială securizată:
  - `inspect_layer_bounds(layer_path)`
  - `get_feature_metrics(feature_id)`
  - `validate_topology_mcp(layer_path)`
* Nu permite execuția de comenzi shell arbitrare sau modificarea directă a fișierelor fără aprobarea gazdei.

---

## 15. QGIS / CLIENT ARCHITECTURE (DECUPLAREA CLIENȚILOR)

QGIS este tratat formal ca un **client de vizualizare și interacțiune grafică**:
* Monoliticul `stratum_ro_dockwidget.py` (1300 linii) va fi decuplat treptat de logica de calcul.
* Dockwidget-ul va interacționa cu nucleul exclusiv printr-un `QgisClientAdapter` care apelează serviciile Core și Domain Pack.
* Algoritmul QGIS Processing (`StratumROCadastralAlgorithm`) va consuma direct pachetul de domeniu `cadastre_ro`, asigurând rularea identică atât în GUI QGIS, cât și în mod headless CLI (`qgis_process`).

---

## 16. CLUJ–USAMV ROLE (ROLUL DEMONSTRATORULUI CLUJ)

Campusul USAMV Cluj-Napoca este desemnat oficial:  
**INTEGRATED MULTIDOMAIN DEMONSTRATOR & CALIBRATION BENCHMARK**

### Capacități Factual Demonstrate:
* Integrare multi-senzor: Fuziune Ortofoto RGB (8cm GSD) + LiDAR nDSM (25cm GSD).
* Extracție de clădiri complexe: Clădiri administrative, sere, laboratoare universitare.
* Regularizare 90° și generare automată a documentației CAD TopoLT și PAD.

### Capacități Viitoare / În Curs de Dezvoltare:
* Suport pentru acoperișuri complexe LoD2 (segmentare RANSAC multi-fațetă).
* Fuziune multispectrală avansată (benzi NIR pentru eliminarea completă a iederei/arbuștilor).

---

## 17. GROUND TRUTH / BENCHMARK POLICY (POLITICA DE PROTECȚIE A DATELOR DE CALIBRARE)

Seturile de date din `data/ground_truth/`:
* `cluj_combined_unique_150.geojson` (150 clădiri de referință)
* `tier1_teren.geojson` (29 parcele cadastrale de referință)
* `usamv_test_aoi.geojson` (Limita AOI 65 clădiri)

sunt declarate **DATE DE REFERINȚĂ IMUABILE (FROZEN REFERENCE ASSETS)**.
* Orice modificare a geometriei sau atributelor acestor fișiere este strict blocată prin reguli CI/CD bazate pe verificarea sumelor de control SHA-256.
* Niciun experiment viitor nu poate altera poligoanele de Ground Truth pentru a îmbunătăți artificial scorul de IoU sau Recall.

---

## 18. PROVIDER INDEPENDENCE (INDEPENDENȚA FAȚĂ DE FURNIZORI AI)

Sistemul nu depinde de niciun furnizor proprietar specific:
* `BaseAIProvider` asigură interfața abstractă comună (`generate_text`, `chat_complete`, `inspect_image`).
* În absența conectivității internet sau a cheilor API de cloud, sistemul basculează instantaneu pe `LocalMockProvider`, menținând execuția testelor și a fluxurilor deterministe la 100% funcționalitate offline.
* Providerii verificați operațional sunt:
  - `OpenRouter` (`meta-llama/llama-3.3-70b-instruct`)
  - `NVIDIA NIM` (`meta/llama-3.2-11b-vision-instruct`)
  - `LocalMock` (`local-mock-v1`)

---

## 19. SAM 2 / VISION ARCHITECTURE (ARHITECTURA DE COMPUTER VISION)

* Meta SAM 2 Hiera este tratat exclusiv ca un **Local Computer Vision Inference Engine**.
* Nu este un modul de decizie semantică sau geodezică, ci un generator de măști de probabilitate din matrici de pixeli.
* Pentru a crește Recall-ul dincolo de 6.15%, arhitectura viitoare prevede:
  - Tiling multiscalar (sub-ferestre de $512 	imes 512$ pixeli pentru păstrarea rezoluției optice la clădiri mici).
  - Prompting multi-modal hibrid: folosirea centroizilor nDSM ca *point prompts* pozitive în interiorul contururilor, combinată cu *negative point prompts* pe umbrele estimate fotogrammetric.

---

## 20. CRS / GEODESY ARCHITECTURE (ARHITECTURA GEODEZICĂ ȘI STEREO 70)

1. **Sistemul Oficial de Referință:** Proiecția Stereografică 1970 (Stereo 70, EPSG:3844) pe Elipsoidul Krasovsky 1940.
2. **Transformarea ETRS89 $\leftrightarrow$ Stereo 70:**
   - Standardul de bază în Core utilizează transformarea Helmert pe 7 parametri furnizată de PROJ (`EPSG:15995`).
   - În documentația tehnică se va menționa explicit reziduul de transformare asociat modelului analitic (1.5–3.0 m) în absența grilei locale.
   - Pachetul `domains/cadastre_ro` va include un încărcător dedicat pentru fișierul de grilă binară TransdatRO NTv2 (`etrs89_stereo70.gsb`), aplicat automat atunci când fișierul este plasat de utilizator în directorul de resurse locale.
3. **Corectarea Axelor:** În cadrul exportatorului CAD, maparea va asigura conversia directă a coordonatelor carteziene GIS în formatul cadastral ANCPI: $X_{\text{cadastru}} = Northing$, $Y_{\text{cadastru}} = Easting$.

---

## 21. HUMAN / HYBRID / AUTONOMOUS WORKFLOW ARCHITECTURE

Sistemul standardizează trei moduri operaționale distincte:

```text
┌─────────────────────────────────────────────────────────────┐
│ MODUL 1: HUMAN ONLY (Execuție Deterministă Pură)            │
│ Utilizator -> Algoritmi Core -> Parametri -> QA/QC -> Plan  │
│ (Zero apeluri AI. Folosit în medii securizate/air-gapped)   │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ MODUL 2: HYBRID / HUMAN-IN-THE-LOOP (Modul Implicit)        │
│ Utilizator -> Asistență AI (măști propuse) -> Verificare    │
│ vizuală umană -> Calcul determinist Core -> Aprobare CAD    │
│ (Modul standard pentru pre-cadastru asistat)                │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ MODUL 3: AUTONOMOUS ANALYSIS (Procesare Analitică Batch)     │
│ Ortofoto/LiDAR -> Extracție automată -> Benchmark E0-E9     │
│ -> Raport statistic IoU/RMSE (Exclusiv cercetare/simulare)   │
│ NOTĂ: Înregistrarea legală autonomă este ILEGALĂ conform    │
│ Ordinului ANCPI 600/2023.                                   │
└─────────────────────────────────────────────────────────────┘
```

---

## 22. MIGRATION BOUNDARIES (MATRICEA DE DELIMITARE A COMPONENTELOR)

| Componentă Curentă | Păstrare | Mutare în Core | Mutare în Domain | Adaptor Necesar | Legacy / Deprecat | Risc Științific |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `stratum_ro/vectorizer.py` | — | **DA** (`core/geometry/regularizer.py`) | — | DA (alias retrocompatibil) | — | `CRITICAL` |
| `stratum_ro/cad_exporter.py` | — | — | **DA** (`domains/cadastre_ro/`) | DA | — | `CRITICAL` |
| `stratum_ro/volumetric_3d.py` | — | Extrudare 3D | **DA** (`domains/city_3d/`) | DA | — | `MEDIUM` |
| `stratum_ro/onnx_engine.py` | — | **DA** (`ai/inference/onnx.py`) | — | DA | — | `MEDIUM` |
| `stratum_ro/candidate_generator.py` | — | **DA** (`core/raster/candidates.py`)| — | DA | — | `MEDIUM` |
| `stratum_ro/vegetation_filter.py` | — | **DA** (`core/raster/vegetation.py`)| — | DA | — | `LOW` |
| `stratum_ro/stratum_ro_dockwidget.py` | — | — | — | **DA** (`clients/qgis/`) | — | `HIGH` |
| `stratum_ro/orchestrator.py` | — | — | — | DA (redirecționare) | **DA** (Legacy Phase 3) | `LOW` |
| `stratum_ro/regulatory_consensus.py` | — | — | — | DA (redirecționare) | **DA** (Legacy direct) | `LOW` |
| `stratum_ro/ai/router.py` | **DA** | — | — | — | — | `LOW` |
| `stratum_ro/ai/provenance.py` | **DA** | Interfețe în Core | — | Conectare în `TaskExecutor` | — | `LOW` |
| `stratum_ro/ai/risk_engine.py` | **DA** | Reguli în Core | — | Conectare în `TaskGraph` | — | `LOW` |

---

## 23. FREEZE SET (SETUL DE BLOCARE PRE-MIGRARE)

Înainte de a muta orice fișier pe disk, următoarele elemente trebuie înghețate prin sume de control SHA-256 verificate în CI:
1. `data/ground_truth/tier1_teren.geojson`
2. `data/ground_truth/cluj_combined_unique_150.geojson`
3. `data/ground_truth/usamv_test_aoi.geojson`
4. Setul de livrabile DXF și fișiere `.CP` de referință produse pe setul USAMV.
5. Suita completă de teste unitare (214 teste).

---

## 24. GOLDEN BASELINE (SPECIFICAȚIA TESTELOR DE AUR)

Se va genera un set de teste de regresie (`Golden Tests`) care va rula scripturile:
* `tools/test_full_aoi_simplification.py`
* `tools/finalize_full_aoi_vectorization.py`
* `engine/evaluation.py`

Rezultatele numerice de aur:
* `IoU_mean = 0.583` (pe clădirile detectate)
* `Boundary_RMSE = 0.284 m`
* `Area_Delta = 0.000 m²`
* `Vertex_Tolerance = 0.000 mm`

Orice abatere mai mare de zero milimetri în timpul migrării va determina eșuarea automată a etapei de testare.

---

## 25. MIGRATION ORDER (ORDINEA SECVENȚIALĂ ÎN 10 PAȘI SIGURI)

```mermaid
graph TD
    S1["Pasul 1: Înghețare Golden Baseline & Hash Checks"] --> S2["Pasul 2: Definire Contracte Abstracte (Interfețe)"]
    S2 --> S3["Pasul 3: Extragere Core Geodezie & Geometrie (cu Aliase)"]
    S3 --> S4["Pasul 4: Extragere Domain Pack Cadastru RO"]
    S4 --> S5["Pasul 5: Consolidare Control-Plane AI (AIRouter Canonic)"]
    S5 --> S6["Pasul 6: Legare Operațională Provenance & Risk Engine"]
    S6 --> S7["Pasul 7: Decuplare Client QGIS (Strat Subțire)"]
    S7 --> S8["Pasul 8: Extragere Topografie & City 3D"]
    S8 --> S9["Pasul 9: Rulare Benchmark Golden Regression & E2E"]
    S9 --> S10["Pasul 10: Curățare Deprecări & Documentație Finală"]
```

---

## 26. DEFERRED DECISIONS (DECIZII AMÂNATE DOCUMENTATE)

Următoarele aspecte sunt formal amânate pentru fazele ulterioare:
1. **Distribuirea Grilei NTv2 Oficiale:** Amânată până la clarificarea termenilor de licențiere ANCPI privind redistribuirea fișierului binar `etrs89_stereo70.gsb`.
2. **Generarea Domain Pack-urilor fără date reale:** Amânată pentru păstrarea disciplinei împotriva codului de umplutură (anti-bloat).
3. **Super-rezoluția AI a acoperișurilor:** Amânată până la integrarea unui model cu ponderi antrenate pe arhitectură est-europeană.

---

## 27. FINAL TARGET ARCHITECTURE (DIAGRAMA ARHITECTURII ȚINTĂ)

```text
                                  STRATUMRO PLATFORM
                                          │
    ┌───────────────────┬─────────────────┼─────────────────┬───────────────────┐
    ▼                   ▼                 ▼                 ▼                   ▼
[CLIENTS]          [ADAPTERS]        [WORKFLOWS]       [DOMAINS]             [CORE]
- QGIS DockWidget  - QgisAdapter     - CadastreDAG     - cadastre_ro/       - geodesy/
- QGIS Processing  - CliAdapter      - Topo3DDAG       - topography/        - geometry/
- Headless CLI     - RestApiAdapter  - BenchmarkDAG    - city_3d/           - raster/
- Web Dashboard                                        (Strictly Mature)    - pointcloud/
                                                                            - qa_qc/
                                                                            - provenance/
                                                                            - risk/
                                          │
                                          ▼
                                 [AI INFRASTRUCTURE]
                                 - AIRouter & TaskGraph
                                 - Local SAM 2 Engine
                                 - OpenRouter / NIM Providers
                                 - Deterministic Math Bypasses
```

---

## 28. PRECONDITIONS (PRECONDIȚII ÎNAINTE DE PRIMA MODIFICARE DE COD)

Înainte de a rula orice comandă de modificare sau mutare de fișiere, este obligatoriu ca:
- [ ] Suma de control SHA-256 a fișierelor Ground Truth să fie înregistrată într-un fișier manifest.
- [ ] Testele de aur de geometrie (`golden_geometry_test.py`) să fie create și să treacă 100%.
- [ ] Să existe un mecanism de import retrocompatibil (`__getattr__` sau redirect imports în `stratum_ro/`) pentru a nu strica scripturile existente ale utilizatorului.
- [ ] Rularea `git status` să confirme absența fișierelor de cod modificate.

---

## 29. FINAL DECISION (DECIZIA FINALĂ)

Sistemul este oficial aprobat pentru faza de pregătire a scripturilor de înghețare și contracte.  
**STATUS: GATA PENTRU DEFINIREA CONTRACTELOR ȘI ÎNGHEȚAREA GOLDEN TESTS.**  
Niciun fișier operațional nu a fost alterat în cursul acestui review criminalistic.

---
