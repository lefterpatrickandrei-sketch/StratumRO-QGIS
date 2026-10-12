# AGENTS.md — StratumRO Engineering & Evidence-First Governance Guide

## 1. Project Identity & Purpose
**StratumRO** is an industrial-grade geomatics and MLOps platform oriented toward Romanian pre-cadastral workflows and engineered to produce technical deliverables compatible with applicable specifications (including technical layer conventions under ANCPI Ordinul nr. 600/2023 and Stereo 70 EPSG:3844), with mandatory human and professional verification.

> **Defensible Positioning:** StratumRO is an **assisted pre-cadastral workflow (Human-in-the-Loop)** that accelerates manual digitization by ~89%. It is **NOT** a fully autonomous legal registration system. Generating technical CAD layers (DXF, .CP, PAD tables) does not constitute autonomous legal compliance; official cadastral registration strictly requires validation and sign-off by a licensed geodetic surveyor (*persoană autorizată ANCPI*).

---

## 2. Codebase Map & Source of Truth
* **Core Implementation:** [`stratum_ro/`](stratum_ro/)
  - `vectorizer.py`: 90° regularization, canonical 4-vertex rectangle fitting, topology cleanup, planar partition.
  - `cad_exporter.py`: TopoLT standard CAD export (`1CC`, `2CC`, `CP`, `VARFURI`, `NUMERE_PCT`), automated PAD coordinate table drawing, `.CP` interchange file generation.
  - `volumetric_3d.py`: True 3D LoD1 solid shell extrusion (`MultiPolygonZ` in GeoPackage), RANSAC 3D roof plane fitting, OGC CityJSON v1.1 export.
  - `onnx_engine.py`: Cross-platform ONNX Runtime inference wrapper supporting DirectML on compatible Windows/DirectX hardware when available, with multithreaded CPU fallback.
  - `processing_provider.py` & `cadastral_algorithm.py`: QGIS Processing Framework integration (`StratumROCadastralAlgorithm`).
  - `stratum_ro_dockwidget.py` & `stratum_ro.py`: PyQGIS desktop plugin GUI and dockwidget.
  - `lidar_processor.py` & `ortho_extractor.py`: Airborne LiDAR (LAS/LAZ) processing, nDSM generation, and orthophoto VRT slicing.
* **Evaluation & Audits:** [`engine/`](engine/)
  - `evaluation.py`: Rigorous geodetic evaluation metrics (IoU, Hausdorff Distance, Boundary RMSE, Centroid Shift, PASCAL/COCO matching, Wilson score confidence intervals).
  - `ablation_study.py`: Formal 5-configuration ablation study (Configs A through E).
* **Automated Test Suite:** [`stratum_ro/test/`](stratum_ro/test/)
  - **260 unit tests** (251 passed, 9 skipped, 0 failed — *verified in runtime on 2026-10-12*) covering vectorization, CAD export, TopoLT layers, PAD tables, .CP export, ONNX wrappers, 3D extrusion, QGIS Processing metadata, TaskSpec/capability matching, ContextEngine resource snapshots, RiskEngine policy, DataProfiler L0-L5 validation, ProvenanceChain lineage, Simulation perturbation, and the six multimodal provider paths (OpenAI, Anthropic, NVIDIA NIM, OpenRouter/UnionAlpha, Ollama, Gemini).
* **Ground Truth & Reference Data:** [`data/ground_truth/`](data/ground_truth/)
  - Official reference datasets, including `tier1_teren.geojson` (29 real cadastral buildings in Stereo 70) and `cluj_combined_unique_150.geojson` (150 unique reference buildings).
* **Official Reports & Architecture Maps:** [`reports/`](reports/) & [`docs/`](docs/)
  - Quality gate verification, audit resolutions, architectural documentation, and model inventories.
  - **Visual System Maps:** [`docs/architecture/STRATUMRO_VISUAL_SYSTEM_MAP.md`](docs/architecture/STRATUMRO_VISUAL_SYSTEM_MAP.md) (Mermaid diagrams) & [`docs/architecture/visual_system_map.html`](docs/architecture/visual_system_map.html) (Interactive dashboard).

---

## 3. The 8 Evidence-First Scientific Rules (MANDATORY)

For every technical claim, benchmark result, or metric, agents must classify it into exactly one of:

