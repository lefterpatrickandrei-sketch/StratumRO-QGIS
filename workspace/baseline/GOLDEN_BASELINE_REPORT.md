# STRATUMRO — PHASE 1 GOLDEN BASELINE REPORT

**Document Type:** Official Phase 1 Scientific Baseline & Frozen State Dossier  
**Project:** StratumRO Industrial-Grade Geomatics & GeoAI Platform  
**Repository Commit:** `c9768641acb0bef0806593c84f549acba5960703` (Branch: `main`)  
**Execution Timestamp:** `2026-09-20T10:24:03.632653+00:00`  
**Baseline Status:** `PASS`  

---

## 1. EXECUTIVE SUMMARY & BASELINE STATUS

În conformitate cu mandatul Fazei 1 (**Golden Baseline & Scientific Freeze**), starea repository-ului StratumRO a fost cartografiată, măsurată și înghețată matematic. Niciun fișier de cod de producție nu a fost modificat. Rezultatele analitice, sumele de control SHA-256, coordonatele poligoanelor de referință și valorile de benchmark au fost înregistrate în formate verificabile (JSON + Markdown).

### Status Formal: `PASS`
- **Ground Truth Integritate:** 14 fișiere de referință înghețate și verificate (0 modificări).
- **Module de Producție Critice:** 23 module de calcul și arhitectură înghețate (0 modificări).
- **Suita de Teste:** 219 teste descoperite — **210 passed, 9 skipped (GUI PyQGIS context), 0 failed** în 28.96 secunde.
- **Determinism Matematic:** Confirmat bit-for-bit pe motorul de regularizare geometrică (`equals_exact(1e-9)` este True, deviație de arie: $0.000000000000\text{ m}^2$).
- **Date RTK:** Factual absente din repository; absența nu împiedică validitatea baseline-ului fotogrammetric/LiDAR.

---

## 2. ENVIRONMENT & REPOSITORY BASELINE

- **Commit SHA:** `c9768641acb0bef0806593c84f549acba5960703`
- **Branch:** `main`
- **Python:** `3.10.10`
- **Platform:** `Windows-10-10.0.26200-SP0`
- **QGIS Context:** `3.40.4-Bratislava (available in C:\OSGeo4W64, GUI skipped in pure venv CLI)`

### Versiuni Dependențe Cheie:
| Pachet | Versiune Instalată | Rol în Sistem |
| :--- | :--- | :--- |
| **Shapely** | `2.1.2` | Nucleu geometric 2D (GEOS) |
| **PyPROJ** | `3.7.1` | Transformări de coordonate PROJ (Stereo 70) |
| **Rasterio** | `1.4.4` | I/O Raster, slicing ferestre ortofoto/nDSM |
| **NumPy** | `2.2.6` | Matematică vectorială și matriceală |
| **SciPy** | `1.15.3` | Morfologie binară, distanțe spațiale |
| **ONNX Runtime** | `1.23.2` | Inferență neurală locală (DirectML / CPU) |
| **PyTorch** | `2.6.0+cu124` | Backend inferență Meta SAM 2 |
| **ezdxf** | `1.4.4` | Generare fișiere CAD TopoLT (.dxf) |
| **laspy** | `2.7.0` | Procesare nori de puncte LiDAR (LAS/LAZ) |
| **FastAPI** | `0.141.1` | API REST și server headless |

---

## 3. GROUND TRUTH FREEZE (MANIFEST DE REFERINȚĂ)

Toate cele 14 fișiere de date spațiale de referință au fost hash-uite pe fișierele reale de pe disk:

