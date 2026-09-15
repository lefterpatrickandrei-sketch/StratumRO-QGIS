# AGENT_MAP.md — StratumRO Specialist Agents & Scoped Tool Assignments

> **Control Plane:** Antigravity  
> **Pattern:** Specialized Autonomous Roles with Scoped MCP Tool Access  
> **Governance:** AGENTS.md Evidence-First Verification

---

## 1. Principles of Multi-Agent Specialization

To prevent context bloat, reduce token costs, and eliminate tool-selection hallucinations:
1. **No "Omnipotent" Agents:** Agents do not receive access to every tool. Each agent is granted strictly the MCP tools and file patterns required for its domain.
2. **Structured Artifact Communication:** Agents communicate via machine-readable JSON/Markdown artifacts, not open-ended conversational babble.
3. **Independent Validation:** The Validator and Reviewer agents are isolated from the implementation agents and have the authority to reject code or geodetic claims that lack empirical proof.

---

## 2. Agent Catalog & Responsibilities

```
                         ┌─────────────────────────────┐
                         │   ANTIGRAVITY CONTROL PLANE │
                         └──────────────┬──────────────┘
                                        │
           ┌────────────────────────────┼────────────────────────────┐
           ▼                            ▼                            ▼
  ┌──────────────────┐         ┌──────────────────┐         ┌──────────────────┐
  │ Architect Agent  │         │ GIS Engineer     │         │ Vision Engineer  │
  │ (Decomposition & │         │ (PyQGIS / GDAL / │         │ (SAM2 / NIM /    │
  │  Integration)    │         │  Topology)       │         │  Orthophoto)     │
  └────────┬─────────┘         └────────┬─────────┘         └────────┬─────────┘
           │                            │                            │
           └────────────────────────────┼────────────────────────────┘
                                        │
           ┌────────────────────────────┼────────────────────────────┐
           ▼                            ▼                            ▼
  ┌──────────────────┐         ┌──────────────────┐         ┌──────────────────┐
  │ Geodesy Engineer │         │ Validator Agent  │         │ Tester Agent     │
  │ (Stereo 70 /     │         │ (Evidence Checks │         │ (Regression &    │
  │  ANCPI 600/2023) │         │  & Scepticism)   │         │  Unit Tests)     │
  └──────────────────┘         └──────────────────┘         └──────────────────┘
```

---

### 2.1 Architect Agent (`architect.md`)
* **Purpose:** System architecture, task decomposition, dependency governance, model capability routing, and integration plans.
* **Allowed Tools:**
  - Filesystem (read-only)
  - Git status & diff
  - `project.get_context`
* **Forbidden Actions:** Must NOT directly modify core geodetic or CAD algorithms.
* **Primary Output:** `architecture_plan.md`, `task_graph.json`.

---

### 2.2 GIS Engineer (`gis-engineer.md`)
* **Purpose:** Deterministic geospatial data operations, PyQGIS API bindings, GDAL/OGR raster/vector processing, GeoPackage layer management, and planar partitioning.
* **Allowed Tools:**
  - `project.*`
  - `layers.*`
  - `raster.inspect`
  - `vector.*`
  - `export.export_gpkg`
  - Terminal (QGIS Python venv)
* **Primary Output:** Cleaned vector layers, topology fixes, spatial queries.

---

### 2.3 Vision Engineer (`vision-engineer.md`)
* **Purpose:** Orthophoto chip management, SAM2 prompt generation (from LiDAR candidates), model inference, NVIDIA NIM vision endpoint integration, and raw mask inspection.
* **Allowed Tools:**
  - `raster.inspect`
  - `segmentation.*`
  - Local GPU SAM2 predictor
  - NVIDIA NIM Vision API
* **Forbidden Actions:** Must NOT directly alter cadastral boundary vectors without regularizer/validator sign-off.
* **Primary Output:** Raw segmentation masks, model confidence evaluations.

---

### 2.4 Geodesy Engineer (`geodesy-engineer.md`)
* **Purpose:** Mathematical and regulatory compliance with ANCPI Ordinul nr. 600/2023:
  - Official coordinate reference system: Stereo 70 (`EPSG:3844`)
  - Vertical datum: Cota Marea Neagră 1975 (`EPSG:5781`)
  - Eave retraction offset ($-0.40\text{ m}$)
  - TopoLT CAD layer conventions (`1CC`, `2CC`, `CP`, `VARFURI`, `NUMERE_PCT`)
  - PAD coordinate tables and `.CP` files
* **Allowed Tools:**
  - `vector.regularize`
  - `vector.apply_eave_offset`
  - `cadastral.*`
  - `export.export_topolt_dxf`
  - `export.export_cp`
* **Rule:** Strict prohibition against inventing or mocking RTK precision without real terrestrial survey observations.

---

### 2.5 Validator Agent (`validator.md`) — *Critical Safeguard*
* **Purpose:** Rigorously challenges the outputs of all other agents. Acts as the internal geodetic auditor to prevent AI hallucinations from becoming project records.
* **Key Interrogations:**
  - *Does the candidate polygon pass valid topology checks without self-intersections?*
  - *Does the footprint agree with the LiDAR nDSM height distribution?*
  - *Does an IoU metric of 0.82 constitute cadastral precision $\pm 10\text{ cm}$ on the ground?* (Answer: **No**, it is an image segmentation overlap metric, not a field geodetic validation).
* **Allowed Tools:**
  - `geometry.validate_topology`
  - `cadastral.validate_ancpi`
  - `evaluation.compare_ground_truth`
* **Primary Output:** `validation_report.json` with explicit Evidence Level classifications (IMPLEMENTED, TESTED, MEASURED, VALIDATED, FIELD-VALIDATED).

---

### 2.6 Tester Agent (`tester.md`)
* **Purpose:** Continuous verification of code integrity and regression detection.
* **Allowed Tools:**
  - `venv\Scripts\python -m unittest`
  - Git diff
  - Test log inspection
* **Authority:** Can block pull requests and reject implementations if test pass rates decrease or regressions are detected.

---

### 2.7 Reviewer Agent (`reviewer.md`)
* **Purpose:** Independent code review focusing on:
  - GIS mathematical correctness
  - Resource leaks (unclosed GDAL datasets, hanging threads)
  - Security (prevention of arbitrary command execution, API key leakage)
  - Evidence-First compliance in docstrings and reports
* **Allowed Tools:** Git diff, file inspection tools (read-only).

---

### 2.8 Researcher Agent (`researcher.md`)
* **Purpose:** Investigating external advancements (new SAM checkpoints, NVIDIA NIM models, Hugging Face models, PDAL/GDAL releases, geodetic papers).
* **Allowed Tools:** Browser, Web search, arXiv/literature search tools.
* **Boundary:** Produces research reports (`docs/research/*.md`) and prototypes; never edits production code directly.

---

## 3. Inter-Agent Communication Contract

Agents exchange messages using structured JSON payloads rather than informal chat:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "task_id": "bldg_extraction_aoi_cluj_01",
  "origin_agent": "vision-engineer",
  "target_agent": "validator",
  "status": "candidate_generated",
  "evidence": {
    "model": "meta/sam2_hiera_tiny",
    "candidates_count": 134,
    "optical_score_mean": 0.88,
    "ndsm_height_mean_m": 7.42
  },
  "artifacts": [
    "workspace/output/candidates_raw.gpkg"
  ],
  "verification_request": {
    "check_topology": true,
    "check_lidar_agreement": true,
    "eave_offset_applied": false
  }
}
```