1. **IMPLEMENTED:** Code exists on disk and is importable.
2. **TESTED:** Automated unit or regression tests executed cleanly with reported exit code.
3. **REPRODUCED:** Independently re-executed on a clean environment, reproducing identical numbers.
4. **MEASURED:** An empirical numerical value exists from a specific script execution.
5. **VALIDATED:** Compared against an appropriate independent reference dataset.
6. **FIELD-VALIDATED:** Verified against ground-truth terrestrial survey coordinates (e.g., GNSS RTK, Total Station). *Never claim field validation without physical terrestrial survey logs!*
7. **THEORETICAL:** Expected mathematically (e.g. algebraic Procrustes residual, geometric extrusion), but not yet empirically proven in the field.
8. **UNVERIFIED:** Claim exists in text or previous audits, but cannot be reproduced from current code/data.

### 3.1 Obligatory Visual & Multi-Factorial Validation Gate
Nicio fază de dezvoltare sau livrabil pre-cadastral nu poate fi declarat „VALIDAT” exclusiv pe baza testelor unitare de cod (`python -m unittest`). Validarea geomatică completă impune în mod obligatoriu următoarele dovezi tangibile:
1. **Hărți de Confuzie Spațială (RGB Ortho Overlay):** Suprapunere tri-cromatică pe ortofotoplanul nativ conform SpaceNet / ISPRS: 🟩 Verde=TP (IoU >= 0.50), 🟥 Roșu=FP (evaluat critic dacă e clădire reală ne-adnotată sau zgomot), 🟦 Albastru=FN (omisiuni).
2. **Coridorul de Toleranță Legală ANCPI (+/- 10 cm):** Randarea grafică a benzii tampon de +/- 10 cm în jurul contururilor terestre oficiale pentru verificarea încadrării în marja Ordinului ANCPI nr. 600/2023.
3. **Analiza Dislocării Radiale (Quiver Plot):** Vizualizarea vectorilor de deplasare (ΔX, ΔY) la nodurile clădirii pentru a separa decalajul sistematic al streșinii (30–80 cm) de erorile algoritmice.
4. **Randarea Grafică a Desenului CAD TopoLT:** Inspecția planșei DXF randate (nu doar a codului sursă) pentru a verifica lizibilitatea straturilor `1CC`, `2CC`, `CP`, caroiajului Stereo 70 și a tabelului de coordonate PAD cu paginare pe coloane.
5. **Transparența celor Trei Denominatori:** Se raportează întotdeauna explicit triada: (True Positives, Referințe Totale, Predicții Totale).

---

## 4. Working Conventions & Anti-Hallucination Guardrails
- **Current Implementation ≠ Target Platform:** Do not treat future Phase 4 target architecture concepts (e.g. Evidence Graph, 18 workflow modes, full sensor simulation) as already implemented on disk.
- **No Blind Feature Inflation:** Never add new features, frameworks, or dependencies merely because they sound impressive. Make StratumRO **more trustworthy**, not just larger.
- **Never Hide Recall Limits or False Positives:** In Phase 3 (E9), the pipeline reduced false positives from 90 to 22, but recall remained at 6.15% (4 TP out of 65 references). Always report all 3 denominators explicitly (TP, matched references, total predictions). StratumRO generates candidates that can be evaluated through existing metrics, not guaranteed ground truth.
- **Assisted Pre-Cadastre Only:** StratumRO is strictly an **assisted pre-cadastral digitizing candidate (Human-in-the-Loop)**. Never claim autonomous legal registration.
- **Testing Standard:** When modifying code, always execute:
  ```bash
  venv\Scripts\python -m unittest discover stratum_ro/test
  ```
  Report the exact test count (e.g., `251 passed, 9 skipped, 0 failed` out of 260 discovered). A skipped test is **NOT** a passed test.
- **Python Environment:** Always use the local virtual environment in [`venv/`](venv/).

---

## 5. Actor Roles & Operational Model

### Active Project Operational Flow
```text
USER (TU)
   ↓
ANTIGRAVITY (Primary Development & Execution Engine)
   ↓
STRATUMRO
   ├─ QGIS Desktop / Processing
   ├─ Date reale (LiDAR, Ortofoto, Cadastru)
   ├─ Tool-uri / MCP
   └─ Provideri AI configurați (OpenRouter, NVIDIA NIM, Local)
   ↓
KILO (Adversarial Reviewer)
   ↓
GITHUB origin/main (Authoritative Shared Source of Truth)
```

