# AUTOAUDIT STRATUMRO — Faza 1: QGIS, Cadastru + PUG Autonom
**Data:** 2026-10-19 | **Auditor:** Antigravity (Gemini 3.8 Flash High) | **Mod:** Strict Read-Only + Verificări Active

---

## A. Git și Siguranță

> **Verdict A (3 rânduri):**
> Repository-ul este public pe GitHub, iar istoricul conține o cheie activă NVIDIA API în `tools/StratumRO_legacy.ipynb` încă prezentă în `HEAD`.
> `main` local și branch-ul `fix/stratumro-verification-20261018` sunt la `ca208fb`, fiind cu 23 de commituri în fața `origin/main` (`5125134`).
> `.env` nu este urmărit în Git, iar istoricul conține peste 100 MB de GeoTIFF-uri ortofoto și GPKG-uri, însă zero fișiere LAS/LAZ.

- **Stare Git locală [REAL]:** Branch curent `main`, `HEAD = ca208fb40da7109eabec874ed451c0e8104550d1`. `git status` conține 6 fișiere modificate nesalvate și 13 fișiere neversionate. Există 9 worktree-uri active (`git worktree list`).
- **Integrare GitHub [REAL]:** `origin/main` este la `5125134`. Branch-ul de integrare activ este `fix/stratumro-verification-20261018` (la `ca208fb`, PR #4 draft). Pe `origin/main` lipsesc 23 de commituri (`77c1a0e`...`ca208fb`: rafinare opțiunea B, audit vizual 216 cazuri, reparare QGIS și teste portabile).
- **Vizibilitate Repository [REAL]:** `git ls-remote --heads https://github.com/lefterpatrickandrei-sketch/StratumRO-QGIS.git` executat fără autentificare a returnat toate referințele; repository-ul este public accesibil pe internet.
- **Secrete & .env [REAL]:** `.env` există pe disc, este ignorat prin `.gitignore:56` și nu a fost niciodată comis. Însă în commitul `35c6964` a fost comis fișierul `tools/StratumRO_legacy.ipynb` (rămas în `HEAD` la linia 210) care conține o cheie reală NVIDIA API (`nvapi-...`, lungime 70 caractere). Cheile din `stratum_ro/test/test_phase4_orchestration.py:12` (`sk-abcdef...`) sunt mock-uri sintetice de test.
- **Date licențiate în istoric [REAL]:** `git rev-list --objects --all` conține 382 obiecte > 1 MB. Sunt comise mozaicuri ortofoto Cluj (`workspace/output/cache_tile_Cluj-*.tif`, 8 tile-uri x 15.55 MB = 124.4 MB; `active_ortho_crop.tif` 14.3 MB; `T18_native_seam.tif` 10.6 MB) și GPKG-uri mari (`cladiri_stereo70.gpkg` 19.4 MB). Niciun fișier `.las` sau `.laz` nu a fost comis în istoric (`set()`).

---

## B. Duplicate și Consolidare

> **Verdict B (3 rânduri):**
> Duplicarea între rădăcină și `domain/cadastre_ro/` este asimetrică: versiunea din domeniu a pierdut blocul critic `ARBORI_CORONAMENT`.
> Există 4 perechi identice prin hash și 3 perechi divergente, importate în peste 25 de module active.
> Planul de consolidare din faza 4 riscă regresii majore dacă transformă rădăcina în forwarder înainte de sincronizarea completă a domeniului.

- **Confirmare `cad_exporter.py` vs `domain/cadastre_ro/exporter.py` [REAL]:**
  - `stratum_ro/cad_exporter.py:311-320` conține blocul `ARBORI_CORONAMENT` (utilizat de `run_hybrid_full_aoi.py:542` pentru exportul conturului coronamentelor).
  - `stratum_ro/domain/cadastre_ro/exporter.py` nu conține acest bloc (dimensiune 20.857 bytes vs 21.476 bytes).
- **Confirmare `cadastral_product.py` vs `domain/cadastre_ro/product.py` [REAL]:**
  - `git diff` arată că fișierele sunt identice cu excepția liniilor 23-24 (importurile din pachet vs import din `.exporter`).
- **Alte perechi găsite în repo [REAL]:**
  - *Hash identic:* `candidate_generator.py` == `domain/vision/candidates.py`; `lidar_quality_gate.py` == `domain/lidar/quality_gate.py`; `onnx_engine.py` == `domain/vision/engine.py`; `vegetation_filter.py` == `domain/vision/vegetation.py`.
  - *Divergente:* `stratum_ro/lidar_processor.py` (23.3 KB) vs `domain/lidar/processor.py` (9.8 KB); `stratum_ro/mask_fusion.py` (6.2 KB) vs `domain/vision/fusion.py` (5.8 KB).
- **Importatori [REAL]:** `cad_exporter` are 21 importatori (inclusiv `cadastral_product.py`, `app.py`, `stratum_ro_dockwidget.py`, `run_hybrid_full_aoi.py`). `domain/cadastre_ro` are 9 importatori, majoritatea scripturi scratch.
- **Ordine sigură de consolidare propusă [PLAN]:**
  1. *Pasul 1:* Backport obligatoriu în `domain/` al tuturor blocurilor lipsă (`ARBORI_CORONAMENT`, extinderile din `lidar_processor`).
  2. *Pasul 2:* Rularea suitei complete de teste pe importurile din `domain/`.
  3. *Pasul 3:* Transformarea modulelor din rădăcină în forwardere compatibile (`from stratum_ro.domain.cadastre_ro.exporter import *`).
  4. *Pasul 4:* Migrarea treptată a apelanților din `tools/` și `stratum_ro/`.

---

## C. QGIS Live și MCP

> **Verdict C (3 rânduri):**
> Puntea socket pe portul 9876 este activă și conectată la QGIS Desktop 3.40.0-Bratislava cu proiectul comun încărcat (106 straturi).
> Din cele 9 teste omise în CI, 8 trec cu succes în QGIS live, iar 1 eșuează legitim din cauza absenței binarelor de traducere (`af.qm`).
> În afara socketului, există o cuplare strânsă: peste 35 de scripturi și module importă direct `qgis.core` și `qgis.utils.iface`.

- **Punte socket port 9876 & Versiune QGIS [REAL]:** Conexiune confirmată pe `127.0.0.1:9876`. Interogarea `execute_code` via `tools/qgis_mcp_query.py` raportează `Qgis.QGIS_VERSION = '3.40.0-Bratislava'`. Proiect activ: `inspectie_corectii.qgs` (106 straturi).
- **Rulare cele 9 teste omise în CI direct în QGIS live [REAL]:**
  1. `test_dockwidget_tabs_and_controls` (`test_ai_assistant_ui.py`): **PASS**
  2. `test_qgis_environment` (`test_qgis_environment.py`): **PASS**
  3. `test_projection` (`test_qgis_environment.py`): **PASS**
  4. `test_stereo70_3844` (`test_qgis_environment.py`): **PASS**
  5. `test_stereo70_31700` (`test_qgis_environment.py`): **PASS**
  6. `test_vertical_marea_neagra` (`test_qgis_environment.py`): **PASS**
  7. `test_icon_png` (`test_resources.py`): **PASS**
  8. `test_dockwidget_ok` (`test_stratum_ro_dockwidget.py`): **PASS**
  9. `test_qgis_translations` (`test_translations.py`): **FAIL** (`af.qm not found — run 'make' to compile translations first`).
- **Audit unelte MCP (`mcp/stratumro_server.py`) [REAL]:** 32 unelte înregistrate.
  - *Funcționale cap-coadă:* `system.get_system_info`, `system.run_command`, `project.get_context`, `layers.list`, `context.*` (4 unelte), `memory.*` (3 unelte), `raster.inspect`, `raster.extract_chip`, `geometry.validate_topology`, `cadastral.validate_ancpi`, `vector.regularize`, `vector.apply_eave_offset`, `vector.planar_partition`, `results.create_preview`, `export.export_gpkg`, `export.export_cityjson`.
  - *Blocate prin politică de permisiuni (ASK):* `export.export_topolt_dxf`, `export.export_cp`, `results.commit_to_project` (necesită flag explicit `approved=True`).
  - *Dependente de date/hardware extern:* `segmentation.run_sam2` (cere checkpoint local SAM2), `lidar.*` (cere fișier LAS valid pe disc).
- **Puncte de cuplare QGIS în afara PlatformService/socket [REAL]:**
  - În pachet: `stratum_ro.py`, `stratum_ro_dockwidget.py` (UI/PyQt), `processing_provider.py` & `cadastral_algorithm.py` (`QgsProcessingAlgorithm`), `qgis_render_order.py`, `ai/context.py:246` (`from qgis.core import QgsProject`), `ai/worker.py` (PyQt signals).
  - În `tools/`: 35 scripturi importă direct `qgis.core` (`QgsProject`, `QgsVectorLayer`, `QgsMapSettings`) și `qgis.utils.iface` pentru execuție în consolă/socket.

---

## D. Cadastru Cap-Coadă

> **Verdict D (3 rânduri):**
> Comanda minimă reproductibilă este `python tools/build_dual_products.py`, generând GPKG, DXF și .CP în 19.54s pe date locale.
> Codul setează necondiționat `validare_ancpi = "ADMIS"` în 4 fișiere, mascând lipsa recepției juridice ANCPI.
> Estimările esențiale (regim de înălțime din nDSM, lățime streașină) sunt salvate ca atribute definitive, fără etichetă de estimare.

- **Cea mai mică comandă reproductibilă [REAL]:**
  - `.\venv\Scripts\python.exe tools/build_dual_products.py`
  - Timp execuție: **19.54s** modul cadastral (219 clădiri C1, 11 anexe C2, 256 arbori aliniament, 26 arbori eliminați de pe acoperișuri).
  - Livrabile generate: `workspace/output/cadastru_ancpi.gpkg` (552 KB), `cadastru_ancpi.dxf` (7.13 MB), `cadastru_ancpi.cp` (186 KB).
- **Separare pași automați vs pași umani (HITL) [REAL]:**
  - *Automat:* Ortogonalizare 90°, filtrare spațială arbori de pe clădiri (buffer 0.8m), calcul Sc/perimetru, export DXF (layere `CONSTRUCTII`, `ANEXE`, `ARBORI`, `STALPI`) și tabele PAD.
  - *Necesită Om:* Identificarea relației parcelă-corp (C1/C2 vs extinderi), verificare vizuală a streșinilor reale, eliminarea falsurilor pe platforme betonate, numere cadastrale reale și semnătura digitală a geodezului autorizat.
- **Apariții `validare_ancpi = "ADMIS"` [REAL]:**
  - `stratum_ro/cadastral_product.py:75` (clădiri principale) și `line 122` (anexe).
  - `stratum_ro/domain/cadastre_ro/product.py:75` și `line 122`.
  - `stratum_ro/regulatory_consensus.py:114, 170` (prompturi LLM care forțează rezoluție ADMIS).
  - `tools/validate_cadastral_topology.py:314`.
- **Model de stări propus [PLAN]:**
  - Înlocuirea stringului hardcodat `"ADMIS"` cu ciclul: `PROPUS_AUTOMAT` $\rightarrow$ `VALIDAT_GEOMETRIC` $\rightarrow$ `PENDING_SURVEYOR_REVIEW` $\rightarrow$ `ACCEPTAT` / `RESPINS` / `INCOMPLET_NECESITA_TEREN`.
- **Lipsa etichetării estimărilor în livrabil [REAL]:**
  - `cadastral_product.py:59-68` calculează `regim_inaltime` împărțind `h_med` la 3.2m, dar îl scrie în câmpul `regim_inaltime` (fără prefix `est_` sau coloană de proveniență).
  - Retragerea de streașină este aplicată heuristic fără atribut care să indice că amprenta la sol derivă din acoperiș fotogrammetric.

---

## E. PUG Cap-Coadă

> **Verdict E (3 rânduri):**
> `pug_product.py` generează un GeoPackage cu 5 straturi analitice în 15.66s, dar nu extrage niciun element din planșe PUG scanate.
> Celulele UTR sunt o grilă artificială de 150x150m, iar starea fitosanitară și etajele sunt calculate prin formule fixe.
> În UAT Iepurești/Giurgiu, datele provin din servicii publice (APIA, ANAR, cIMeC, OSM), lipsind complet vectorizarea automată a planșelor PUG PDF.

- **Ce produce concret `pug_product.py` [REAL]:**
  - Executat în 15.66s via `tools/build_dual_products.py`: `workspace/output/urbanism_pug.gpkg` (1.77 MB) și `raport_indicatori_pug.json`.
  - Straturi generate: `CLADIRI_LOD1_VOLUMETRIC` (219 corpuri cu H_cornisa, H_coama, Sd), `ANEXE_VOLUMETRICE` (11 corpuri), `REGISTRU_SPATII_VERZI_ARBORI` (256 puncte), `CORONAMENTE_FOND_VEGETAL` (poligoane buffer $r=h \times 0.35$), `INDICATORI_UTR_GRID` (24 celule grid).
- **Analitic vs Extras din planșe [REAL]:**
  - *100% Analitic / Heuristic:* Grila `UTR_GRID` de 150 m x 150 m (2.25 ha) este generată prin `shapely.geometry.box` (nu reprezintă UTR-uri oficiale din PUG). Înălțimea de nivel este fixată la 3.0 m (`floor(h/3.0)`). Starea arborilor este setată fix la `"Corespunzatoare"`.
  - *Extras din planșe PUG:* **0%**. Niciun modul nu vectorizează planșe PUG desenate sau scanate.
- **Starea pe UAT real (Iepurești/Giurgiu) [REAL]:**
  - În `projects/UAT_Iepuresti/` există 52 de fișiere (inclusiv `UAT_Iepuresti_PUG_Master.gpkg`, 187 MB).
  - Toate datele au fost culese din surse vectoriale deschise: ANCPI (limita UAT), APIA 2025 (blocuri fizice agricole), cIMeC (situri RAN), EEA (Natura 2000), ANAR (hidrografie), OSM (drumuri, clădiri), Sentinel-2 (benzi spectrale).
- **Ce lipsește pentru PUG autonom [PLAN]:**
  1. Georeferențierea automată a planșelor PUG raster/PDF pe caroiajul Stereo 70.
  2. Segmentarea cromatică a zonificării funcționale (ZTR/UTR) conform standardului Ghid GP 038/99.
  3. Parser OCR/LLM pentru extragerea indicatorilor urbanistici (POT max, CUT max, H max) din Regulamentul Local de Urbanism (RLU).

---

## F. Măsurare și Metrici

> **Verdict F (3 rânduri):**
> Referința „Tier 1” din `tier1_teren.geojson` are doar 29 de clădiri și provine din ANCPI WFS, nu din măsurători RTK de teren cu telemetru.
> `metrics.py` implementează doar metrici geometrice pereche (IoU, Hausdorff, RMSE, deviație unghiulară), lipsind metricile de detecție.
> Precizia și recall-ul sunt în prezent complet nemăsurate pe toate loturile de clădiri; propunem un protocol CPU în 5 secunde.

- **Analiză Ground Truth existent [REAL]:**
  - `data/ground_truth/tier1_teren.geojson` conține 29 de poligoane. Proprietatea `survey_source` este `'ANCPI_CONSTRUCTII_STEREO70'`.
  - Atributele menționate în `data/ground_truth/README.md` (`equipment: Leica GS18 T`, `eave_measured_offset_m`, `h_cornisa_m`) nu există în fișier. Datele sunt un export WFS, nu un etalon de măsurătoare directă pe soclu.
- **Metrici existente în `stratum_ro/core/geometry/metrics.py` [REAL]:**
  - `compute_iou`, `compute_hausdorff` (densificat la 0.10 m), `compute_boundary_rmse` (eșantionare la 0.20 m), `compute_centroid_shift`, `compute_angular_deviation`.
  - *Lipsesc:* Evaluarea la nivel de instanță: Precision, Recall, F1-Score, corelarea bipartită (Hungarian matching) și eroarea relativă de arie.
- **Confirmare: Precizie/Recall sunt nemăsurate [REAL]:** Confirmat. Niciun script din repository nu raportează o curbă Precision-Recall sau un scor F1 măsurat independent pe detecția corpurilor de clădire.
- **Protocol minim de evaluare pe Cluj îngheț fără GPU [PLAN]:**
  1. *Date:* Compară `selected_v4_orthogonal/lot3_orthogonal.gpkg` + `lot4_orthogonal.gpkg` cu `tier1_teren.geojson`.
  2. *Potrivire spațială:* Căutare bipartită cu prag IoU $\ge 0.50$ pentru definirea True Positives ($TP$).
  3. *Calcul metrici detecție:* $\text{Precision} = TP / (TP + FP)$, $\text{Recall} = TP / (TP + FN)$.
  4. *Calcul metrici de contur pe perechi:* Mediana și percentila 95 pentru IoU, Hausdorff și Boundary RMSE via `metrics.py`.
  5. *Resurse:* Rulare 100% CPU via GeoPandas/Shapely în sub 5 secunde.

---

## G. Contradicții în Documentație

> **Verdict G (3 rânduri):**
> Există contradicții majore între documentele vechi de audit (care afirmă 89% economie de timp) și codul real care generează timpii aleator.
> Poziționarea oscilează între „asistent pre-cadastral Tier 3/4” și „platformă autonomă până la semnătura geodezului”.
> Propunem marcarea a 7 documente istorice cu eticheta SUPERSEDED pentru a asigura claritatea direcției.

- **Contradicții identificate [REAL]:**
  1. *Economie de timp:* `docs/EVIDENCE_MATRIX.md`, `docs/RAPORT_AUDIT_12_REZOLUTIE.md` și `docs/TECHNICAL_STATUS.md` proclamă „~89% economie de timp demonstrată”. În cod (`engine/time_study_benchmark.py`), timpii sunt eșantionați din distribuții `np.random.normal/exponential` sintetice. `PROJECT_STATE.md:61` confirmă că economia nu este dovedită prin studiu de operatori.
  2. *Identitatea produsului:* `docs/architecture/STRATUMRO_PRODUCT_ARCHITECTURE.md` (v1.0) descrie StratumRO ca „asistent pre-cadastral pentru clienți QGIS”. `AGENTS.md:16` și promptul proprietarului definesc StratumRO drept o platformă de coordonare prin MCP care automatizează lucrarea până la semnătură.
  3. *Certificare legală vs Conformitate:* Rapoartele istorice de audit afirmă „0% conformitate legală directă”, în timp ce exporturile cadastrale marchează clădirile ca `validare_ancpi = "ADMIS"`.
  4. *Etalonul Ground Truth:* `data/ground_truth/README.md` descrie măsurători RTK de teren inexistente în GeoJSON-ul real.
- **Documente propuse spre marcare ca înlocuite (SUPERSEDED) [PLAN]:**
  1. `docs/RAPORT_AUDIT_10_REZOLUTIE.md`
  2. `docs/RAPORT_AUDIT_11_REZOLUTIE.md`
  3. `docs/RAPORT_AUDIT_12_REZOLUTIE.md`
  4. `docs/RAPORT_FINAL_CERTIFICARE_CADASTRALA.md`
  5. `docs/TECHNICAL_STATUS.md`
  6. `docs/EVIDENCE_MATRIX.md`
  7. `docs/architecture/STRATUMRO_PRODUCT_ARCHITECTURE.md` (de actualizat la v2.0 conform `SYSTEM_MAP.md`).

---

## H. Harta Autonomiei

> **Verdict H (3 rânduri):**
> Cadastrul are motoare geometrice 100% deterministe, dar este blocat de lipsa determinării fațadei și de obligația legală a semnăturii.
> PUG-ul este autonom doar la sinteza analitică a straturilor deschise, lipsindu-i complet procesarea planșelor urbanistice oficiale.
> Niciunul dintre fluxuri nu poate funcționa legal fără revizia umană (HITL) a inginerului geodez / urbanist.

### Tabel Cadastru Autonom

| Pas Flux Cadastral | Cine decide azi | Dovadă | Ce lipsește pentru autonom | Risc |
|---|---|---|---|---|
| 1. Definire AOI & Date | Om / Agent | `run_regional_roofs.py:34` | Descoperire autonomă date ANCPI/orto | Erori de NoData / zonă greșită |
| 2. Detecție / Segmentare | Automat | `regional_roofs.py:120` | Model calibrat pe texturi românești | Fals pozitive (platforme, șantiere) |
| 3. Retragere streașină | Automat (Heuristic) | `vectorizer.py:310` | Determinare fațadă din LiDAR/sol | Suprapunere limite de proprietate |
| 4. Ortogonalizare (90°) | Automat | `roof_simple_geometry.py:150` | Fitter adaptiv pentru clădiri curbe | Distorsionare forme arhitecturale |
| 5. Curățare topologică | Automat | `cadastral_product.py:91` | Rezoluție contextuală calcan/corp comun | Tăiere eronată corpuri lipite |
| 6. Clasificare C1/C2 | Automat (Heuristic) | `cadastral_product.py:72` | Consultare carte funciară / titlu | Identitate cadastrală greșită |
| 7. Validare ANCPI | Om (simulat `ADMIS`) | `cadastral_product.py:75` | Verificator riguros Ordinul 600/2023 | Respingere dosar oficiu teritorial |
| 8. Semnătură & Livrabile | Om (Geodez autorizat) | `mcp/stratumro_server.py:200` | Asigurare răspundere juridică | Nulitate juridică documentație |

### Tabel PUG Autonom

| Pas Flux PUG | Cine decide azi | Dovadă | Ce lipsește pentru autonom | Risc |
|---|---|---|---|---|
| 1. Limită UAT & Intravilan | Automat (Harvester) | `build_master_pug_gpkg.py:38` | Extragere intravilan propus din PDF | Incompatibilitate intravilan aprobat |
| 2. Delimitare UTR | Automat (Grilă falsă) | `pug_product.py:211` | Extragere limite UTR din planșe PUG | Indicatori calculați pe careuri oarbe |
| 3. Extragere RLU | Nimeni (Inexistent) | `stratum_ro/pug_product.py` | Parser RLU (text/tabelare reglementări) | Necunoaștere restricții de construire |
| 4. Volumetrie LoD1 | Automat (Heuristic) | `pug_product.py:76` | Validare niveluri (autorizații/mansarde)| Erori de volum și suprafață desfășurată |
| 5. Registru Spații Verzi | Automat (Heuristic) | `pug_product.py:169` | Recunoaștere specii / inspecție teren | Neconformitate Legea 24/2007 |
| 6. Bilanț teritorial | Automat (pe grilă) | `pug_product.py:245` | Bilanț pe UTR-uri reale Legea 350 | Indicatori urbanistici eronați |
| 7. Redactare planșe A3 | Automat | `projects/UAT_Iepuresti` | Validare cromatică Ghid GP 038/99 | Planșe respinse la avizare CTU |
| 8. Aprobare HCL / Avize | Exclusiv Om (Consiliu) | Legea 350/2001 | Imposibil de autonomizat legal | Act administrativ fără valoare legală |

---

## Întrebări Către Proprietar (Ordonate după Impact)

1. **Securitate critică:** Autorizați invalidarea imediată la furnizor a cheii NVIDIA API expuse în `tools/StratumRO_legacy.ipynb` și rescrierea istoricului Git (via `git-filter-repo` sau BFG), având în vedere că repo-ul este public pe GitHub?
2. **Integrare GitHub:** Doriți deschiderea unui PR sau merge al branch-ului `fix/stratumro-verification-20261018` (`ca208fb`) în `origin/main` (`5125134`) pentru a sincroniza cele 23 de commituri de progres pe ramura principală?
3. **Consolidare rădăcină vs domeniu:** Confirmați prioritatea de a aduce îmbunătățirile din rădăcină (`ARBORI_CORONAMENT`, extinderile LiDAR) în `domain/cadastre_ro/` înainte de a transforma fișierele din rădăcină în forwardere?
4. **Stări cadastrale:** Sunteți de acord cu eliminarea atributului hardcodat `validare_ancpi = "ADMIS"` și înlocuirea lui cu modelul `PROPUS_AUTOMAT` / `PENDING_SURVEYOR_REVIEW` / `ACCEPTAT`?
5. **Direcția PUG:** Extragerea automată din planșe PUG scanate (PDF raster/RLU) este o prioritate a Fazei 1 sau rămânem strict pe agregarea serviciilor deschise (APIA, ANCPI, ANAR, OSM) așa cum s-a procedat la Iepurești?
6. **Ground Truth real:** Avem la dispoziție măsurători GNSS-RTK reale de teren (coordonate la soclu + streașină măsurată) pentru a constitui un etalon Tier 1 autentic în Cluj, distinct de datele ANCPI WFS?
7. **Documente istorice:** Aprobați marcarea oficială ca `SUPERSEDED` a rapoartelor vechi de audit ce conțin cifra nefondată de „89% economie de timp”?
8. **Date binare în Git:** Doriți curățarea celor peste 100 MB de GeoTIFF-uri și GPKG-uri istorice din Git și transferarea lor strict în storage extern sau LFS configurat?

---

## Cele 5 Lucruri de Făcut Primele (Propunere — Fără Execuție)

1. **Rotire cheie API & Sanitize:** Revocarea tokenului `nvapi-...` din portalul NVIDIA și eliminarea lui din fișierul de notebook `tools/StratumRO_legacy.ipynb`.
2. **Sincronizare bloc `ARBORI_CORONAMENT`:** Copierea logicii de export a coronamentelor în `stratum_ro/domain/cadastre_ro/exporter.py` și verificarea unit-testelor CAD.
3. **Refactorizare stări `validare_ancpi`:** Înlocuirea valorii fixe `"ADMIS"` cu stări explicite de audit cadastral (`PROPUS_AUTOMAT` / `PENDING_SURVEYOR_REVIEW`) în generatoarele de produs.
4. **Implementare metrici detecție în `metrics.py`:** Adăugarea funcțiilor de evaluare la nivel de obiect (Precision, Recall, F1-Score cu Hungarian matching) pe CPU.
5. **Marcare documentație depășită:** Adăugarea unui banner de avertizare `SUPERSEDED` pe rapoartele vechi de audit care conțin cifre nesusținute de codul real.

---
**Fișiere noi create în acest audit:**
- `workspace/autoaudit_20261019/REPORT.md` (raportul curent).
*Niciun alt fișier nu a fost modificat, creat sau șters.*
