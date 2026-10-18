# STRATUMRO — PHASE 1: GOLDEN BASELINE & SCIENTIFIC FREEZE DOSSIER

**Document Type:** Master Phase 1 Closure Dossier & Pre-Restructuring Scientific Gate  
**Project:** StratumRO Industrial-Grade Geomatics & GeoAI Platform  
**Repository Commit:** `c9768641acb0bef0806593c84f549acba5960703` (Branch: `main`)  
**Audit Standard:** 8 Evidence-First Scientific Rules (AGENTS.md §3)  
**Baseline Status:** `PASS`  
**Date:** 2026-09-20  
**Authoritative Engine:** Antigravity  

---

## 1. MISIUNE ÎNDEPLINITĂ

Faza 1 a implementării a fost finalizată cu succes în mod **STRICT READ-ONLY pe codul de producție**. S-a stabilit baza de referință științifică incontestabilă necesară pentru a garanta principiul suprem:

> **„ARCHITECTURAL CLEANUP MUST NOT CHANGE SCIENTIFIC BEHAVIOR.”**

Orice viitoare restructurare în Faza 2 și Faza 3 va trebui să treacă testele automate de înghețare stabilite aici, demonstrând **deviație numerică de zero milimetri** pe coordonatele cadastrale.

---

## 2. ARTEFACTELE LIVRATE ÎN FAZA 1

Toate fișierele cerute la §42 și §43 au fost generate pe disk:

```text
workspace/baseline/
├── repository_baseline.json          # Metadate commit, platformă, pachete, teste
├── manifest_ground_truth.json        # 14 dataset-uri de referință (SHA-256, mărimi, featuri)
├── manifest_critical_modules.json   # 23 fișiere de cod sursă înghețate
├── manifest_experiments.json        # 20 predicții GeoJSON din EXP_000..EXP_009
├── golden_geometry_baseline.json     # 4 clădiri TP USAMV + 3 cazuri canonice vectorizer
├── golden_metrics_baseline.json      # Metrice oficiale E9 (Recall 6.15%, IoU 0.6659)
├── test_baseline.json                # Raport complet teste (219 total, 210 passed, 9 skipped)
└── GOLDEN_BASELINE_REPORT.md         # Raportul tehnic complet de baseline

stratum_ro/test/
└── test_phase1_golden_freeze.py      # Suită automată unittest pentru regresia Fazei 1

STRATUMRO_PHASE1_GOLDEN_BASELINE.md   # Acest document master la rădăcina repo-ului
```

---

## 3. CE A FOST ÎNGHEȚAT FACTUAL

1. **Datele de Referință Ground Truth (14 fișiere):**
   - `data/ground_truth/tier1_teren.geojson` (`4edecae807e795bb...`)
   - `data/derived_reference/cluj_combined_unique_150.geojson` (`967c3028da1e23c2...`)
   - Fișierele de test fixtures `case_01_L_shape.geojson` ... `case_07_sf_maria_calcan_merge.geojson`.

2. **Codul de Producție Critic (23 module):**
   - `stratum_ro/vectorizer.py` (`edb9a7fe81497763...`)
   - `stratum_ro/cad_exporter.py` (`371ce3fcfd58bcd4...`)
   - `stratum_ro/volumetric_3d.py` (`3a9a4e5e5de513a5...`)
   - `engine/evaluation.py` (`31eb4f4833a76896...`)
   - `stratum_ro/ai/router.py`, `task_graph.py`, `executor.py`, `provenance.py`, `risk.py`.

3. **Geometria Celor 4 Clădiri TP USAMV:**
   - `USAMV_TP_01`: Arie $744.94\text{ m}^2$, Perimetru $143.26\text{ m}$, 90 vârfuri, $\text{IoU} = 0.5054$.
   - `USAMV_TP_02`: Arie $2235.86\text{ m}^2$, Perimetru $352.48\text{ m}$, 152 vârfuri, $\text{IoU} = 0.6316$.
   - `USAMV_TP_03`: Arie $1032.10\text{ m}^2$, Perimetru $131.78\text{ m}$, 51 vârfuri, $\text{IoU} = 0.8916$.
   - `USAMV_TP_04`: Arie $417.82\text{ m}^2$, Perimetru $86.72\text{ m}$, 45 vârfuri, $\text{IoU} = 0.6350$.

4. **Metricele Benchmark-ului Cluj–USAMV (E9):**
   - $\text{TP} = 4, \text{FP} = 22, \text{FN} = 61, \text{Total Ref} = 65$.
   - $\text{Precision} = 15.38\%, \text{Recall} = 6.15\%, \text{F1} = 8.79\%, \text{IoU} = 0.6659, \text{RMSE} = 3.04\text{ m}$.

---

## 4. CE NU A PUTUT FI ÎNGHEȚAT / CE ESTE LIMITARE CUNOSCUTĂ

1. **Măsurători Terestre RTK:** Factual absente în repository. Nu există carnete de măsurători RTK în fișiere text/binar. Verificarea terestră rămâne cerință legală a fluxului cadastral uman.
2. **Grila TransdatRO NTv2:** Fișierul `.gsb` oficial nu este integrat în runtime-ul Python CLI. PROJ Helmert 7 parametri rămâne baseline-ul activ.
3. **Convenția de Afișare a Axelor X/Y:** Inversiunea din `cad_exporter.py` a fost lăsată neatinsă conform regulii stricte de la §22. Va fi adresată în Faza 3 prin adaptor dedicat.

---

## 5. REZULTATUL SUITEI DE TESTE

```text
Ran 219 tests in 28.964s
OK (skipped=9)
```
- **210 teste trecute (100% din cele executabile în CLI Windows)**.
- **9 teste sărite** strict din cauza lipsei mediului C++ PyQGIS GUI bindings.
- Noul modul [`stratum_ro/test/test_phase1_golden_freeze.py`](file:///c:/Users/lefpa/Downloads/QGIS-AI/stratum_ro/test/test_phase1_golden_freeze.py) a rulat cele 5 teste de integritate în 0.015s și a confirmat invarianța completă.

---

## 6. CE ESTE PERMIS ȘI CE ESTE INTERZIS ÎN FAZA 2

### Permis în Faza 2 (Contracts & Boundaries):
- Definirea interfețelor abstracte (`BaseDomainPack`, `IGeoProcessor`, `IProvenanceRecorder`).
- Definirea claselor de date și contractelor de tipuri (type annotations, Pydantic/dataclasses).
- Documentarea specifică a granițelor de pachet.

### Strict Interzis în Faza 2:
- NU muta fișiere de cod sursă.
- NU șterge module vechi.
- NU modifica algoritmii geometrici sau formulele din `vectorizer.py`.
- NU altera fișierele Ground Truth.

---

## 7. DECIZIA FAZEI 1: `PASS`

Toate verificările au trecut cu succes. Baza de referință științifică este înghețată și securizată.

**STATUS FINAL: PHASE 1 COMPLETE — READY FOR PHASE 2.**