### Actor Definitions
* **Antigravity (Primary Development & Execution Engine):**
  Inspects workspace, runs tests, executes real experiments, drives QGIS verification, produces visual evidence, commits and pushes verified code.
* **Kilo (Adversarial Reviewer):**
  Performs second-opinion code reviews, checks for metric leakage, identifies no-op experiments, and challenges over-engineered architectures.
* **ChatGPT (Architecture & System Reasoning Partner):**
  Synthesizes source-of-truth documentation, reviews system designs, and creates detailed execution plans for Antigravity.
* **Claude Desktop (RETIRED / Historical Only):**
  **NU mai face parte din fluxul activ al proiectului; feedback-ul anterior este doar istoric.** Nu este utilizat în execuția curentă a sistemului.
* **GitHub (`origin/main`):**
  The single authoritative shared source of truth for code, tests, and data.

---

## 6. Model Routing & Execution Guardrails

1. **Geometry / Math → Deterministic Local:**
   - All spatial transformations, Helmert 2D, 90° CAD orthogonalization, eave retraction offsets, polygon areas, perimeters, PAD coordinate tables, and topology cleanup MUST run exclusively through local deterministic Python/GEOS/GDAL math. Zero LLM hallucinations permitted.
2. **Building Segmentation → SAM2 / Local:**
   - Optical delineation uses Meta SAM 2 Hiera (PyTorch / ONNX DirectML) cross-validated with local LiDAR nDSM height statistics.
3. **Reasoning & Code Audits → OpenRouter / Kilo:**
   - Verified models: `meta-llama/llama-3.3-70b-instruct` (722ms) and `meta-llama/llama-3.1-8b-instruct` (540ms).
4. **Visual Multimodal Verification → Gemini free tier (NVIDIA NIM is NOT reliable here):**
   - Measured 2026-10-08: `gemini-3.1-flash-lite` scores **8/9** on falsification controls using a describe-first prompt; `meta/llama-3.2-11b-vision-instruct` scores **1/9** (approves pure noise) and must not be used for delivery decisions.
   - The prompt must ask the model to **describe before it classifies**. A leading "is this a real building?" question drops Gemini to 2/9 and produces false approvals (`scripts/vlm_prompt_ablation.py`).
5. **Provider Status Reality (MEASURED by live HTTP probe, 2026-10-08, `scripts/provider_credit_status.py`):**
   - NVIDIA NIM: `OPERATIONAL` — HTTP 200 on `meta/llama-3.2-11b-vision-instruct`. **Not usable for VLM audit**: it passed only 1/9 falsification controls (it approves pure noise).
   - Google Gemini: `OPERATIONAL (free tier, quota-limited)` — `gemini-3.1-flash-lite` answered and passed 4/4 transport + discrimination controls. Free tier is ~15 RPM; bursts return HTTP 429.
   - OpenRouter / UnionAlpha: `DEAD — NO CREDITS`. Balance measured at **−0.2169 USD** (`total_credits=0`, `total_usage=0.2169`); every request returns HTTP 402. `OPENROUTER_API_KEY` and `UNION_ALPHA_API_KEY` are the **same key**.
   - OpenAI direct: `DEAD — NO CREDITS` (HTTP 429 "You have no credits remaining").
   - Anthropic direct: `DEAD — NO CREDITS` (HTTP 400 "Your credit balance is too low").
   - Cerebras: `DEAD — PAYMENT REQUIRED` (HTTP 402).
   - SambaNova: `DEAD — INVALID KEY` (HTTP 401).
   - Ollama: `OPERATIONAL (local, no credits)` — `llava:13b`, `minicpm-v:8b`, `qwen3:8b`, `qwen3-agent:8b`, `dolphin3:8b`. Vision latency 22–49 s.
   - Local Mock: `OPERATIONAL` (0.0 ms air-gapped deterministic baseline).
   - **Consequence:** as of 2026-10-08 there is no paid LLM/VLM budget available. Any pipeline step that requires a frontier model is blocked until a key is topped up. Do not assume credit availability from an older note in this file.


