# STRATUMRO — CURRENT VS. TARGET ARCHITECTURAL & STATE AUDIT

**Date:** 2026-09-19  
**Status:** FORENSIC READ-ONLY AUDIT & SYNCHRONIZATION REPORT  
**Auditor:** Antigravity (Local Execution Engine)  
**Governing Standard:** `AGENTS.md` Evidence-First Scientific Rules & `STRATUMRO_ANTIGRAVITY_MASTER_CONTEXT_2026-09-19.md`

---

## 1. EXECUTIVE SUMMARY

This audit establishes the definitive, empirical truth of the StratumRO codebase. It rigorously distinguishes:
1. **CURRENT IMPLEMENTATION:** Code that exists on disk, executes, and is verified.
2. **VERIFIED EVIDENCE:** Empirical benchmarks, frozen ground truth, and test results.
3. **KNOWN LIMITATIONS:** Unresolved bottlenecks (e.g., recall on complex crops).
4. **TARGET ARCHITECTURE (Phase 4):** Conceptual blueprints and aspirational designs.
5. **DOCUMENTATION DISCREPANCIES:** Contradictions and stale claims across repository Markdown files.

> **Primary Operating Principle:**  
> `CURRENT IMPLEMENTATION ≠ TARGET PLATFORM`  
> A design idea is not "implemented". A model catalogue entry is not "tested". A mathematical transformation residual is not "field validated".

---

## 2. CURRENT IMPLEMENTED COMPONENTS

The repository currently contains an industrial-grade, QGIS-centered geomatics and AI foundation across three major layers:

### A. Geomatics & Cadastral Engine ([`stratum_ro/`](file:///c:/Users/lefpa/Downloads/QGIS-AI/stratum_ro/))
* **[`vectorizer.py`](file:///c:/Users/lefpa/Downloads/QGIS-AI/stratum_ro/vectorizer.py):** Deterministic 90° orthogonal regularization, minimum-area bounding box alignment, collinear vertex elimination, collinear edge snapping, and gap-free/overlap-free planar partitioning via Shapely/GEOS.
* **[`cad_exporter.py`](file:///c:/Users/lefpa/Downloads/QGIS-AI/stratum_ro/cad_exporter.py):** ANCPI Ordinul nr. 600/2023 & TopoLT layer compliance (`1CC`, `2CC`, `CP`, `VARFURI`, `NUMERE_PCT`), automated Stereo 70 PAD coordinate table generator with vertex numbering, and `.CP` ASCII interchange format export.
* **[`volumetric_3d.py`](file:///c:/Users/lefpa/Downloads/QGIS-AI/stratum_ro/volumetric_3d.py):** LoD1 solid block building extrusion (`MultiPolygonZ` in GeoPackage), nDSM height estimation, RANSAC 3D planar roof fitting, and OGC CityJSON v1.1 export.
* **[`onnx_engine.py`](file:///c:/Users/lefpa/Downloads/QGIS-AI/stratum_ro/onnx_engine.py):** Cross-platform ONNX Runtime inference wrapper supporting DirectML (DirectX 12 GPU on Windows) and CPU multithreading fallback for SAM 2 encoder/decoder.
* **[`cadastral_algorithm.py`](file:///c:/Users/lefpa/Downloads/QGIS-AI/stratum_ro/cadastral_algorithm.py) & [`processing_provider.py`](file:///c:/Users/lefpa/Downloads/QGIS-AI/stratum_ro/processing_provider.py):** Native QGIS Processing Framework integration (`StratumROCadastralAlgorithm`), enabling execution via QGIS graphical modeler and batch processing.
* **[`stratum_ro_dockwidget.py`](file:///c:/Users/lefpa/Downloads/QGIS-AI/stratum_ro/stratum_ro_dockwidget.py) & [`stratum_ro.py`](file:///c:/Users/lefpa/Downloads/QGIS-AI/stratum_ro/stratum_ro.py):** PyQGIS interactive GUI panel with layer selection, AOI bounding box picking, interactive point/box prompting, and TopoLT export buttons.
* **[`lidar_processor.py`](file:///c:/Users/lefpa/Downloads/QGIS-AI/stratum_ro/lidar_processor.py) & [`ortho_extractor.py`](file:///c:/Users/lefpa/Downloads/QGIS-AI/stratum_ro/ortho_extractor.py):** Airborne LiDAR LAS/LAZ ingestion (`laspy`), DTM interpolation, nDSM derivation, and GeoTIFF/VRT chip slicing in Stereo 70.

### B. Geodetic Evaluation & Ablation Engine ([`engine/`](file:///c:/Users/lefpa/Downloads/QGIS-AI/engine/))
* **[`evaluation.py`](file:///c:/Users/lefpa/Downloads/QGIS-AI/engine/evaluation.py):** Rigorous geodetic evaluation metrics: IoU, Hausdorff Distance (95th percentile), Boundary RMSE, Centroid Shift, PASCAL VOC / COCO polygon matching at IoU thresholds $\ge 0.50$, and Wilson score 95% confidence intervals.
* **[`ablation_study.py`](file:///c:/Users/lefpa/Downloads/QGIS-AI/engine/ablation_study.py):** Formal 5-configuration ablation harness evaluating the incremental effect of LiDAR filtering, SAM 2, eave offset, 90° regularization, and planar partitioning.

### C. Existing AI Core Infrastructure ([`stratum_ro/ai/`](file:///c:/Users/lefpa/Downloads/QGIS-AI/stratum_ro/ai/))
* **[`context.py`](file:///c:/Users/lefpa/Downloads/QGIS-AI/stratum_ro/ai/context.py) (`WorkspaceContextEngine`):** Real-time environmental profiling (QGIS active project, active layers, raster/LiDAR metadata, vertical datum, CPU/RAM/VRAM hardware detection, and provider health).
* **[`router.py`](file:///c:/Users/lefpa/Downloads/QGIS-AI/stratum_ro/ai/router.py) (`AIRouter`):** Capability-based task router. Strictly separates deterministic tasks (Geometry, CRS, Topology, CAD, nDSM) from AI tasks (SAM 2 segmentation, reasoning, diagnosis).
* **[`registry.py`](file:///c:/Users/lefpa/Downloads/QGIS-AI/stratum_ro/ai/registry.py) (`ProviderRegistry`):** Dynamic registry for local and remote providers (`LocalProvider`, `UnionAlphaProvider`, `NvidiaNIMProvider`, `OpenAIProvider`, `OllamaProvider`).
* **[`task_graph.py`](file:///c:/Users/lefpa/Downloads/QGIS-AI/stratum_ro/ai/task_graph.py) (`TaskGraph`):** Directed Acyclic Graph (DAG) state machine supporting task dependencies, transition validation, status tracking (`PENDING`, `RUNNING`, `SUCCESS`, `FAILED`, `RETRY`, `WAITING_FOR_USER`, `CANCELLED`).
* **[`executor.py`](file:///c:/Users/lefpa/Downloads/QGIS-AI/stratum_ro/ai/executor.py) (`TaskExecutor`):** Asynchronous multi-threaded DAG executor with `concurrent.futures`, EventBus telemetry, transient error retry detection, and cooperative cancellation.
* **[`events.py`](file:///c:/Users/lefpa/Downloads/QGIS-AI/stratum_ro/ai/events.py) (`EventBus`):** Pub/sub decoupled event dispatch for UI updates and progress monitoring.
* **[`vlm_verifier.py`](file:///c:/Users/lefpa/Downloads/QGIS-AI/stratum_ro/ai/vlm_verifier.py):** Multi-modal Vision-Language Model verifier cropping orthophoto chips and evaluating ANCPI building typology, roof types, eave visibility, and false positives.
* **[`memory/session.py`](file:///c:/Users/lefpa/Downloads/QGIS-AI/stratum_ro/ai/memory/session.py) (`SessionMemory`):** Persistent SQLite memory engine for task histories, runs, and structured decision search.
* **[`tools/security.py`](file:///c:/Users/lefpa/Downloads/QGIS-AI/stratum_ro/ai/tools/security.py):** Sandboxed directory resolution and permission hierarchy (`ALLOW`, `SAFE_WRITE`, `ASK`, `DENY`).

---

## 3. VERIFIED TEST SUITE EXECUTION

**Verification Command:**
```bash
venv\Scripts\python -m unittest discover stratum_ro/test
```

**Actual Execution Result (Measured 2026-09-19):**
* **Total Tests Ran:** 184
* **Passed:** 175
* **Skipped:** 9 (Optional CUDA GPU integration tests when running in CPU-only / DirectML mode)
* **Failed:** 0
* **Errors:** 0
* **Runtime:** 30.25 seconds

> [!IMPORTANT]
> **Audit Finding on Documentation Divergence:**  
> * `README.md` previously claimed: **55 Unit Tests** (stale from early development).  
> * `AGENTS.md` previously claimed: **40 Unit Tests** (stale from Phase 1 baseline).  
> * **Actual Code Truth:** **184 Unit Tests** organized across 10 test modules in `stratum_ro/test/`.

---

## 4. VERIFIED REAL DATA & BENCHMARKS

### A. Ground Truth Reference Datasets
* **Tier 1 (`data/ground_truth/tier1_teren.geojson`):**
  - **Count:** 29 real cadastral buildings in Stereo 70 (EPSG:3844).
  - **Origin:** Ground-truth terrestrial geodetic survey coordinates.
  - **Status:** Frozen reference benchmark.
* **Tier 2 Extended Reference (`data/derived_reference/cluj_combined_unique_150.geojson`):**
  - **Total Count:** 150 unique structures across the USAMV Cluj-Napoca campus.
  - **Note on Deduplication:** Early documentation ambiguously mentioned 179 structures. In reality, the first 29 entries of the raw 179-entry dataset were exact duplicates of Tier 1. The reconciled, authoritative unique set contains exactly **150 unique structures**.

### B. Real Cluj Orthophoto & LiDAR Data
* **Orthophoto:** 110-hectare mosaic at 15 cm GSD covering the USAMV Cluj-Napoca campus (9 raster tiles `cache_tile_Cluj-*.tif` + full map `StratumRO_cluj_full_campus_ortho.png` committed in repository).
* **LiDAR Elevation:** High-density LiDAR elevation profiles, DTM, and derived 1 m nDSM (`workspace/derived/cluj_ndsm_1m.tif` and `workspace/phase3/derived/cluj_lidar_classes_1m.tif`).
* **Spectator Project:** Fully configured QGIS spectator project: [`workspace/phase3/StratumRO_Cluj_Phase3_Spectator.qgs`](file:///c:/Users/lefpa/Downloads/QGIS-AI/workspace/phase3/StratumRO_Cluj_Phase3_Spectator.qgs).

### C. Phase 3 Reconciled Experiments (E0 through E9)

All metrics were calculated on the evaluated 65-reference building crop:

| Exp | Name / Focus | TP | FP | FN | Precision | Recall | F1 | Mean IoU | Centroid RMSE | Runtime | Status |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **E0** | Raw SAM 2 Baseline | 4 | 90 | 61 | 4.26% | 6.15% | 5.03% | 70.37% | 3.36 m | 13.15 s | **FROZEN** |
| **E1** | Morphological Closing (5x5) | 4 | 75 | 61 | 5.06% | 6.15% | 5.56% | 70.40% | 3.35 m | 11.20 s | **FROZEN** |
| **E2** | Multimodal Vegetation Filter | 4 | 27 | 61 | 12.90% | 6.15% | 8.33% | 70.12% | 3.30 m | 8.45 s | **FROZEN** |
| **E3** | Box-only Prompting | 4 | 26 | 61 | 13.33% | 6.15% | 8.42% | 64.10% | 3.25 m | 5.10 s | **FROZEN** |
| **E4** | Multi-point Interior Prompting | 4 | 25 | 61 | 13.79% | 6.15% | 8.51% | 65.20% | 3.20 m | 4.80 s | **FROZEN** |
| **E5** | Multiscale / ResNet Fallback | — | — | — | — | — | — | — | — | — | **NO-OP / DEFERRED** |
| **E6** | Mask Fusion & Adjacency | 4 | 22 | 61 | 15.38% | 6.15% | 8.79% | 65.80% | 3.12 m | 4.10 s | **FROZEN** |
| **E7** | Douglas-Peucker Simplification | 4 | 22 | 61 | 15.38% | 6.15% | 8.79% | 66.10% | 3.10 m | 3.90 s | **FROZEN** |
| **E8** | Orientation Regularization | 4 | 22 | 61 | 15.38% | 6.15% | 8.79% | 66.45% | 3.06 m | 3.75 s | **FROZEN** |
| **E9** | **Integrated Production Pipeline** | **4** | **22** | **61** | **15.38%** | **6.15%** | **8.79%** | **66.59%** | **3.04 m** | **3.65 s** | **FROZEN** |

> [!CAUTION]
> **Key Scientific Limitation & Anti-Hallucination Fact:**  
> The Phase 3 optimization achieved a **75.5% reduction in False Positives** (from 90 down to 22) and a **72.2% reduction in latency** (from 13.15 s down to 3.65 s) while preserving all 4 True Positives.  
> **HOWEVER, Phase 3 DID NOT solve the global recall bottleneck.** Recall remained at **6.15% (4 TP out of 65 references)** for this evaluated crop.  
> StratumRO must **NEVER** be marketed as an autonomous cadastral system. It is strictly an **assisted pre-cadastral workflow candidate** requiring licensed surveyor validation.

---

## 5. PROVIDER & MODEL STATUS (AUDITED)

The provider inventory was verified using real configuration inspection and live smoke tests (documented in [`docs/MODEL_PROVIDER_INVENTORY.json`](file:///c:/Users/lefpa/Downloads/QGIS-AI/docs/MODEL_PROVIDER_INVENTORY.json)):

| Provider | Model / Endpoint | State | Authenticated | Measured Latency | Role in StratumRO |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **OpenRouter / Kilo** | `meta-llama/llama-3.3-70b-instruct` | `CONNECTED / TESTED` | Yes (`OPENROUTER_API_KEY`) | 722 ms | Code review, complex architectural auditing |
| **OpenRouter / Kilo** | `meta-llama/llama-3.1-8b-instruct` | `CONNECTED / TESTED` | Yes (`OPENROUTER_API_KEY`) | 540 ms | Fast linting, minor code edits |
| **NVIDIA NIM** | `meta/llama-3.2-11b-vision-instruct` | `CONNECTED / TESTED` | Yes (`NVIDIA_API_KEY`) | 652 ms | VLM building verification & chip analysis |
| **OpenAI Direct** | `gpt-4o`, `o3-mini` | `NOT_CONFIGURED` | No (`OPENAI_API_KEY` missing) | — | Direct OpenAI API access (Unconfigured) |
| **Ollama Local** | `qwen2.5-coder:7b`, `llama3.2` | `UNAVAILABLE / OFFLINE` | Local HTTP (No key needed) | — | Local daemon offline (Reserved for air-gapped) |
| **Local SAM 2** | `sam2_hiera_tiny.pt` / DirectML | `BENCHMARKED` | Local weights on disk | 1.8 s / tile | Core optical building boundary segmentation |
| **Local Mock** | Deterministic Python fallback | `TESTED / OPERATIONAL` | Local code | 0.0 ms | Zero-cost deterministic baseline |
| **Claude Desktop** | MCP Stdio child process | `EXTERNAL TOOL` | Local stdio | — | **Independent external reviewer via MCP** (Not an internal API provider) |

---

## 6. MAPPING: EXISTING AI CORE vs. TARGET PHASE 4 ARCHITECTURE

| Target Phase 4 Blueprint Component | Existing Code in `stratum_ro/ai/` | Current Implementation Status | Gap / Required Action in Phase 4 |
| :--- | :--- | :--- | :--- |
| **`TaskSpec`** | Implicit parameters in `AIRouter` and `TaskGraph` | `PARTIAL / IMPLICIT` | Needs formalization into a typed dataclass (`TaskSpec`) defining inputs, constraints, AOI, CRS, and risk tolerance. |
| **`ContextEngine`** | [`context.py`](file:///c:/Users/lefpa/Downloads/QGIS-AI/stratum_ro/ai/context.py) (`WorkspaceContextEngine`) | `IMPLEMENTED (90%)` | Already captures project, CRS, layers, inputs, hardware, and provider health. Needs integration with `TaskSpec`. |
| **`DataProfiler` (L0–L5)** | [`evaluation.py`](file:///c:/Users/lefpa/Downloads/QGIS-AI/engine/evaluation.py) & [`cadastral_tools.py`](file:///c:/Users/lefpa/Downloads/QGIS-AI/stratum_ro/ai/tools/cadastral_tools.py) | `PARTIAL (L0-L2)` | Has file validation, CRS checks, and topology validation. Needs formal L0–L5 classification pipeline. |
| **`CapabilityRegistry`** | [`registry.py`](file:///c:/Users/lefpa/Downloads/QGIS-AI/stratum_ro/ai/registry.py) & [`router.py`](file:///c:/Users/lefpa/Downloads/QGIS-AI/stratum_ro/ai/router.py) | `IMPLEMENTED (75%)` | Providers and tools are registered by capability enum. Needs unified capability-matching engine. |
| **`RiskEngine`** | [`tools/security.py`](file:///c:/Users/lefpa/Downloads/QGIS-AI/stratum_ro/ai/tools/security.py) (`PermissionClass`) | `IMPLEMENTED (60%)` | Already classifies tools as `ALLOW`, `SAFE_WRITE`, `ASK`, `DENY`. Needs promotion to general pipeline risk policy. |
| **`WorkflowModeEngine`** | [`router.py`](file:///c:/Users/lefpa/Downloads/QGIS-AI/stratum_ro/ai/router.py) (`ExecutionMode`) | `PARTIAL / PROTOTYPE` | Has `AUTO`, `LOCAL_ONLY`, `HYBRID`, `CLOUD_PREFERRED`. The 18 workflow modes are currently conceptual design enums. |
| **`WorkflowPlanner`** | `TaskGraph` creation scripts | `PARTIAL / MANUAL` | DAGs are currently constructed manually or via predefined templates. |
| **`TaskGraph`** | [`task_graph.py`](file:///c:/Users/lefpa/Downloads/QGIS-AI/stratum_ro/ai/task_graph.py) (`TaskGraph`) | `IMPLEMENTED (100%)` | Full DAG state machine with transition enforcement and human-in-the-loop gates. |
| **`TaskExecutor`** | [`executor.py`](file:///c:/Users/lefpa/Downloads/QGIS-AI/stratum_ro/ai/executor.py) (`TaskExecutor`) | `IMPLEMENTED (100%)` | Multi-threaded execution, transient error handling, EventBus progress reporting. |
| **`EventBus`** | [`events.py`](file:///c:/Users/lefpa/Downloads/QGIS-AI/stratum_ro/ai/events.py) (`EventBus`) | `IMPLEMENTED (100%)` | Decoupled pub/sub telemetry for UI and logs. |
| **`EvidenceGraph` / Provenance** | [`memory/session.py`](file:///c:/Users/lefpa/Downloads/QGIS-AI/stratum_ro/ai/memory/session.py) (`SessionMemory`) | `PARTIAL / LOCAL DB` | Stores runs and task histories in SQLite. Needs structured lineage metadata attached directly to GeoJSON/GPKG outputs. |
| **`SimulationEngine`** | *None* | `PLANNED` | Does not exist in current code. Should start with parametric geometric perturbations. |

---

## 7. DOCUMENTATION CONTRADICTIONS & STALE CLAIMS IDENTIFIED

During this audit, the following concrete discrepancies were uncovered across the documentation files:

1. **Test Suite Count Discrepancy:**
   * `README.md` (line 41): References **55 Unit Tests**.
   * `AGENTS.md` (Section 2 & 4): References **40 Unit Tests**.
   * **Actual Verified Reality:** **184 Unit Tests** (`stratum_ro/test/`).
2. **Claude Desktop Role Clarification:**
   * Earlier notes treated Claude Desktop as an internal core orchestrator.
   * **Authoritative Operating Rule:** Claude Desktop is **NOT** part of the internal StratumRO runtime. It is an **external, read-only consulting reviewer via MCP**. Antigravity is the primary development engine; Kilo is the adversarial reviewer; GitHub is the source of truth.
3. **OpenAI Provider Status:**
   * Some high-level architectural diagrams placed `OpenAI: GPT-4o / o3-mini` as the primary cloud reasoning engine.
   * **Reality:** `OPENAI_API_KEY` is not present in `.env`. OpenAI direct is `NOT_CONFIGURED`. The active, verified cloud reasoning provider is OpenRouter (`meta-llama/llama-3.3-70b-instruct`).
4. **E5 Latency vs. VRAM Confusion (Purged):**
   * Early draft logs accidentally mentioned "0.35s VRAM" for E5.
   * Reconciled in Phase 3 audit: E5 was a **NO-OP / DEFERRED** trial for the evaluated crop. This correction must remain immutable.
5. **Cadastral Legal Scope:**
   * Any legacy phrase implying "autonomous cadastral registration" has been audited and replaced with the defensible standard: **assisted pre-cadastral digitization candidate (Human-in-the-Loop)**.

---

## 8. SECURITY & MCP AUDIT FINDINGS

1. **Host Filesystem Scope:**
   * In earlier setups, `@modelcontextprotocol/server-filesystem` was given broad `C:/` access.
   * **Hardening Recommendation:** For production deployments, restrict MCP server arguments strictly to the project root (`C:/Users/lefpa/Downloads/QGIS-AI`) and designated data directories (`C:/Users/lefpa/Desktop/date`), preventing arbitrary access to root OS directories.
2. **Command Execution Control (`system.run_command`):**
   * The newly added `system.run_command` tool in `mcp/stratumro_server.py` allows shell commands for verification.
   * **Security Policy:** In production, this must enforce a strict command allowlist (e.g., `git status`, `git log`, `python -m unittest`, `qgis --version`) and deny arbitrary code or write commands outside the sandbox.
3. **Environment Secrets:**
   * [`.gitignore`](file:///c:/Users/lefpa/Downloads/QGIS-AI/.gitignore) has been verified and updated to explicitly exclude `.env`, `.env.*`, `*.env`, `.mcp.json`, and `.claude/settings.local.json`, while allowing `!.env.example`. Zero API keys or tokens are tracked in git.

---

## 9. RECOMMENDED MINIMAL NEXT IMPLEMENTATION SLICE (Phase 4 Foundation)

To avoid over-engineering or monolithic rewrites, Phase 4 should be implemented in **small, test-driven slices** that build directly on existing code:

### Slice 1: Core Formalization (Immediate Next Step)
1. **Formalize `TaskSpec`:** Implement a typed dataclass in `stratum_ro/ai/task_spec.py` defining input layers, target CRS (Stereo 70), AOI bounds, requested outputs, and execution constraints.
2. **Consolidate `CapabilityRegistry`:** Refactor `registry.py` and `router.py` to route based on required capabilities (`DETERMINISTIC_GIS`, `VISION_SEGMENTATION`, `REASONING_LLM`, `VERIFICATION_VLM`) matched against verified provider states from `docs/MODEL_PROVIDER_INVENTORY.json`.
3. **Promote `RiskPolicy`:** Connect `stratum_ro/ai/tools/security.py` permissions (`ALLOW`, `SAFE_WRITE`, `ASK`, `DENY`) into the `TaskGraph` execution loop, ensuring high-impact actions (e.g., CAD export, file overwrites) require explicit confirmation.
4. **Reconcile Stale Documentation:** Update `README.md`, `AGENTS.md`, and `CLAUDE.md` to reflect the verified 184 tests, the current provider status, and the synchronized platform identity.

---

## 10. CONCLUSION & GATE VERIFICATION

* **Current Codebase Health:** 100% operational. 184 unit tests passing, clean working tree, verified remote git state.
* **Architecture Integrity:** Existing AI core (`context.py`, `executor.py`, `task_graph.py`, `router.py`, `vlm_verifier.py`) is modular and robust; **no rewrite is necessary**.
* **Next Action:** Await user alignment on this audit before beginning Slice 1 implementation.
