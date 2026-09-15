# MIGRATION_PLAN.md — Step-by-Step Evolution to Antigravity Control Plane

> **Objective:** Integrate Multi-Model AI Orchestration into StratumRO without disrupting existing functionality.  
> **Guiding Axiom:** "Make StratumRO more trustworthy, not just larger. Protect the working geodetic pipeline."

---

## 1. Non-Negotiable Rules & Invariants

1. **Zero Breaking Changes:** Existing entry points (`run_hybrid_full_aoi.py`, `create_hybrid_qgis_project.py`, `run_regulatory_audit_2026.py`, `StratumROCadastralAlgorithm`) must remain 100% functional.
2. **Deterministic Integrity:** Do not move, refactor, or rewrite core mathematical modules (`vectorizer.py`, `lidar_processor.py`, `cad_exporter.py`, `sam2_engine.py`). They remain authoritative domain engines.
3. **Continuous Regression Testing:** Every phase must execute the unit test suite (`venv\Scripts\python -m unittest discover stratum_ro/test`) maintaining a pass baseline (47 passed, 8 skipped, 0 failed).
4. **Mocked Provider Tests:** Unit tests for external AI providers must use recorded or synthetic mock responses so tests run offline without consuming tokens or failing on network timeouts.
5. **No Secret Leakage:** API keys are read strictly from environment variables or secure storage; `.env` is ignored by Git.

---

## 2. Phased Implementation Roadmap

```mermaid
gantt
    title StratumRO AI Orchestrator Migration Phases
    dateFormat  X
    axisFormat  Phase %d

    section Foundation
    Phase 1: Architecture Audit & Governance       :done, p1, 0, 1
    Phase 2: Provider Abstraction Layer            :active, p2, 1, 2
    Phase 3: Capability Registry & Task Router     :p3, 2, 3

    section Orchestration Core
    Phase 4: Task Graph & Event Bus Engine         :p4, 3, 4
    Phase 5: Domain Engine Tool Wrappers & MCP     :p5, 4, 5
    Phase 6: Context Engine & Session Memory       :p6, 5, 6

    section QGIS Integration & Delivery
    Phase 7: QGIS DockWidget Assistant Panel       :p7, 6, 7
    Phase 8: End-to-End Equivalence Verification   :p8, 7, 8
```

---

### Phase 1: Architecture Audit & Governance (COMPLETED)
* **Actions:**
  - Full codebase inspection across domain engines, QGIS plugin, and existing MCP servers.
  - Test baseline established: 55 unit tests (47 passed, 8 skipped, 0 failed).
  - Production of audit deliverables:
    - `CURRENT_ARCHITECTURE.md`
    - `MCP_TOOL_MAP.md`
    - `AGENT_MAP.md`
    - `MODEL_PROVIDER_MAP.md`
    - `MIGRATION_PLAN.md`
* **Deliverable Review:** Await user sign-off before modifying files.

---

### Phase 2: Provider Abstraction Layer (`stratum_ro/ai/providers/`)
* **Goal:** Create a uniform Python interface for LLM/vision inference providers.
* **New Files:**
  - `stratum_ro/ai/__init__.py`
  - `stratum_ro/ai/providers/__init__.py`
  - `stratum_ro/ai/providers/base.py` (Abstract `BaseAIProvider` class)
  - `stratum_ro/ai/providers/nvidia_nim_provider.py` (Migrates logic from `orchestrator.py`)
  - `stratum_ro/ai/providers/openai_provider.py` (Standard OpenAI API wrapper)
  - `stratum_ro/ai/providers/ollama_provider.py` (Local HTTP client)
  - `stratum_ro/ai/providers/local_provider.py` (Deterministic & mock fallback)
* **Verification:** `stratum_ro/test/test_ai_providers.py` (Mock-based tests for discovery and generation).

---

### Phase 3: Capability Registry & Task Router (`stratum_ro/ai/`)
* **Goal:** Intelligently direct user prompts or geodetic requests to the optimal provider.
* **New Files:**
  - `stratum_ro/ai/registry.py` (Provider health, model availability, and capability catalog)
  - `stratum_ro/ai/router.py` (Rule-based and capability-based task routing)