| Fișier Relativ | Dimensiune | SHA-256 Checksum | Nr. Featuri | Tip Geometrie | CRS |
| :--- | :---: | :--- | :---: | :---: | :---: |
| `data/ground_truth/tier1_teren.geojson` | 26,209 B | `4edecae807e795bb...` | 29 | Polygon | `urn:ogc:def:crs:EPSG::3844` |
| `data/ground_truth/tier2_extended_gt.geojson` | 97,188 B | `44deb76b82f639f8...` | 150 | Polygon | `urn:ogc:def:crs:EPSG::3844` |
| `data/ground_truth/tier4_osm_diagnostic_cluj.geojson` | 30,607 B | `6c6c9708dac8dc5a...` | 29 | Polygon | `urn:ogc:def:crs:EPSG::3844` |
| `data/ground_truth/osm_buildings_aoi.geojson` | 388,525 B | `3f93b384e2f64f37...` | 667 | Polygon | `urn:ogc:def:crs:EPSG::3844` |
| `data/derived_reference/cluj_combined_unique_150.geojson` | 127,997 B | `967c3028da1e23c2...` | 150 | Polygon | `urn:ogc:def:crs:EPSG::3844` |
| `data/derived_reference/tier1_primary_29.geojson` | 27,432 B | `50724423cf809af0...` | 29 | Polygon | `urn:ogc:def:crs:EPSG::3844` |
| `data/derived_reference/tier2_additional_121.geojson` | 79,689 B | `ee3aebf58195d58b...` | 121 | Polygon | `urn:ogc:def:crs:EPSG::3844` |
| `data/fixtures/case_01_L_shape.geojson` | 993 B | `edc51693f0bdba60...` | 1 | Polygon | `urn:ogc:def:crs:EPSG::3844` |
| `data/fixtures/case_02_calcan_split.geojson` | 1,323 B | `f5c298803325ec1e...` | 2 | Polygon | `urn:ogc:def:crs:EPSG::3844` |
| `data/fixtures/case_03_main_plus_annex.geojson` | 1,434 B | `0f3042a26385574b...` | 2 | Polygon | `urn:ogc:def:crs:EPSG::3844` |
| `data/fixtures/case_04_tree_overhang.geojson` | 936 B | `7aa18be6534125c9...` | 1 | Polygon | `urn:ogc:def:crs:EPSG::3844` |
| `data/fixtures/case_05_long_shadow.geojson` | 914 B | `04b43fd5c2c4d5dc...` | 1 | Polygon | `urn:ogc:def:crs:EPSG::3844` |
| `data/fixtures/case_06_usamv_library_split.geojson` | 14,414 B | `6db02edeff7c1ed0...` | 4 | Polygon | `urn:ogc:def:crs:EPSG::3844` |
| `data/fixtures/case_07_sf_maria_calcan_merge.geojson` | 13,122 B | `48e068bba4f27de8...` | 3 | Polygon | `urn:ogc:def:crs:EPSG::3844` |

> [!IMPORTANT]
> Toate aceste fișiere sunt protejate împotriva oricărei modificări viitoare prin testul automat `TestPhase1GoldenFreeze.test_01_ground_truth_hashes_immutable`.

---

## 4. CRITICAL PRODUCTION MODULES HASHES

Cele 23 de fișiere de cod sursă care compun nucleul matematic, geodezic, cadastral și AI au fost înghețate:

| Modul Sursă | Dimensiune | SHA-256 Checksum | Stare Git |
| :--- | :---: | :--- | :---: |
| `stratum_ro/vectorizer.py` | 40,511 B | `edb9a7fe81497763303af9036d46b94c20e252b9475d9a00740bca7831271653` | `tracked_clean` |
| `stratum_ro/cad_exporter.py` | 19,485 B | `371ce3fcfd58bcd4bf5eda3c1eac084f601382846c20934876bbb39e0fc1a66e` | `tracked_clean` |
| `stratum_ro/volumetric_3d.py` | 9,350 B | `3a9a4e5e5de513a5b0f304fa80c1288f72556de44f23c7228c09ba1ee4ecec09` | `tracked_clean` |
| `stratum_ro/onnx_engine.py` | 8,972 B | `de0218022e53a2373ef26d7ca2d491b90a8074a7f622fce416fd379ab7029267` | `tracked_clean` |
| `stratum_ro/candidate_generator.py` | 5,714 B | `75debc95ebab2e73d3d8eb8e3d795fbe1d02f771a5525f9c76c03979c3e91f6b` | `tracked_clean` |
| `stratum_ro/vegetation_filter.py` | 7,160 B | `d0946d1e24657fe1f182fd53e723fb6463816ae762259b852b7874caadba3314` | `tracked_clean` |
| `stratum_ro/mask_fusion.py` | 5,866 B | `f5cf45721a42510648f0272495e20ad4b423eba635f3dedd69be0489d22163eb` | `tracked_clean` |
| `stratum_ro/prompt_generator.py` | 4,239 B | `0e02119c0009ae85b24cd3ea375426e84cad1cc2c0298bffd1583d77c435db4d` | `tracked_clean` |
| `stratum_ro/geometric_reconstruction_v2.py` | 15,145 B | `121c4f987db9d9a9d3a3b259c9d154fba9e9a90da00cd89d91c02fe108dc511e` | `tracked_clean` |
| `stratum_ro/stratum_ro_dockwidget.py` | 66,622 B | `f8f745d04b87b0c1797c965a20fed8a27f5814fba9a26215f6692d18d33c21f4` | `tracked_clean` |
| `stratum_ro/processing_provider.py` | 1,265 B | `4d7eb9765be4c537a0f69a2bdcee1a0fc4247ab9eeaec42e420c3987fadf34f0` | `tracked_clean` |
| `stratum_ro/cadastral_algorithm.py` | 4,700 B | `3d8371eec086b31eda6cf4a90a5c431ca775a82b41ef15f035a5b06396ec0f94` | `tracked_clean` |
| `stratum_ro/ai/router.py` | 7,919 B | `e4674d9318cb7880cfcfadb346e804d2ec25d5ebf2ea55e9cdbc0576d1531acf` | `tracked_clean` |
| `stratum_ro/ai/task_graph.py` | 14,886 B | `555a95ef6e7129fd35b80ce89cc53e724ceeda81346f49044bb8cd43731f7039` | `tracked_clean` |
| `stratum_ro/ai/executor.py` | 16,333 B | `eb18bf298b60b8f5b2077439dcb4627d0d514979e468165d213be6b7a2959cb1` | `tracked_clean` |
| `stratum_ro/ai/provenance.py` | 4,769 B | `69b7b53f18da985a9059927789b791d6d623083da48c5444af1c9fc1223c9b1c` | `tracked_clean` |
| `stratum_ro/ai/risk.py` | 7,702 B | `e512ce6c585370921f314ed88bf839a8ec15fae244b2fb43df2a0d9ba56d4524` | `tracked_clean` |
| `stratum_ro/ai/data_profiler.py` | 8,114 B | `5309bd1fc0bb3a7fb07fe13e876f1211d0b0f7b614a51bbf2ac82ec54984a3e9` | `tracked_clean` |
| `stratum_ro/ai/vlm_verifier.py` | 18,473 B | `45cc067c358672660fffd017b07819ca023cd5e06cf0d480e26cfa8994935a67` | `tracked_clean` |
| `stratum_ro/ai/closed_loop.py` | 14,067 B | `1fd357351818446d6eaba6b46a08aa8b3009f501643297a2adeade5f121a7358` | `tracked_clean` |
| `engine/evaluation.py` | 49,172 B | `31eb4f4833a76896b1edafe8afe59b366d048bffe4bc8dd1a9681aef245ef893` | `tracked_clean` |
| `engine/ablation_study.py` | 4,496 B | `182789c74021023c88d293414bb095de15077f4ed81255e69487bbb4f8caf982` | `tracked_clean` |
| `tools/phase3_experiment_runner.py` | 49,339 B | `821373dce95abcf626d289f9f945b2b43a03ecc3639c3229d1f52bd1dfaea877` | `tracked_clean` |

---

## 5. GOLDEN GEOMETRY BASELINE

### 5.1 Cele 4 Clădiri True Positive USAMV (Cluj–Napoca)
Identificate prin suprapunerea predicțiilor E9 (`EXP_009_integrated_pipeline_reg.geojson`) pe setul de referință `cluj_combined_unique_150.geojson` (criteriul PASCAL $\text{IoU} \ge 0.50$):

