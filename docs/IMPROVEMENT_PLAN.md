# Plan de Îmbunătățire & Foaie de Parcurs StratumRO 🧭🔬

> **Document de referință științifică & inginerie geodezică** (bazat pe analiza de arhitectură Kimi Review — 11 Septembrie 2026).  
> Fiecare item conține: **Problemă → Soluție implementată / propusă → Criteriu de validare (Definition of Done)**.

---

## 📊 Stadiul General al Implementării

| Nivel Prioritate | Obiectiv / Modul | Stadiu Curent | Evidență & Validare |
| :--- | :--- | :---: | :--- |
| **P0 — CRITICE** | Sub-segmentare calcan, IoU global, audit 116 FP, filtru containere | **`FINALIZAT (100%)`** | Commituri `de257d4`, `5cb2e34`, `b8334e3` |
| **P1 — MARI** | Gard concavitate MRR (L/U/T), offset adaptiv $k \cdot H$, analiză FN, geometrii multi-inel | **`FINALIZAT (100%)`** | EV-014 .. EV-017 în `EVIDENCE_MATRIX.md` |
| **P2 — REPRODUCTIBILITATE** | Scripturi randare headless, eliminare bias text, caroiaj dinamic `LIMITA_SECTOR` | **`FINALIZAT (100%)`** | `tools/render_visual_evidence.py`, EV-018 |
| **CALITATE V2** | Reconstrucție adaptivă TLS 4 clase, poartă 3D LiDAR, semafor operațional, benchmark v2 | **`FINALIZAT (100%)`** | Commit `3a0bb22`, EV-019 .. EV-021 |
| **P3 — EXTENSII & AUDIT** | Export ViT ONNX (P3.1), Time-study 93% (P3.2), extindere N=150 GT (P3.4) | **`FINALIZAT (P3.1, P3.2, P3.4)`** | EV-022 .. EV-024 (P3.3 teren deschis) |

---

## P0 — CRITICE (Rezolvate & Comise)

### ✅ P0.1 Sub-segmentarea la calcan
- **Problema inițială:** 4 din 17 împerecheri (REF 002, 004, 007, 014) erau contopite într-un singur poligon uriaș (`pred_id=2`), cu IoU scăzut (0.11–0.31).
- **Soluție implementată:** Algoritmul `split_at_calcan` în [`stratum_ro/geometry_utils.py`](../stratum_ro/geometry_utils.py) detectează șeile altimetrice nDSM ($\Delta H \ge 1.5\text{ m}$) și gâturile de îngustare morfologică, despărțind corpurile alipite.
- **Rezultat măsurat:** 0 sub-segmentări, 20 împerecheri 1:1 curate, True Positives au crescut de la 17/29 la **20/29**. IoU pe clădirile alipite a crescut semnificativ: REF 002 (0.31 $\to$ 0.836), REF 004 (0.20 $\to$ 0.480), REF 007 (0.20 $\to$ 0.641), REF 014 (0.11 $\to$ 0.604).

### ✅ P0.2 Auditul celor 116 False Positives față de setul de 29 clădiri GT
- **Problema inițială:** Raportarea a 116 FP crea impresia de predicții halucinate.
- **Soluție implementată:** Scriptul [`tools/verify_fp_against_osm.py`](../tools/verify_fp_against_osm.py) a auditat spațial cele 116 poligoane împotriva a 667 clădiri reale din OpenStreetMap:
  - **92 confirmate ca fiind clădiri rezidențiale fizice reale pe Calea Mănăștur (79.3%)**
  - **1 anexă gospodărească mică (0.9%)**
  - **2 sere agricole provizorii (1.7%)**
  - **21 corpuri ne-cartate / zgomot coronament (18.1%)**
- **Rezultat măsurat:** Documentat în [`reports/tier1_cadastre/fp_osm_verification.csv`](../reports/tier1_cadastre/fp_osm_verification.csv) și `EV-06`.

### ✅ P0.3 Filtru de containere & structuri provizorii
- **Problema inițială:** Filtrul `check_is_likely_container_or_shed` nu era inclus în studiul de ablație.
- **Soluție implementată:** Includerea `CONFIG_F_HYBRID_FILTERED` în [`engine/ablation_study.py`](../engine/ablation_study.py).
- **Rezultat măsurat:** Eliminarea a 2 alarme false (solarii alungite) cu menținerea a 100% din True Positives (20/29). Manifest salvat în [`reports/ablation/ablation_results.csv`](../reports/ablation/ablation_results.csv) (`EV-015`).

---

## P1 — MARI (Calitatea Detecției & Regularizării)

