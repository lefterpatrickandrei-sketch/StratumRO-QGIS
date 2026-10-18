# STRATUMRO CURRENT PROJECT MAP

**Audit date:** 2026-09-20  
**Audit mode:** read-only repository onboarding; no product source files were changed.  
**Report path:** `workspace/hermes/STRATUMRO_CURRENT_PROJECT_MAP.md`

Evidence labels used below: **OBSERVED** = read directly from the current checkout; **VERIFIED** = executed or checked during this audit; **HISTORICAL** = stated by an existing document but not re-established by this audit; **UNKNOWN** = not established.

## Repository

- **OBSERVED:** Canonical local root is `C:\Users\lefpa\Downloads\QGIS-AI`.
- **OBSERVED:** Git remote is `https://github.com/lefterpatrickandrei-sketch/StratumRO-QGIS.git`.
- **OBSERVED:** Repository name used by the onboarding brief is `StratumRO-QGIS`.
- **VERIFIED:** The checkout is a Git repository and the resolved root matches the configured local path.
- **OBSERVED:** Top-level product and infrastructure areas include `stratum_ro/`, `engine/`, `data/`, `datasets/`, `models/`, `mcp/`, `docs/`, `reports/`, `scripts/`, `tools/`, `workspace/`, `venv/`, and QGIS project/batch files.
- **OBSERVED:** A `dev_sdk/` directory was not found at the repository root. No custom IDE or FastAPI IDE was created during this audit.

## Git

- **VERIFIED:** Current branch is `main`.
- **VERIFIED:** Current HEAD is `c976864` (`c9768641acb0bef0806593c84f549acba5960703`), matching the Phase 1 baseline document.
- **VERIFIED:** The canonical worktree is `C:/Users/lefpa/Downloads/QGIS-AI`.
- **OBSERVED:** Additional worktrees exist:
  - `C:/Users/lefpa/.gemini/antigravity/worktrees/QGIS-AI/mlops_qgis_pipeline_integration` on `mlops_qgis_pipeline_integration` at `c193e6a`.
  - `C:/Users/lefpa/Downloads/QGIS-AI/.kilo/worktrees/geode-barber` at detached `c976864`.
  - `C:/Users/lefpa/Downloads/QGIS-AI/.kilo/worktrees/lowly-vanilla` on `lowly-vanilla` at `0c840d3`.
- **VERIFIED:** The canonical worktree is not clean. Tracked modifications: `scripts/validate_project.py`, `stratum_ro/ai/providers/__init__.py`, `stratum_ro/test/test_ai_providers.py`, `stratum_ro/test/test_volumetric_3d.py`, and `stratum_ro/volumetric_3d.py`.
- **VERIFIED:** Numerous untracked onboarding/architecture reports, Phase 2–4 workspace artifacts, `stratum_ro/contracts/`, `stratum_ro/core/`, `stratum_ro/domain/`, `stratum_ro/test/test_contracts.py`, core tests, and `scripts/run_agent_with_custom_api.py` are present. These pre-existing changes were not altered.
- **RISK:** Do not reset, clean, rebase, switch branches, or remove worktrees without explicit approval.

## Architecture

- **OBSERVED:** The project is a QGIS-integrated geospatial platform with deterministic geodesy/geometry, LiDAR and raster processing, cadastral exports, 3D building generation, AI/CV assistance, MCP servers, and evaluation tooling.
- **OBSERVED:** `docs/architecture/CURRENT_ARCHITECTURE.md` describes a sensor-to-segmentation-to-vectorization-to-cadastral-output flow using LiDAR, raster/orthophoto data, SAM2, vectorization, GeoPackage/DXF/CP/CityJSON outputs.
- **OBSERVED:** The current checkout contains newer separation candidates under `stratum_ro/core/`, `stratum_ro/contracts/`, and `stratum_ro/domain/`, while legacy root modules remain present.
- **OBSERVED:** `workspace/architecture/reorientation_report.md` identifies duplicate domain extraction as the central Phase 4 reconciliation issue.
- **INFERRED:** The repository is in a transition state rather than a fully consolidated domain-pack architecture, because duplicate implementations remain on disk and the corresponding changes are uncommitted.

## Product Core