* **Routing Logic:**
  - Pure math / geometry $\rightarrow$ Local deterministic engine
  - Building segmentation $\rightarrow$ Local SAM2 / ONNX
  - AOI planning / failure diagnosis $\rightarrow$ OpenAI / Claude / NIM / Ollama fallback
* **Verification:** `stratum_ro/test/test_ai_router.py`.

---

### Phase 4: Task Graph & Asynchronous Event Bus
* **Goal:** Asynchronous, stateful execution of multi-step processing plans.
* **New Files:**
  - `stratum_ro/ai/task_graph.py` (Directed acyclic graph with statuses: `PENDING`, `RUNNING`, `SUCCESS`, `FAILED`, `WAITING_FOR_USER`)
  - `stratum_ro/ai/events.py` (Publish/subscribe event dispatcher)
  - `stratum_ro/ai/executor.py` (Worker executing graph nodes sequentially or in parallel)
* **Verification:** `stratum_ro/test/test_ai_task_graph.py`.

---

### Phase 5: StratumRO Domain Engine Tool Wrappers & MCP Integration
* **Goal:** Wrap existing algorithms in clean, functional interfaces for AI and MCP use.
* **New Files:**
  - `stratum_ro/ai/tools/__init__.py`
  - `stratum_ro/ai/tools/qgis_tools.py` (Project, layers, AOI queries)
  - `stratum_ro/ai/tools/lidar_tools.py` (Calls `LidarProcessor`)
  - `stratum_ro/ai/tools/segmentation_tools.py` (Calls `SAM2BuildingSegmenter`)
  - `stratum_ro/ai/tools/vector_tools.py` (Calls `CadastralVectorizer`)
  - `stratum_ro/ai/tools/cadastral_tools.py` (Calls `CadastralDxfExporter`)
  - `mcp/stratumro_server.py` (FastMCP server exposing curated tools to Antigravity)
* **Rule:** Wrappers call existing functions directly without duplicating algorithms.

---

### Phase 6: Project Context & Memory Engine
* **Goal:** Automatically supply spatial and environmental context to the AI.
* **New Files:**
  - `stratum_ro/ai/context.py` (Collects CRS, active layers, available LiDAR/Orthophoto files, GPU status)
  - `stratum_ro/ai/memory/session.py` (Tracks run history, user approvals, and intermediate files in SQLite/JSON)

---

### Phase 7: QGIS DockWidget Assistant Panel (UI)
* **Goal:** Unified user interface inside QGIS without breaking existing controls.
* **Modifications:**
  - Extend `stratum_ro/stratum_ro_dockwidget.py` with an "AI Assistant" tab or collapsible panel.
  - Integrate `QgsTask` / `QThread` for non-blocking execution.
  - Human-in-the-loop modal dialog: displaying preview layers and requiring user confirmation before committing changes to official GeoPackage/DXF layers.

---

### Phase 8: End-to-End Equivalence & Validation
* **Goal:** Verify that AI-orchestrated execution produces identical results to `run_hybrid_full_aoi.py`.
* **Execution:**
  - Run standard benchmark on Cluj USAMV study area.
  - Compare generated building counts, IoU metrics, and boundary coordinates.
  - Verify that no deviations exist between manual script execution and AI-orchestrated execution.

---

## 3. Risk Mitigation Matrix

| Potential Risk | Severity | Mitigation Strategy |
| :--- | :--- | :--- |
| **Network Failure during Cloud API Call** | High | All providers implement strict timeouts ($5\text{--}10\text{ s}$) and auto-fallback to local Ollama or synthetic mocks. |
| **QGIS UI Freeze during Processing** | High | Long-running operations execute exclusively via `QgsTask` or `QThread` with Qt progress signals. |
| **LLM Hallucination of Parcel Boundaries** | Critical | Geometry is generated **exclusively** by deterministic engines (`vectorizer.py`, `buildingregulariser`). LLMs only configure parameters. |
| **Accidental Overwrite of Cadastral Data** | Critical | Destructive operations require explicit user approval (`ASK` gate). Results are written to temporary preview layers first. |