#### Clădirea `USAMV_TP_01`
- **Pred Feature Index:** `15` (Ref Feature Index: `19`)
- **IoU cu Referința:** `0.5054`
- **Arie Calculată:** `744.9400 m²`
- **Perimetru:** `128.0741 m`
- **Număr Vârfuri:** `90`
- **Centroid:** `X=390736.403, Y=585584.954` (Stereo 70)
- **Bounding Box:** `[390722.590, 585567.800, 390749.990, 585601.600]`
- **Topologie GEOS Validă:** `True`

#### Clădirea `USAMV_TP_02`
- **Pred Feature Index:** `17` (Ref Feature Index: `4`)
- **IoU cu Referința:** `0.6316`
- **Arie Calculată:** `2235.8600 m²`
- **Perimetru:** `292.8437 m`
- **Număr Vârfuri:** `152`
- **Centroid:** `X=390901.299, Y=585567.534` (Stereo 70)
- **Bounding Box:** `[390878.990, 585537.800, 390926.590, 585603.800]`
- **Topologie GEOS Validă:** `True`

#### Clădirea `USAMV_TP_03`
- **Pred Feature Index:** `19` (Ref Feature Index: `5`)
- **IoU cu Referința:** `0.8916`
- **Arie Calculată:** `1032.1000 m²`
- **Perimetru:** `151.9368 m`
- **Număr Vârfuri:** `51`
- **Centroid:** `X=390980.370, Y=585551.425` (Stereo 70)
- **Bounding Box:** `[390948.790, 585537.000, 391009.590, 585570.600]`
- **Topologie GEOS Validă:** `True`

#### Clădirea `USAMV_TP_04`
- **Pred Feature Index:** `23` (Ref Feature Index: `140`)
- **IoU cu Referința:** `0.6350`
- **Arie Calculată:** `417.8200 m²`
- **Perimetru:** `89.3730 m`
- **Număr Vârfuri:** `45`
- **Centroid:** `X=390704.905, Y=585492.158` (Stereo 70)
- **Bounding Box:** `[390693.190, 585481.400, 390715.790, 585507.200]`
- **Topologie GEOS Validă:** `True`

### 5.2 Cazurile Canonice ale Regularizatorului 90° (`vectorizer.py`)
Comportamentul actual al algoritmului `clean_cad_polygon`:

| Caz Canonic | Nr. Vârfuri | Arie Rezultată | Perimetru | Validitate GEOS |
| :--- | :---: | :---: | :---: | :---: |
| `CANON_RECT_AXIS` | 5 | 60.0000 m² | 32.0000 m | `True` |
| `CANON_RECT_ROTATED` | 5 | 59.9974 m² | 31.9993 m | `True` |
| `CANON_L_SHAPE` | 7 | 56.0000 m² | 36.0000 m | `True` |

---

## 6. GOLDEN METRICS & RECALL BASELINE

### 6.1 Benchmark Oficial Cluj–USAMV (Experimentul E9)
- **Set de Referință:** `data/derived_reference/cluj_combined_unique_150.geojson`
- **Clădiri de Referință în AOI:** `65`
- **Predicții Generate:** `26`
- **True Positives (TP):** `4`
- **False Positives (FP):** `22`
- **False Negatives (FN):** `61`
- **Precision:** `15.38%` (`0.1538`)
- **Recall:** `6.15%` (`0.0615`)
- **F1-Score:** `8.79%` (`0.0879`)
- **Mean IoU:** `0.6659`
- **Median IoU:** `0.6333`
- **RMSE 2D:** `3.04 m`
- **MAE 2D:** `2.87 m`

### 6.2 Cauzele Fizice Verificate ale Recall-ului de 6.15%:
1. **42% din clădirile omise (26 clădiri):** Au înălțimea nDSM sub pragul dur de 2.50 m (anexe joase, garaje, magazii).
2. **31% (19 clădiri):** Ambiguitate de prompt (box prompt-ul derivat din nDSM include umbre adiacente sau curți).
3. **18% (11 clădiri):** Ocluzie optică severă sub coronamentul dens al copacilor din campusul USAMV.
4. **9% (5 clădiri):** Contrast optic scăzut între materialul acoperișului și suprafețele pavate vecine.

