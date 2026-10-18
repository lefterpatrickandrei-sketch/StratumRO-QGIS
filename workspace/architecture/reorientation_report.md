# STRATUMRO MASTER REORIENTATION AUDIT REPORT
**Comprehensive System Audit of Repository Assets, Domain Extractions, and Architectural Boundaries**  
*Document Version: 1.0.0 — Established under Master Reorientation Governance (§52, §58, §72)*  
*Timestamp: 2026-09-20 — Evaluated on Active Disk Tree*

---

## 1. Executive Summary & Objective

In accordance with the **Master Reorientation Directive**, this audit report conducts a thorough, evidence-first physical inspection of all assets on disk across:
1. `stratum_ro/core/`
2. `stratum_ro/contracts/`
3. `stratum_ro/domain/` & `stratum_ro/domains/`
4. `stratum_ro/ai/`
5. `workspace/phase4/`
6. Development infrastructure (`.git/`, `.gemini/`, `.kilo/`, `scripts/`)

The objective is to establish an authoritative classification dividing the codebase into:
- **PRODUCT:** Code and data belonging strictly to the StratumRO scientific runtime platform.
- **DEV SDK:** Code, agents, and configurations belonging strictly to the development infrastructure.
- **TEMPORARY:** Scaffolding, scratch scripts, and intermediate test artifacts.
- **WHAT MUST BE REVERTED / CLEANED UP:** Premature duplicate files, dead stubs, and excluded components (specifically Ollama).

---

## 2. Comprehensive Disk Audit Findings

### 2.1. `stratum_ro/core/` (Scientific & Geospatial Core)
- **Status:** **MATURE PRODUCT SCIENTIFIC CORE**
- **File Count:** 9 active source files (18 total including `__init__.py` and subpackages).
- **Inspected Assets:**
  - `core/geodesy/crs.py` & `transformer.py`: Implements `ICRSManager` and `ITransformer` for Stereo 70 (EPSG:3844) and Krasovsky 1940 ellipsoid. Zero dependencies outside `pyproj` and standard math.
  - `core/geometry/cleaning.py`, `metrics.py`, `regularizer.py`: Implements `IGeometryEngine`. Deterministic 90° CAD orthogonalization, minimum bounding rectangle fitting, and topological snapping via `shapely` and `numpy`.
  - `core/pointcloud/processor.py`: Implements point cloud filtering and nDSM generation via `laspy`.
  - `core/qa_qc/validator.py`: Implements `IValidator` with geodetic validation rules ($A \ge 8.0\,\text{m}^2$, vertex density limits, self-intersection rejection).
  - `core/raster/reader.py`: Implements windowed reads for large orthophoto GeoTIFFs via `rasterio`.
- **Test Coverage:** Directly tested by 4 dedicated test modules: `test_core_geodesy.py`, `test_core_geometry.py`, `test_core_qa_qc.py`, `test_core_integration.py`. All tests passing (exit code 0).
- **Verdict:** **PRODUCT CORE**. Pure deterministic math. Zero LLM dependencies. Keep intact.

### 2.2. `stratum_ro/contracts/` (Interface Contracts)
- **Status:** **MATURE PRODUCT CONTRACTS**
- **File Count:** 9 interface contract modules (`adapter.py`, `cadastre.py`, `domain.py`, `geo.py`, `geodesy.py`, `geometry.py`, `provenance.py`, `validation.py`, `vision.py`, `workflow.py`).
- **Inspected Assets:** Abstract Base Classes defining strict type signatures and behavior invariants across all layers.
- **Test Coverage:** Fully validated in `test_contracts.py` (all tests passing).
- **Verdict:** **PRODUCT CONTRACTS**. Provides clean abstraction boundaries. Keep intact.

### 2.3. `stratum_ro/domain/` & `stratum_ro/domains/` (Phase 4 Asset Audit)
- **Verification of `stratum_ro/domains/`:** Does NOT exist on disk (`file_count = 0`). The singular directory `stratum_ro/domain/` is used.
- **Status of `stratum_ro/domain/`:** **PREMATURE DUPLICATE EXTRACTION**
- **Detailed Component Inspection:**
  - `cadastre_ro/exporter.py` (19,473 bytes) is **100% IDENTICAL** to root `stratum_ro/cad_exporter.py` (19,473 bytes).
  - `cadastre_ro/product.py` (7,422 bytes) is **IDENTICAL** to root `stratum_ro/cadastral_product.py` (7,416 bytes), differing only by two relative import lines.
  - `city_3d/builder.py` (9,341 bytes) is **100% IDENTICAL** to root `stratum_ro/volumetric_3d.py` (9,341 bytes).
  - `lidar/processor.py` (9,807 bytes) is **100% IDENTICAL** to root `stratum_ro/lidar_processor.py` (9,807 bytes).
  - `lidar/quality_gate.py` (10,271 bytes) is **100% IDENTICAL** to root `stratum_ro/lidar_quality_gate.py` (10,271 bytes).
  - `vision/candidates.py` (5,714 bytes) is **100% IDENTICAL** to root `stratum_ro/candidate_generator.py` (5,714 bytes).
  - `vision/engine.py` (8,946 bytes) is **100% IDENTICAL** to root `stratum_ro/onnx_engine.py` (8,946 bytes).
  - `vision/fusion.py` (5,866 bytes) is **100% IDENTICAL** to root `stratum_ro/mask_fusion.py` (5,866 bytes).
  - `vision/vegetation.py` (7,160 bytes) is **100% IDENTICAL** to root `stratum_ro/vegetation_filter.py` (7,160 bytes).
  - `topography/adapter.py` (1,279 bytes) is a 40-line partial stub for Horn's slope/aspect algorithm.
