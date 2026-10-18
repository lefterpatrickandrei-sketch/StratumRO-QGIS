# STRATUMRO — PHASE 4.2: CHANGE AUDIT, OWNERSHIP VERIFICATION & SAFE DOMAIN CONSOLIDATION REPORT

**Authoritative System Audit, Evidence-First Verification, and Pre-Consolidation Specification**  
*Document Version: 1.0.0 — Evaluated under Master Reorientation Governance*  
*Timestamp: 2026-09-20 | Git Commit HEAD: `c9768641acb0bef0806593c84f549acba5960703` | Branch: `main`*

---

## 1. Executive Summary

Phase 4.2 executes a controlled, read-only system audit of all repository modifications introduced in early Phase 4. Following the **Master Reorientation Directive**, this audit verifies the physical state of the codebase, establishes true architectural ownership for each subsystem, compares duplicate implementations down to the byte and AST level, assesses provider call graphs, and drafts a zero-regression domain consolidation roadmap.

### Key Audit Findings
1. **Repository & Test Stability:** Full unit test suite executed cleanly: **247 tests run: 238 passed, 9 skipped, 0 failed** in 39.025s (exit code 0). Golden baseline freeze passed with 100% precision (**5 tests run, 5 passed** in 0.016s).
2. **Duplicate Invariant:** 8 of the 9 candidate domain files in `stratum_ro/domain/` are **exact byte-for-byte duplicates** of mature modules at the repository root with matching SHA-256 hashes. 1 file (`product.py`) is a near-duplicate differing solely by 2 relative import lines.
3. **Consumer Decoupling:** In the active production tree, **0 files** import from `stratum_ro.domain`. All active consumers (QGIS plugin, Processing algorithm, batch runners, unit tests) continue importing from the root modules.
4. **Provider Demarcation:** Coding LLMs (Anthropic Claude 3.5/3.7, OpenAI GPT-4o, OpenRouter Union Alpha) are classified strictly as **DEV SDK ONLY**. SAM2 (ONNX DirectML) is classified as **PRODUCT RUNTIME CV ENGINE**. Ollama is **PERMANENTLY EXCLUDED (§13, §80)**.

---

## 2. Git State

- **Branch:** `main`
- **Commit HEAD:** `c9768641acb0bef0806593c84f549acba5960703`
- **Working Tree Changes (`git status --short`):**
  - Tracked modifications:
    - `M scripts/validate_project.py` (+2 lines: Anthropic provider health check)
    - `M stratum_ro/ai/providers/__init__.py` (+2 lines: export `AnthropicProvider`)
    - `M stratum_ro/test/test_ai_providers.py` (+42 lines: unit tests for `AnthropicProvider`)
  - Untracked artifacts:
    - Domain packages in `stratum_ro/domain/` (untracked candidate files)
    - Architecture specifications (`STRATUMRO_PRODUCT_ARCHITECTURE.md`, `STRATUMRO_DEV_SDK_ARCHITECTURE.md`, `STRATUMRO_PRODUCT_VS_DEV_SDK_BOUNDARY.md`)
    - Reports and matrices in `workspace/phase4/` and `workspace/architecture/`
    - SDK script `scripts/run_agent_with_custom_api.py`
    - Local provider `stratum_ro/ai/providers/anthropic_provider.py`
- **Worktree Integrity:** Canonical branches (`geode-barber`, `lowly-vanilla`, `mlops_qgis_pipeline_integration`) remain unmerged and isolated.

---

## 3. Phase 4 Change Inventory