- **OBSERVED:** `stratum_ro/core/` contains pure-Python-oriented packages for `geodesy`, `geometry`, `pointcloud`, `qa_qc`, and `raster`.
- **OBSERVED:** Core modules include CRS handling, coordinate transformation, geometry cleaning/metrics/regularization, point-cloud processing, QA/QC validation, and windowed raster reading.
- **OBSERVED:** `stratum_ro/contracts/` contains contracts for adapter, cadastre, domain, geo, geodesy, geometry, provenance, validation, vision, and workflow boundaries.
- **OBSERVED:** Legacy/runtime modules remain in `stratum_ro/`, including `vectorizer.py`, `cad_exporter.py`, `cadastral_product.py`, `volumetric_3d.py`, `lidar_processor.py`, `ortho_extractor.py`, `onnx_engine.py`, `sam2_engine.py`, and QGIS plugin/Processing modules.
- **SCIENTIFIC CONSTRAINT:** Geometry, CRS transformation, measurements, topology, and cadastral coordinate handling must remain deterministic, inspectable, and testable. AI is not the scientific authority.

## Domain Packs

- **OBSERVED:** Singular `stratum_ro/domain/` exists; plural `stratum_ro/domains/` does not exist.
- **OBSERVED:** Domain packs present:
  - `cadastre_ro/` — exporter and cadastral product.
  - `city_3d/` — 3D builder.
  - `lidar/` — processor and quality gate.
  - `topography/` — partial adapter stub.
  - `vision/` — candidate generation, engine, mask fusion, and vegetation handling.
- **OBSERVED:** Existing reports identify the domain files as exact or near duplicates of legacy root modules, with no established external imports or test dependencies from the domain package at the time of those audits.
- **VERIFIED:** The current checkout still contains both the domain files and the legacy root files. No consolidation was performed in this onboarding.
- **RISK:** A future Phase 4 change must choose one canonical implementation and preserve compatibility through deliberate forwarders/re-exports, with targeted regression tests.

## QGIS

- **OBSERVED:** QGIS integration is implemented through `stratum_ro/stratum_ro.py`, `stratum_ro/stratum_ro_dockwidget.py`, `stratum_ro/processing_provider.py`, and `stratum_ro/cadastral_algorithm.py`.
- **OBSERVED:** Additional QGIS-related files include plugin metadata, UI/runtime helpers, QGIS test fixtures, QGIS project files, and launch/install batch scripts.
- **OBSERVED:** `mcp_config.json` declares a QGIS MCP server using `py -3.12 -m qgis_mcp.server`, described as a QGIS 3.40 control plane.
- **VERIFIED:** The full unit-test command ran in the local `venv`; tests emitted QGIS/MCP socket `ResourceWarning`s and an ONNX Runtime warning, but exited successfully.
- **UNKNOWN:** A live QGIS Desktop control-plane session was not started during this read-only audit.
- **BOUNDARY:** QGIS is an integration/client environment; core deterministic modules should not acquire QGIS-only imports without an explicit boundary decision.

## AI

- **OBSERVED:** `stratum_ro/ai/` contains routing, task specification/graph/execution, context, memory, risk, provenance, data profiling, tool modules, VLM verification, and provider adapters.
- **OBSERVED:** Provider implementations include NVIDIA NIM, OpenAI, Ollama, Local deterministic, Union Alpha/OpenRouter-compatible, and Anthropic adapters.
- **OBSERVED:** `stratum_ro/sam2_engine.py` and ONNX-related modules represent local computer-vision inference; these are separate from LLM reasoning.
- **HISTORICAL:** Existing project documents report prior smoke tests for OpenRouter and NVIDIA NIM, local SAM2, and a local deterministic provider. Those historical results were not re-run as part of this audit.
- **SCIENTIFIC CONSTRAINT:** LLMs may plan, classify, orchestrate, review, and explain; they must not silently invent or alter coordinates, geometry, CRS, measurements, or ground-truth labels.

## Computer Vision