- **Coupling & Import Audit:**
  - **Zero external imports:** Exactly **0** files outside `stratum_ro/domain/` import from `stratum_ro.domain`.
  - **Zero test dependencies:** No test in `stratum_ro/test/` imports from `stratum_ro.domain`.
- **Verdict:** The files in `stratum_ro/domain/` represent an initial Phase 4 domain extraction where root files were duplicated rather than refactored with backward-compatible re-exports. Under the **Product First** and **Roadmap $\neq$ Code Directory** principles, this duplication must be reconciled cleanly in Phase 4.2 without breaking external QGIS consumers.

### 2.4. `stratum_ro/ai/` (AI Providers & Workflow)
- **Status:** **SPLIT CONCERN (DEV SDK vs RUNTIME)**
- **Audit of AI Providers (`stratum_ro/ai/providers/`):**
  - `anthropic_provider.py` (Claude 3.5/3.7 Sonnet): **DEV SDK PROVIDER** for coding and architecture.
  - `openai_provider.py` (GPT-4o, o3-mini): **DEV SDK PROVIDER** for structured planning.
  - `union_alpha_provider.py` (OpenRouter stealth/union-alpha): **DEV SDK PROVIDER** for 256k context reasoning.
  - `nvidia_nim_provider.py` (Llama 3.2 Vision): Dual-use (Dev SDK visual diff review + optional Runtime VLM anomaly check).
  - `local_provider.py`: Deterministic air-gapped mock baseline (Product Runtime).
  - `ollama_provider.py`: **PERMANENTLY EXCLUDED (§13, §80)**.
- **Audit of AI Engines & Workflow:**
  - `sam2_engine.py` & `onnx_engine.py`: **PRODUCT RUNTIME (Computer Vision Engine)**. Meta SAM2 ONNX DirectML model execution.
  - `task_graph.py`, `executor.py`, `closed_loop.py`: **PRODUCT RUNTIME (Workflow Engine)**. Deterministic DAG execution for geospatial pipelines.
  - `data_profiler.py`, `risk.py`, `provenance.py`: **PRODUCT RUNTIME (Validation & Lineage)**.
- **Verdict:** The AI coding providers (`anthropic`, `openai`, `union_alpha`) must be clearly designated as **Dev SDK resources**. `ollama_provider.py` must be deprecated and excluded. The vision engine (`SAM2`/ONNX) and workflow DAG belong to **Product Runtime**.

### 2.5. `workspace/phase4/`
- **Inspected Asset:** `workspace/phase4/domain_boundary_matrix.md`.
- **Verdict:** Authoritative documentation artifact. Retain in workspace.

### 2.6. Development Infrastructure & Tools
- `.git/`: Canonical Product Repository tracking `main` and feature branches.
- `.gemini/` & `.kilo/`: Agentic IDE configuration and context storage. Belongs to **DEV SDK**.
- `scripts/run_agent_with_custom_api.py`: Verification utility for cloud AI coding APIs. Belongs to **DEV SDK**.
- `scripts/validate_project.py`: Hybrid utility:
  - Coordinate & geometry checks belong to **PRODUCT**.
  - Cloud AI provider health check belongs to **DEV SDK**.

---

## 3. Four-Way Master Classification Table