Detailed inventory documented in [`workspace/phase4/phase42_change_inventory.md`](file:///c:/Users/lefpa/Downloads/QGIS-AI/workspace/phase4/phase42_change_inventory.md):
- Total candidate domain code files created: 10 files
- Total documentation/README files created: 5 files
- Total packages initialized: 5 domain subpackages + 1 domain root
- Total duplicate files identified: 8 exact byte duplicates + 1 near duplicate
- Total partial stubs: 1 file (`topography/adapter.py`)

---

## 4. `product.py` Diff Analysis

A mandatory detailed audit was conducted on `stratum_ro/domain/cadastre_ro/product.py` versus root `stratum_ro/cadastral_product.py`:

```diff
--- stratum_ro/cadastral_product.py
+++ stratum_ro/domain/cadastre_ro/product.py
@@ -20,8 +20,8 @@
 from shapely.ops import unary_union
 import geopandas as gpd
 
-from .vectorizer import CadastralVectorizer
-from .cad_exporter import CadastralDxfExporter
+from stratum_ro.vectorizer import CadastralVectorizer
+from .exporter import CadastralDxfExporter
```

### Mandatory Question Responses (§5, §25):
1. **Ce linii s-au modificat?** Liniile 23-24 (căile de import).
2. **Sunt modificări de import?** DA. Exclusiv modificări de import.
3. **Sunt modificări de logică?** NU. Nicio linie de logică matematică sau cadastrală nu a fost modificată.
4. **Schimbă behavior?** NU. Algoritmul `CadastralProductGenerator` rulează identic.
5. **De ce au fost făcute?** Pentru a permite importarea lui `CadastralDxfExporter` din modulul local `exporter.py` (`from .exporter ...`) și `CadastralVectorizer` din pachetul rădăcină.
6. **Sunt necesare?** Erau necesare doar pentru a face fișierul importabil din noua sa locație.
7. **Sunt doar pentru packaging?** DA. Pur cosmetice de împachetare.
8. **Pot produce circular imports?** NU. Nu există ciclu de import între `CadastralProductGenerator`, `CadastralVectorizer` și `CadastralDxfExporter`.
9. **Pot afecta legacy API?** Nu afectează legacy API dacă `stratum_ro/cadastral_product.py` este păstrat ca modul canonic/forwarder.
10. **Semantic Check:** Does it change output (NO), imports (YES, relative only), API (NO), domain semantics (NO), validation (NO), geometry (NO), serialization (NO).
- **Audit Verdict:** `product.py` este aprobat ca fiind non-regresiv, dar reprezintă un near-duplicate care va fi consolidat în Phase 4.3.

---

## 5. Domain Directory Clarification (§6)

- `stratum_ro/domain/` (singular): **EXISTS ON DISK** (contains 5 domain subpackages).
- `stratum_ro/domains/` (plural): **DOES NOT EXIST ON DISK** (verified: `os.path.exists` is False, 0 files).
- **Rule Enforcement:** We strictly preserve the singular `stratum_ro/domain/` convention. We will NOT create `domains/` or allow parallel naming schemes.

---

## 6. Duplicate Implementation Analysis

Byte-for-byte and cryptographic SHA-256 analysis of duplicate candidates:

| Root File | Domain Candidate File | Root Size | Domain Size | SHA-256 Root | SHA-256 Domain | Classification |
| :--- | :--- | :---: | :---: | :--- | :--- | :--- |
| `cad_exporter.py` | `domain/cadastre_ro/exporter.py` | 19,485 B | 19,485 B | `371ce3fcfd58...` | `371ce3fcfd58...` | **IDENTICAL** |
| `cadastral_product.py`| `domain/cadastre_ro/product.py` | 7,461 B | 7,467 B | `eb7e1a7ec0ad...` | `bff3c422bb7a...` | **NEAR IDENTICAL** |
| `volumetric_3d.py` | `domain/city_3d/builder.py` | 9,350 B | 9,350 B | `3a9a4e5e5de5...` | `3a9a4e5e5de5...` | **IDENTICAL** |
| `lidar_processor.py` | `domain/lidar/processor.py` | 9,824 B | 9,824 B | `fd285f281c92...` | `fd285f281c92...` | **IDENTICAL** |
| `lidar_quality_gate.py`| `domain/lidar/quality_gate.py` | 10,271 B | 10,271 B | `4a210f5cfe7b...` | `4a210f5cfe7b...` | **IDENTICAL** |
| `candidate_generator.py`| `domain/vision/candidates.py` | 5,714 B | 5,714 B | `75debc95ebab...` | `75debc95ebab...` | **IDENTICAL** |
| `onnx_engine.py` | `domain/vision/engine.py` | 8,972 B | 8,972 B | `de0218022e53...` | `de0218022e53...` | **IDENTICAL** |
| `mask_fusion.py` | `domain/vision/fusion.py` | 5,866 B | 5,866 B | `f5cf45721a42...` | `f5cf45721a42...` | **IDENTICAL** |
| `vegetation_filter.py` | `domain/vision/vegetation.py` | 7,160 B | 7,160 B | `d0946d1e2465...` | `d0946d1e2465...` | **IDENTICAL** |

---

## 7. Cadastre Ownership

- **Subsystem:** Cadastre RO (ANCPI Ordinul 600/2023, TopoLT DXF, `.CP` exchange files, PAD tables).
- **Public API:** `CadastralDxfExporter`, `CadastralProductGenerator`.
- **Consumers:** `stratum_ro/cadastral_algorithm.py`, `stratum_ro/stratum_ro_dockwidget.py`, `stratum_ro/ai/tools/cadastral_tools.py`, `run_hybrid_full_aoi.py`.
- **Unit Tests:** `test_cad_exporter.py` (2 tests), `test_cp_export_real_coords.py` (3 tests).
- **True Owner:** **STRATUMRO PRODUCT (Domain: `cadastre_ro`)**.
- **Consolidation Action:** In Phase 4.3, `stratum_ro/domain/cadastre_ro/` becomes canonical. Root files become forwarders.

---

## 8. Topography Ownership

- **Subsystem:** Topography (Slope & Aspect calculation).
- **Current File:** `stratum_ro/domain/topography/adapter.py` (40 lines, Horn 3x3 finite-difference).
- **Maturity:** **PARTIAL (§10, §11)**.
- **Consumers:** Zero active consumers in pipeline.
- **True Owner:** **STRATUMRO PRODUCT (Domain: `topography`)**.
- **Consolidation Action:** Retain as partial adapter. **DO NOT EXPAND ARTIFICIALLY** per *Roadmap $\neq$ Code Directory* rule.

---

## 9. LiDAR Ownership

- **Subsystem:** Airborne LiDAR point cloud processing & 3D Quality Gate.
- **Public API:** `LidarProcessor`, `LidarQualityGate`.
- **Consumers:** `stratum_ro/stratum_ro_dockwidget.py`, `stratum_ro/ai/tools/lidar_tools.py`, `stratum_ro/vectorizer.py`, `test_geometric_reconstruction_v2.py`.
- **True Owner:** **STRATUMRO PRODUCT (Domain: `lidar`)**.
- **Consolidation Action:** In Phase 4.3, `stratum_ro/domain/lidar/` becomes canonical. Root files become forwarders.

---

## 10. Vision Ownership

- **Subsystem:** Computer Vision Building Segmentation & Mask Fusion.
- **Public API:** `CandidateGenerator`, `ONNXSegmentationEngine`, `MaskFusionEngine`, `MultimodalVegetationFilter`.
- **Consumers:** `stratum_ro/stratum_ro_dockwidget.py`, `stratum_ro/ai/tools/segmentation_tools.py`, `test_onnx_engine.py`, `test_phase3_modules.py`.
- **True Owner:** **STRATUMRO PRODUCT (Domain: `vision`)**.
- **Consolidation Action:** In Phase 4.3, `stratum_ro/domain/vision/` becomes canonical. Root files become forwarders.

---

## 11. City 3D Ownership

- **Subsystem:** 3D LoD1 Solid Shell Extrusion & CityJSON v1.1 Export.
- **Public API:** `Volumetric3DBuilder`.
- **Consumers:** `stratum_ro/ai/tools/vector_tools.py`, `stratum_ro/pug_product.py`, `test_volumetric_3d.py`.
- **True Owner:** **STRATUMRO PRODUCT (Domain: `city_3d`)**.
- **Consolidation Action:** In Phase 4.3, `stratum_ro/domain/city_3d/builder.py` becomes canonical. Root file becomes forwarder.

---

## 12. Provider Ownership

Full call-graph analysis documented in [`workspace/phase4/provider_ownership_matrix.md`](file:///c:/Users/lefpa/Downloads/QGIS-AI/workspace/phase4/provider_ownership_matrix.md):
- `AnthropicProvider`: **DEV SDK ONLY** (consumed only by test suite and SDK validation).
- `OpenAIProvider`: **DEV SDK ONLY** (consumed by registry and code review tools).
- `UnionAlphaProvider`: **DEV SDK ONLY** (consumed by `closed_loop.py` for Kilo adversarial review).
- `NvidiaNIMProvider`: **BOTH (Dual-Use)** (Dev SDK visual reviews + optional runtime VLM verification).
- `LocalProvider`: **PRODUCT RUNTIME** (deterministic air-gapped mock baseline).
- `OllamaProvider`: **PERMANENTLY EXCLUDED (§13, §80)**.

---

## 13. Model Registry Ownership

- **Development Model Registry:** Managed by Dev SDK via environment configurations (`.env`) for coding/review models.
- **Product Model Registry:** Managed by `stratum_ro/ai/registry.py` for runtime CV models and task capabilities.
- **Decision:** No second registry class created yet. Keep decoupled logically (§23).

---

## 14. SAM2 Ownership

- **Analysis:** Meta SAM 2 Hiera executed via ONNX Runtime DirectML.
- **Callers:** `stratum_ro_dockwidget.py`, `segmentation_tools.py`, `run_hybrid_full_aoi.py`.
- **Verdict:** **PRODUCT RUNTIME CV ENGINE (§14, §20)**. SAM2 is not an LLM, not a chat engine, and not a coding provider.

---

## 15. QGIS Boundary

- `stratum_ro_dockwidget.py` & `stratum_ro.py`: Product Desktop GUI clients.
- `cadastral_algorithm.py` & `processing_provider.py`: Product QGIS Processing framework integrations.
- **Dependency Flow:** QGIS Client $\longrightarrow$ Domain Packs $\longrightarrow$ Scientific Core.
- The QGIS client never imports Dev SDK or coding LLM providers.

---

## 16. SDK vs Product Classification

| Asset Category | Belonging System | Runtime Deployment Role |
| :--- | :--- | :--- |
| `stratum_ro/core/` | **Product** | Local deterministic geomatics math |
| `stratum_ro/contracts/` | **Product** | Abstraction interfaces |
| `stratum_ro/domain/` | **Product** | Specialized geomatics packs |
| `SAM2 / ONNX DirectML` | **Product** | Optical building mask segmentation |
| `data/ground_truth/` | **Product Data** | Authoritative reference datasets |
| `Cluj-USAMV` demonstrator | **Product Data** | Integrated benchmark demonstrator |
| `Anthropic / OpenAI / UnionAlpha` | **Dev SDK** | Code generation, planning, Kilo audits |
| `.gemini/`, `.kilo/` | **Dev SDK** | IDE agent configuration & memory |
| `.env` (API Keys) | **Dev SDK** | Developer secrets (git-ignored) |

---

## 17. Legacy API Analysis

Because external scripts (`run_hybrid_full_aoi.py`, `tools/run_e2e_desktop_operator.py`) and existing tests import directly from root files:
- Root files CANNOT be deleted or moved abruptly.
- Forwarders must be deployed to preserve backward compatibility during domain migration.

---

## 18. Dependency Graph

```text
QGIS Client (DockWidget / CadastralAlgorithm)
      │
      ▼
Domain Packs (cadastre_ro, city_3d, lidar, vision)
      │
      ├───────────────────────┐
      ▼                       ▼
Geospatial Core        Scientific Core
(raster, pointcloud)   (geodesy, geometry, qa_qc)
      │                       │
      └───────────┬───────────┘
                  ▼
         Deterministic GEOS/GDAL
```

---

## 19. Circular Dependency Risks

- `Domain` $\to$ `Core`: Clean DAG, no cycles.
- `cadastre_ro` $\to$ `vectorizer` $\to$ `qa_qc`: Clean DAG, no cycles.
- `city_3d` $\to$ `geometry`: Clean DAG, no cycles.
- **Risk Level:** **ZERO CYCLES DETECTED**.

---

## 20. Scientific Regression Check

- Baseline evaluation against `tier1_teren.geojson` (29 reference buildings):
  - Area calculation: Identical ($\pm 0.000\,\text{m}^2$).
  - Boundary vertices: Identical (canonical 4-vertex rectangle fitting intact).
  - TopoLT layer names: Preserved (`1CC`, `2CC`, `CP`, `VARFURI`, `NUMERE_PCT`, `TABEL_PAD`).
- **Regression Status:** **ZERO REGRESSIONS DETECTED**.

---

## 21. Golden Baseline Check

- `venv\Scripts\python -m unittest stratum_ro/test/test_phase1_golden_freeze.py`:
  - **5 tests run, 5 passed, 0 failed** in 0.016s.
- `venv\Scripts\python -m unittest discover stratum_ro/test`:
  - **247 tests run, 238 passed, 9 skipped, 0 failed** in 39.025s (exit code 0).
- **Golden Baseline Status:** **VERIFIED & FROZEN**.

---

## 22. Consolidation Plan

Actionable migration plan detailed in [`workspace/phase4/domain_consolidation_plan.md`](file:///c:/Users/lefpa/Downloads/QGIS-AI/workspace/phase4/domain_consolidation_plan.md).  
Priority sequence:
$$\mathbf{city\_3d} \longrightarrow \mathbf{cadastre\_ro} \longrightarrow \mathbf{lidar} \longrightarrow \mathbf{vision} \longrightarrow \mathbf{topography}$$

---

## 23. Deferred Decisions

1. **Dev SDK Separate Repository (§24, §73):** Deferred. Keep Dev SDK cleanly segregated logically within `StratumRO-QGIS` until domain boundaries stabilize.
2. **Topography Domain Expansion (§11, §17):** Deferred. Kept as a 40-line partial stub; no artificial feature inflation.
3. **PUG & Urbanism Domain:** Deferred. `pug_product.py` remains an experimental prototype.

---

## 24. Final Decision

All required change inventories, diff analyses, checksums, usage graphs, and decision matrices have been generated on disk without modifying source code.

```text
PHASE 4.2 STATUS:
PASS
```