- **OBSERVED:** SAM2 and ONNX components are present, with related tests and model assets under `models/`.
- **OBSERVED:** Vision domain modules include candidate generation, inference engine, mask fusion, and vegetation handling.
- **OBSERVED:** The architecture documents describe LiDAR-guided candidate generation combined with orthophoto/SAM2 segmentation and deterministic geospatial postprocessing.
- **UNKNOWN:** A fresh end-to-end SAM2 inference run and model-load benchmark were not performed during this audit.
- **CLASSIFICATION:** CV inference is an AI/CV subsystem; deterministic geometry and geospatial postprocessing remain separate responsibilities.

## LiDAR

- **OBSERVED:** LiDAR support exists in `stratum_ro/lidar_processor.py`, `stratum_ro/lidar_quality_gate.py`, `stratum_ro/core/pointcloud/`, `stratum_ro/domain/lidar/`, and related AI tools/tests.
- **OBSERVED:** The documented pipeline includes LAS/LAZ ingestion, DTM/DSM/nDSM processing, height filtering, candidate generation, and quality gates.
- **UNKNOWN:** Current production readiness, coverage of available LAZ fixtures, and a fresh LiDAR benchmark were not established during this audit.

## Orthophoto

- **OBSERVED:** `stratum_ro/ortho_extractor.py`, `stratum_ro/core/raster/reader.py`, raster tools, and architecture documents cover orthophoto/raster extraction and windowed reads.
- **OBSERVED:** The repository references GeoTIFF/VRT/rasterio workflows and orthophoto chips used by the CV pipeline.
- **UNKNOWN:** A fresh orthophoto extraction or full sensor-fusion run was not executed during this audit.

## Testing

- **VERIFIED:** Command executed:
  `venv\\Scripts\\python -m unittest discover stratum_ro/test`
- **VERIFIED:** Result: **250 tests discovered; 241 passed; 9 skipped; 0 failed; 0 errors; exit code 0; runtime 48.355 seconds.**
- **VERIFIED:** Skips were reported by the test runner; they must not be counted as passes.
- **OBSERVED:** Test files cover AI providers/router/tools/context, contracts, core geodesy/geometry/integration/QA-QC, cadastral/CAD/CP export, evaluation, geometry golden cases, MCP tools, ONNX, phase freezes, QGIS integration, resources, task specification, VLM verification, vectorization, and volumetric 3D.
- **RISK:** Existing documents contain conflicting historical counts, including 55, 193, 206, 219, and 247 tests. The current executable result is the 250-test result above and supersedes those counts for current-state reporting.
- **NOTE:** Test output included repeated unclosed-socket `ResourceWarning`s around the QGIS MCP endpoint and an ONNX Runtime graph merge warning. These did not fail the suite but merit a later cleanup/diagnostic task.

## Baseline

- **OBSERVED:** Protected baseline artifacts are under `workspace/baseline/`, including `GOLDEN_BASELINE_REPORT.md`, geometry/metrics/test/repository manifests, ground-truth manifest, and City 3D baseline data.
- **OBSERVED:** Ground-truth and derived/reference data are under `data/ground_truth/`, `data/derived_reference/`, and `data/fixtures/`.
- **HISTORICAL:** `workspace/baseline/GOLDEN_BASELINE_REPORT.md` records a Phase 1 freeze at commit `c9768641...`, including frozen hashes, reference datasets, and deterministic geometry claims.
- **VERIFIED:** The current HEAD matches the baseline document's recorded commit, but the working tree contains substantial uncommitted changes. Therefore the clean baseline commit and the current working tree must not be conflated.
- **PROTECTED:** Do not modify ground truth or golden baseline artifacts to improve metrics. Fix algorithms or explicitly approve/document a baseline change.

## Current Phase

- **VERIFIED:** Current active work is best classified as **Phase 4.2 domain-boundary/reconciliation work**, based on the current uncommitted domain-pack files and the Phase 4.2 change inventory/decision matrix.
- **HISTORICAL:** Existing documents state Phase 1, Phase 2, Phase 3, Phase 3.5, and some Phase 4.x gates as passed. Those claims are historical unless reproduced by current tests or artifacts.
- **OBSERVED:** Phase 4.2 documentation explicitly proposes canonical domain implementations plus backward-compatible root forwarders, but the current checkout still has duplicated implementations and no completed consolidation.
- **UNKNOWN:** Phase 4.3 completion cannot be accepted solely from the onboarding brief because the current disk still shows the relevant city-3D duplication and the working tree is not clean.
- **Recommended phase gate:** finish forensic comparison and obtain explicit approval before any domain consolidation or migration.