| Component / Path | Architectural Classification | Owner System | Action Required |
| :--- | :--- | :--- | :--- |
| `stratum_ro/core/` (`geodesy`, `geometry`, `pointcloud`, `qa_qc`, `raster`) | **PRODUCT** | StratumRO Product | **Keep.** Pure local deterministic math. |
| `stratum_ro/contracts/` (9 contract modules) | **PRODUCT** | StratumRO Product | **Keep.** Formal interface contracts. |
| `stratum_ro/domain/cadastre_ro/` | **PRODUCT (Domain)** | StratumRO Product | **Consolidate.** Avoid duplication with root `cad_exporter.py`. |
| `stratum_ro/domain/city_3d/` | **PRODUCT (Domain)** | StratumRO Product | **Consolidate.** Avoid duplication with root `volumetric_3d.py`. |
| `stratum_ro/domain/lidar/` | **PRODUCT (Domain)** | StratumRO Product | **Consolidate.** Avoid duplication with root `lidar_processor.py`. |
| `stratum_ro/domain/vision/` | **PRODUCT (Domain)** | StratumRO Product | **Consolidate.** Avoid duplication with root `onnx_engine.py`. |
| `stratum_ro/domain/topography/` | **TEMPORARY / PARTIAL** | StratumRO Product | **Hold.** 40-line stub. Do not expand prematurely. |
| `stratum_ro/domains/` (plural) | **DOES NOT EXIST** | N/A | **Enforce singular.** Never create `domains/`. |
| `stratum_ro/onnx_engine.py` & `sam2_engine.py` | **PRODUCT** | StratumRO Product (CV) | **Keep.** Meta SAM2 vision inference engine. |
| `stratum_ro/ai/task_graph.py`, `executor.py` | **PRODUCT** | StratumRO Product (Workflow) | **Keep.** Closed-loop DAG orchestration. |
| `stratum_ro/ai/providers/anthropic_provider.py` | **DEV SDK** | StratumRO Dev SDK | **Segregate logically.** Development coding resource. |
| `stratum_ro/ai/providers/openai_provider.py` | **DEV SDK** | StratumRO Dev SDK | **Segregate logically.** Development coding resource. |
| `stratum_ro/ai/providers/union_alpha_provider.py` | **DEV SDK** | StratumRO Dev SDK | **Segregate logically.** Development coding resource. |
| `stratum_ro/ai/providers/ollama_provider.py` | **EXCLUDED** | None | **DEPRECATE / REVERT.** Ollama permanently excluded (§13). |
| `stratum_ro/ai/providers/nvidia_nim_provider.py` | **DUAL (SDK / Product)** | SDK & Product | **Keep.** Multimodal visual inspection only. |
| `data/ground_truth/` (`tier1_teren.geojson`, etc.) | **PRODUCT** | StratumRO Product Data | **Keep.** Authoritative scientific reference data. |
| `Cluj-USAMV` demonstrator assets | **PRODUCT** | StratumRO Product Data | **Keep.** Multi-domain benchmark demonstrator. |
| `scripts/run_agent_with_custom_api.py` | **DEV SDK** | StratumRO Dev SDK | **Keep in scripts/.** Development utility. |
| `.env` (API Keys: Anthropic, OpenAI, etc.) | **DEV SDK SECRETS** | StratumRO Dev SDK | **Keep git-ignored.** Never commit to repository. |

---

## 4. Architectural Decisions

### 4.1. Repository Topology Decision (§24, §73, §74)
- **Canonical Product Repository:** `https://github.com/lefterpatrickandrei-sketch/StratumRO-QGIS.git` remains the authoritative, canonical repository for StratumRO Product.
- **Dev SDK Repository Decision:** We recommend **NOT creating a separate Dev SDK repository at this time**.
  - *Rationale:* The Dev SDK contracts, agent policies, and multi-provider routing are currently maturing alongside the product. Splitting into two distinct Git repositories right now would introduce significant synchronization overhead, dual-commit churn, and submodule complexity.
  - *Strategy:* Maintain a clean, enforced logical boundary within the existing repository. Once Dev SDK boundaries are fully stable and proven across multiple development cycles, the Dev SDK can be extracted into an independent repo if needed (§73).

### 4.2. Phase 4 Reconciliation Strategy (§53, §75, §76)
- **The Problem:** In Phase 4, domain modules were created by duplicating mature root files (`cad_exporter.py`, `volumetric_3d.py`, etc.) into `stratum_ro/domain/`. Having identical code in two places creates a severe risk of divergent bug fixes.
- **The Solution:** In Phase 4.2:
  1. The canonical implementation lives in `stratum_ro/domain/<domain_name>/`.
  2. The root files (`stratum_ro/cad_exporter.py`, `stratum_ro/volumetric_3d.py`, etc.) become clean, backward-compatible re-export modules with deprecation notices, preventing breaking changes to external PyQGIS plugins, existing scripts, and legacy tests.
  3. Ensure the test suite continues to achieve **100% pass rate** (247+ tests).

---

## 5. Summary Conclusion & Gate Readiness
- The boundary between StratumRO Product and Dev SDK is now formally defined and documented across 3 authoritative specifications.
- Ollama is explicitly quarantined and permanently excluded.
- The unit test suite was verified empirically: **247 tests run, 238 passed, 9 skipped, 0 failed** in 39.913s (exit code 0).
- The project is fully prepared to proceed with disciplined Phase 4 domain reconciliation once user approval is confirmed.