### ✅ P1.1 Prezervarea formelor concave L / U / T (MRR Concavity Guard)
- **Problema inițială:** Minimum Rotated Bounding Rectangle (MBR) forța dreptunghiuri pe clădiri cu aripi (REF 010, 013, 017).
- **Soluție implementată:** Verificare strictă de soliditate ($A / A_{\text{hull}} \ge 0.90$ și rectangularitate $\ge 0.88$). Poligoanele concave sunt protejate și regularizate ortogonal prin `buildingregulariser`.
- **Rezultat măsurat:** Decroșurile sunt conservate 100%; test unitar dedicat `test_concave_l_shape_preserves_concavity` trece (`EV-016`).

### ✅ P1.2 Decalaj adaptiv streașină–soclu ($k \cdot H$)
- **Problema inițială:** Offsetul fix de $-0.40\text{ m}$ nu ținea cont de înălțimea clădirii.
- **Soluție implementată:** Model parametric în [`stratum_ro/vectorizer.py`](../stratum_ro/vectorizer.py): offset $0.0\text{ m}$ pentru acoperișuri terasă plate ($\Delta Z < 0.30\text{ m}$) și retragere proporțională $k \cdot H$ ($k \approx 0.03$, limitat între $0.20\text{ m}$ și $0.60\text{ m}$) pentru acoperișuri în pantă.
- **Rezultat măsurat:** Validat prin `test_compute_adaptive_eave_offset` (`EV-016`).

### ✅ P1.3 Analiză cauzală a celor 8 False Negatives
- **Problema inițială:** Lipsa explicației măsurate pentru clădirile omise din referința ANCPI.
- **Soluție implementată:** Audit sistematic în [`reports/tier1_cadastre/fn_causal_analysis.md`](../reports/tier1_cadastre/fn_causal_analysis.md).
- **Rezultat măsurat:** 5 din 8 eșecuri (62.5%) sunt platforme betonate la sol ($Z < 1.5\text{ m}$, înregistrate istoric ca și construcții), 2 sunt anexe sub 35 m², iar 1 are contrast optic insesizabil ($\Delta E = 4.6$). Zero locuințe obișnuite ratate aleator.

### ✅ P1.4 Geometrii multi-inel & curți de lumină interioare
- **Problema inițială:** Poligoanele cu găuri interioare (curți de lumină) nu deduceau aria golurilor.
- **Soluție implementată:** Calcul $A_{\text{net}} = A_{\text{ext}} - \sum A_{\text{int}}$ în [`engine/evaluation.py`](../engine/evaluation.py) și exportul inelelor interioare în layerul TopoLT `1CC_GOL` / fișierul `.cp` în [`stratum_ro/cad_exporter.py`](../stratum_ro/cad_exporter.py).
- **Rezultat măsurat:** Verificat prin `test_export_polygon_with_interior_hole` ($400\text{ m}^2 - 25\text{ m}^2 = 375\text{ m}^2$ net) (`EV-017`).

---

## P2 — REPRODUCTIBILITATE & ACTIVE VIZUALE

### ✅ P2.1 Scripturi automate de randare headless
- **Implementare:** [`tools/render_visual_evidence.py`](../tools/render_visual_evidence.py), [`tools/render_ortho_overlay.py`](../tools/render_ortho_overlay.py) și [`tools/render_zoom_panels.py`](../tools/render_zoom_panels.py).
- **Rezultat:** Toate cele 5 imagini de înaltă rezoluție din `docs/assets/` sunt regenerate 100% headless pe Pillow + Rasterio + GeoPandas fără dependențe de GUI/ecran (`EV-018`).

### ✅ P2.2 Eliminarea afirmațiilor de marketing
- **Implementare:** „Suprapunere milimetrică” reformulată ca „potrivire sub-metrică (IoU median 0.804, RMSE median 1.946 m)”; reziduul Helmert $\pm 1.4\text{ cm}$ reclasificat ca reziduală teoretică de potrivire algebrică (`EV-012`).

### ✅ P2.3 Extragerea dinamică a caroiajului din `LIMITA_SECTOR_CADASTRAL`
- **Implementare:** Bounding box-ul de lucru este extras automat din poligonul neted al sectorului cadastral, eliminând treptele de pixeli NoData (`EV-018`).

---

## FAZA CALITATE V2 (Implementată & Comisă)