## Providers

Provider state below is intentionally separated from historical live claims and does not expose secret values.

| Provider / component | Current evidence | Classification |
|---|---|---|
| OpenRouter / Union Alpha-compatible | `.env` contains `OPENROUTER_API_KEY` and `UNION_ALPHA_API_KEY` names; adapter exists | **IMPLEMENTED; CONFIGURED-NAME OBSERVED; LIVE NOT VERIFIED IN THIS AUDIT** |
| NVIDIA NIM | `.env` contains `NVIDIA_API_KEY`; adapter exists | **IMPLEMENTED; CONFIGURED-NAME OBSERVED; LIVE NOT VERIFIED IN THIS AUDIT** |
| OpenAI direct | `.env` contains `OPENAI_API_KEY` name; adapter exists | **IMPLEMENTED; VALUE/USABILITY NOT VERIFIED** |
| Anthropic | `.env` contains `ANTHROPIC_API_KEY` name; adapter exists and is untracked | **IMPLEMENTED IN WORKTREE; CONFIGURED-NAME OBSERVED; LIVE NOT VERIFIED** |
| SambaNova | `.env` contains `SAMBANOVA_API_KEY` name; no dedicated provider implementation was established in this audit | **CONFIGURED-NAME OBSERVED; IMPLEMENTATION UNKNOWN** |
| Cerebras | `.env` contains `CEREBRAS_API_KEY` name; no dedicated provider implementation was established in this audit | **CONFIGURED-NAME OBSERVED; IMPLEMENTATION UNKNOWN** |
| Gemini | `.env` contains `GEMINI_API_KEY` name; no dedicated provider implementation was established in this audit | **CONFIGURED-NAME OBSERVED; IMPLEMENTATION UNKNOWN** |
| Local deterministic provider | `local_provider.py` exists and is covered by provider tests | **IMPLEMENTED; TESTED BY SUITE** |
| SAM2 / local CV | Model/provider code and model directory exist | **IMPLEMENTED; FRESH LIVE INFERENCE NOT VERIFIED** |
| Ollama | `ollama_provider.py` exists and `OLLAMA_HOST` is supported by code | **IMPLEMENTED IN WORKTREE BUT EXCLUDED BY PROJECT POLICY; NOT STARTED OR CONFIGURED** |

**Secret handling:** API key names were inspected without displaying values. No secret was copied into this report. The pasted chat material contained exposed credentials; those credentials should be revoked and reissued before any operational use.

## MCP

- **OBSERVED:** `mcp/stratumro_server.py` provides the StratumRO MCP surface.
- **OBSERVED:** `mcp/filesystem/server.py` provides a sandboxed filesystem server.
- **OBSERVED:** `mcp/dataset_manager/server.py` provides geospatial dataset ingestion/download and structural validation components.
- **OBSERVED:** `mcp_config.json` declares five servers: `stratumro`, `filesystem`, `dataset_manager`, `context7`, and `qgis`.
- **OBSERVED:** `.aider.mcp.json` declares `filesystem` and `stratumro`.
- **UNKNOWN:** No MCP server was launched or live tool call was made during this audit.
- **RISK:** The QGIS MCP command depends on a working PyQGIS/QGIS 3.40 environment; that runtime prerequisite was not revalidated here.

## Skills

- **OBSERVED:** Project-local agent roles exist under `.agents/agents/`: architect, geodesy-engineer, gis-engineer, researcher, reviewer, tester, validator, and vision-engineer.
- **OBSERVED:** Project-local rules exist under `.agents/rules/`: evidence, geometry, and qgis_runtime.
- **OBSERVED:** Project-local skills exist under `.agents/skills/`: `gsd-cadastre`, `huashu-design`, and `qgis-live`.
- **VERIFIED:** Hermes skill search found relevant hub entries for Git, QGIS, geospatial work, testing, and repository discovery, but no additional hub skill was installed during this audit.
- **VERIFIED:** Loaded Hermes skills used for this audit were `hermes-agent`, `github`, and `codebase-inspection`.
- **RECOMMENDATION:** Prefer the project-local rules/skills for StratumRO-specific work; use general Hermes skills only for the surrounding workflow.