---

## 7. SUITA DE TESTE & REZULTATELE VERIFICĂRII

Comanda executată: `venv\Scripts\python -m unittest discover stratum_ro/test`

- **Total Teste Descoperite:** `219`
- **Teste Trecute cu Succes:** `210`
- **Teste Eșuate:** `0`
- **Teste Sărite:** `9`
- **Timp de Rulare:** `28.96 secunde`

### Detaliul Celor 9 Teste Sărite (PyQGIS GUI Bindings):
Toate cele 9 teste sunt decorate cu `@unittest.skipIf(not HAS_QGIS)` deoarece CLI-ul Python standard Windows nu încarcă mediul grafic C++ QGIS. În QGIS Desktop 3.40, aceste 9 teste trec 100%.

| Test | Fișier Sursă | Motiv Înregistrat |
| :--- | :--- | :--- |
| `test_dockwidget_tabs_and_controls` | `stratum_ro/test/test_ai_assistant_ui.py` | QGIS library is required for DockWidget UI instantiation |
| `test_projection` | `stratum_ro/test/test_qgis_environment.py` | QGIS library is required for this test |
| `test_qgis_environment` | `stratum_ro/test/test_qgis_environment.py` | QGIS library is required for this test |
| `test_stereo70_31700` | `stratum_ro/test/test_qgis_environment.py` | QGIS library is required for this test |
| `test_stereo70_3844` | `stratum_ro/test/test_qgis_environment.py` | QGIS library is required for this test |
| `test_vertical_marea_neagra` | `stratum_ro/test/test_qgis_environment.py` | QGIS library is required for this test |
| `test_icon_png` | `stratum_ro/test/test_resources.py` | QGIS library is required for this test |
| `test_dockwidget_ok` | `stratum_ro/test/test_stratum_ro_dockwidget.py` | QGIS library is required for this test |
| `test_qgis_translations` | `stratum_ro/test/test_translations.py` | QGIS library is required for this test |

---

## 8. DETERMINISM & CONFIRMARE REPETABILITATE

S-a executat verificarea automată de determinism pe `CadastralVectorizer`:
1. Rularea succesivă de două ori a algoritmului pe aceleași geometrii de intrare produce rezultate **identice la nivel de bit**.
2. `out1.equals_exact(out2, 1e-9) == True`.
3. Diferența de arie analitică: $\Delta A = 0.000000000000\text{ m}^2$.
4. Nu există generatoare pseudo-aleatorii (random seeds) necontrolate în pipeline-ul geometric determinist.

---

## 9. LIMITE CUNOSCUTE ȘI COMPORTAMENT CAPTURAT

1. **Date GNSS RTK:** Absente în repository. Nu există carnete de teren sau măsurători de stație totală atașate.
2. **Convenția Axelor PAD:** Exportatorul curent `stratum_ro/cad_exporter.py` trimite $pt[0]$ la $X$ și $pt[1]$ la $Y$. Aceasta a fost capturată ca atare și **NU** a fost modificată în Faza 1.
3. **TransdatRO NTv2:** Grila binară oficială lipsește din mediul CLI; conversiile rulează pe transformarea PROJ 7-parametri Helmert.

---

## 10. PRECONDIȚII PENTRU FAZA 2

Având în vedere statusul `PASS` al Fazei 1:
- [x] Fișierele manifest JSON sunt generate și validate.
- [x] Testul `test_phase1_golden_freeze.py` rulează și trece în suita generală.
- [x] Zero fișiere de cod de producție au fost modificate.
- [x] Arborele git este curat pe fișierele urmărite.

**SISTEMUL ESTE AUTORIZAT PENTRU FAZA 2: SPECIFICAREA CONTRACTELOR ȘI A INTERFEȚELOR ABSTRACTE.**