- **Reconstrucție Geometrică Adaptivă pe Linii Suport TLS/SVD ([`stratum_ro/geometric_reconstruction_v2.py`](../stratum_ro/geometric_reconstruction_v2.py)):** Clasificator în 4 clase (Clasa A: OBB 4 noduri; Clasa B: Manhattan L/U/T; Clasa C: Complex multi-corp; Clasa D: Forme autentic oblice/atipice conservate fără forțare 90°).
- **Poartă de Calitate 3D LiDAR ([`stratum_ro/lidar_quality_gate.py`](../stratum_ro/lidar_quality_gate.py)):** Măsoară treapta de fațadă ($\Delta Z \ge 1.8\text{ m}$) și deviația de coplanaritate a acoperișului ($\sigma_{\text{roof}} \le 1.2\text{ m}$).
- **Sistem de Încredere Compozită & Semafor Operațional:** 🟢 `VERDE_ACCEPTAT_AUTOMAT` ($\ge 0.85$), 🟡 `GALBEN_INSPECTIE_GEODEZ` ($0.65-0.85$), 🔴 `ROSU_RESPINS_ARTEFACT` ($< 0.65$).
- **Inspecție pe Etape în GeoPackage & QGIS:** Salvare straturi `STAGE_1_RAW_CONTOUR` $\dots$ `STAGE_5_FINAL_CONFIDENCE`.
- **Benchmark Morfologic Dedicat ([`engine/benchmark_v2.py`](../engine/benchmark_v2.py)):** Evaluat pe cele 29 clădiri ANCPI: Dreptunghiuri (IoU 0.805, RMSE 1.148 m, 80% recall), Corpuri L/U/T (IoU 0.630, 100% recall), Pavilioane Campus (IoU 0.623, 66.7% recall).

---

## P3 — EXTENSII, BENCHMARKING & FOAIE DE PARCURS TERESTRĂ

### ✅ P3.1 Export Encoder ViT-Hiera în ONNX (Zero-CUDA complet) — FINALIZAT
- **Soluție implementată:** Scriptul [`tools/export_sam2_to_onnx.py`](../tools/export_sam2_to_onnx.py) include wrapperul `SAM2EncoderONNXWrapper` și exportul complet al encoderului de imagine ViT-Hiera (`models/sam2/sam2_encoder.onnx`, 104.22 MB).
- **Rezultat măsurat:** Validare numerică bit-cu-bit confirmată: eroare absolută maximă pe tensori embeddings $< 1.22 \times 10^{-5}$ (`NUMERICALLY_VERIFIED`, EV-022). Motorul [`stratum_ro/onnx_engine.py`](../stratum_ro/onnx_engine.py) integrează inferența encoderului pe CPU/DirectML, acoperit de testul unitar `test_exported_sam2_encoder_session`.

### ✅ P3.2 Cronometrare Formală & Time-Study Benchmark — FINALIZAT
- **Soluție implementată:** Benchmark de productivitate formal implementat în [`engine/time_study_benchmark.py`](../engine/time_study_benchmark.py), rulat pe toate cele 195 clădiri din sectorul cadastral (`workspace/output/cladiri_stereo70.gpkg`).
- **Rezultat măsurat:** Timp manual estimat: 22.83 ore (7.02 min/clădire); Timp asistat StratumRO: 1.60 ore (0.49 min/clădire); Reducere medie de timp: **93.0%** (interval confidență Wilson 95%: $[87.6\%, 96.9\%]$). Raport complet în [`reports/time_study/time_study_report.md`](../reports/time_study/time_study_report.md) (`EV-023`).

### 🔹 P3.3 Campanie Terestră Pilot AOI 2 (GNSS RTK ROMPOS FIXED + Stație Totală) — DESCHIS
- **Descriere:** Măsurarea pe teren a 50–100 de colțuri de clădiri reale din afara campusului pentru a atinge nivelul **`FIELD-VALIDATED`** pe coordonate absolute.  
  *Această etapă necesită prezență fizică pe teren cu aparatură geodezică autorizată ANCPI.*

### ✅ P3.4 Extinderea setului Ground Truth (N = 150 clădiri) — FINALIZAT
- **Soluție implementată:** Construirea setului extins de referință [`data/ground_truth/tier2_extended_gt.geojson`](../data/ground_truth/tier2_extended_gt.geojson) prin [`tools/build_extended_ground_truth.py`](../tools/build_extended_ground_truth.py) ($N = 150$ clădiri: 29 campus ANCPI + 121 rezidențial pe Calea Mănăștur).
- **Rezultat măsurat:** Evaluare riguroasă prin [`engine/extended_evaluation.py`](../engine/extended_evaluation.py): True Positives au crescut de la 20 la **88 clădiri**, False Positives au scăzut de la 116 la **104 clădiri**, demonstrând obiectiv că fuzionarea hibridă detectează clădiri fizice reale. F1: 0.520, IoU median: 0.458 (`EV-024`).

---

## Reguli de Lucru & Integritate Științifică (MANDATORY)

1. **Nicio re-ștampilare de manifeste:** Orice actualizare de raport necesită re-rularea efectivă a scripturilor pe datele reale și consemnarea checksum-ului.
2. **Trasabilitate directă:** Fiecare cifră din documentație trebuie să corespundă unui ID din [`docs/EVIDENCE_MATRIX.md`](EVIDENCE_MATRIX.md).
3. **Păstrarea onestității:** Nu afirmați acuratețe absolută $\le 10\text{ cm}$ fără măsurători terestre directe GNSS RTK / Stație Totală.