## Protected Artifacts

- **OBSERVED:** `data/ground_truth/` and `workspace/baseline/` are protected scientific/reference areas.
- **OBSERVED:** `stratum_ro/core/` and `stratum_ro/contracts/` are identified by current project documentation as foundational boundaries.
- **OBSERVED:** Existing uncommitted user/agent changes are protected from overwrite until explicitly reviewed.
- **RULE:** Never edit ground truth, golden manifests, or scientific reference labels to improve metrics.
- **RULE:** Preserve deterministic CRS, geometry, topology, area, distance, and measurement behavior unless an approved scientific change explicitly includes regression evidence.

## Risks

1. **High — Working-tree contamination:** The canonical worktree has many tracked and untracked changes; ownership and intended commit boundaries are not yet resolved.
2. **High — Duplicate implementations:** Domain-pack copies and legacy root modules coexist, creating drift risk.
3. **High — Conflicting historical baselines:** Existing reports claim different test counts and provider states; only fresh execution should be used for current claims.
4. **High — Scientific integrity:** Ground truth and golden baselines must remain immutable unless a documented, reviewed baseline change is approved.
5. **Medium — Provider drift:** Provider adapters contain defaults that may not match currently available upstream model IDs; no live provider probe was performed in this audit.
6. **Medium — QGIS runtime coupling:** QGIS/MCP integration is present but live Desktop availability was not verified.
7. **Medium — Warning debt:** The current suite passes while emitting socket and ONNX Runtime warnings.
8. **Medium — Policy/code mismatch:** `ollama_provider.py` exists although the project onboarding policy says Ollama is excluded. It was not started, configured, or modified.
9. **Medium — Credential exposure:** Historical/chat artifacts contain credential-looking material. Secrets must remain outside reports, commits, and source files; exposed keys should be rotated.
10. **Unknown — Field validation:** No current repository evidence establishes field validation against GNSS RTK or total-station survey logs.

## Unknowns

- Whether every uncommitted file belongs to the same intended Phase 4.2 change set.
- Whether the domain-pack duplicates are byte-identical after all current working-tree changes; existing reports say many are, but this audit did not rewrite or reconcile them.
- Whether current provider keys are valid, active, quota-bearing, or authorized for the intended models.
- Whether QGIS Desktop 3.40 and the QGIS MCP server are currently running and reachable.
- Whether current model files load successfully in the active environment outside the unit-test paths.
- Whether the documented regulatory claims remain current; legal/regulatory conclusions require official current sources.
- Whether Phase 4.3 is actually complete in the current branch.

## Recommended Next Task

**Do not migrate code yet.** The next task should be an approval-gated **Phase 4.2 reconciliation plan**:

1. Inventory and classify every current tracked/untracked change by owner and intended commit.
2. Compare each domain candidate against its legacy root module with hashes and import graphs.
3. Identify the single canonical implementation per domain.
4. Design backward-compatible forwarders without changing scientific behavior.
5. Define targeted regression tests for imports, geometry, CRS, exports, and QGIS consumers.
6. Obtain explicit approval before editing or deleting any duplicate.
7. After approval, make the smallest migration, run targeted tests, then run the full 250-test suite and inspect the diff.

The most important immediate risk is not missing functionality; it is consolidating duplicate implementations without changing scientific behavior or overwriting the existing worktree changes.

## Audit Completion Checklist

- [x] Hermes working context identified as `C:\Users\lefpa\Downloads\QGIS-AI`
- [x] Git repository detected
- [x] Canonical root verified
- [x] `AGENTS.md` read
- [x] Architecture inspected
- [x] Current phase assessed
- [x] Domain packs mapped
- [x] Scientific constraints recorded
- [x] Baseline identified
- [x] Ground truth identified
- [x] Tests identified and executed
- [x] QGIS boundary assessed
- [x] AI/CV boundary assessed
- [x] Provider configuration names inspected without exposing values
- [x] MCP configuration inspected
- [x] Relevant project-local and Hermes skills identified
- [x] Ollama excluded from operational recommendations
- [x] Secrets protected in this report
- [x] No product source files modified during audit
- [x] Current Project Map created
