---
name: gsd-cadastre
description: Native Antigravity Spec-Driven Cadastral Workflow (Discuss -> Research -> Plan -> Execute -> Test -> QGIS Verify -> Kilo Audit)
---

# GSD Cadastre: Spec-Driven Cadastral Workflow

This skill executes high-discipline, evidence-first geomatics development for StratumRO. It eliminates "context rot" and premature code completion by enforcing a strict 7-stage verification loop.

## The 7-Stage Cadastral Loop

```text
1. DISCUSS    Define exact geodetic, topological, or algorithmic boundary.
      ↓
2. RESEARCH   Inspect relevant files (vectorizer, cad_exporter, lidar_processor) & active layers.
      ↓
3. PLAN       Create formal implementation plan (what changes, what must NOT change).
      ↓
4. EXECUTE    Implement code strictly using local deterministic Python/GEOS/GDAL math.
      ↓
5. TEST       Execute 193 unit tests (venv\Scripts\python -m unittest discover stratum_ro/test).
      ↓
6. QGIS E2E   Render real raster/LiDAR layers in QGIS Desktop 3.40 (spectator or QGIS MCP).
      ↓
7. VERIFY     Audit with Kilo (Claude 3.5 Sonnet / DeepSeek via OpenRouter) before git commit.
```

## Stage Guidelines

### Stage 1: Discuss & Scope
- Clearly state: What is the exact input? (Orthophoto resolution, LiDAR density, Stereo 70 extent).
- What is the exact deliverable? (TopoLT DXF, .CP file, GeoPackage layer, LoD1 CityJSON).

### Stage 2: Research & Documentation Lookup
- Check existing FastMCP tools in `mcp/stratumro_server.py`.
- If working with complex GDAL/PyQGIS/Shapely 2.0 signatures, use Context7 MCP (`use context7`) to verify current APIs.

### Stage 3: Strict Plan (Planning Mode)
- Never modify files without an approved `implementation_plan.md`.
- Explicitly list dependencies, affected modules, and regression test suites.

### Stage 4: Deterministic Local Execution
- Execute all geometric transforms locally in `venv\Scripts\python`.
- Never hallucinate coordinates or RTK points.

### Stage 5: Automated Test Suite
- Run:
  ```powershell
  venv\Scripts\python -m unittest discover stratum_ro/test
  ```
- Ensure: 0 failed, exact count reported.

### Stage 6: Real QGIS Verification
- Validate against real datasets in `workspace/output/`.
- Inspect geometries in QGIS Desktop 3.40 via spectator launcher (`run_qgis_spectator.bat`) or QGIS MCP.

### Stage 7: Adversarial Review
- Check against `AGENTS.md` and `.kilorules`.
- Run Kilo audit or independent review before marking the task complete.
