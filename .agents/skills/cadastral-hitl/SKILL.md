---
name: cadastral-hitl
description: Human-in-the-Loop (HITL) Cadastral Repair & QGIS Live Canvas Feedback Bridge
---

# Cadastral HITL: Interactive Human-in-the-Loop Feedback & Geometry Repair

This skill equips Antigravity to receive visual feedback from the licensed surveyor in QGIS Desktop 3.40 (via mouse selection on port 9876 or attribute marking), diagnose geometric defects, and execute instant deterministic repairs.

## 1. Operating Architecture

```text
SURVEYOR IN QGIS DESKTOP 3.40
  │  (Selects features with mouse OR edits 'rev_status' in attribute table)
  ▼
TCP SOCKET (127.0.0.1:9876 - qgis_mcp_plugin)
  ▲
  │  JSON-RPC protocol: get_selection, update_feature_geometry, commit_edits
  ▼
STRATUMRO HITL CONTROLLER (tools/hitl_feedback_bridge.py)
  │  (Applies deterministic GEOS/Shapely transformations)
  ▼
UPDATED GEOMETRY IN QGIS CANVAS (< 1.5s latency)
```

## 2. Supported Interactive Commands

When the surveyor gives verbal feedback in chat:

1. **Unifică clădirile selectate ("Merge selected"):**
   - Surveyor: *„Am selectat clădirile 4 și 5 în QGIS. Unește-le într-un singur corp.”*
   - Execution:
     ```powershell
     venv\Scripts\python.exe tools/hitl_feedback_bridge.py --action merge --layer CLADIRI_SOL_ANCPI
     ```
   - Applies morphological closing bridge `(P1 | P2).buffer(+0.80).buffer(-0.80)`, updates canvas, and saves changes.

2. **Regularizează la 90 de grade ("Regularize selected"):**
   - Surveyor: *„Clădirea selectată are dinți de pixeli, transform-o în dreptunghi la 90°.”*
   - Execution:
     ```powershell
     venv\Scripts\python.exe tools/hitl_feedback_bridge.py --action regularize --layer CLADIRI_SOL_ANCPI
     ```
   - Fits exact Minimum Rotated Rectangle (OBB) or Manhattan frame with 4–8 clean vertices.

3. **Șterge artefactele selectate ("Delete selected"):**
   - Surveyor: *„Șterge copacii selectați din parcare, sunt mașini, nu arbori.”*
   - Execution:
     ```powershell
     venv\Scripts\python.exe tools/hitl_feedback_bridge.py --action delete --layer ARBORI
     ```
   - Removes features from active layer and commits edits.

4. **Ajustează retragerea streșinii ("Adjust eave offset"):**
   - Surveyor: *„Ajustează retragerea streșinii pe clădirea selectată la 0.50m.”*
   - Execution:
     ```powershell
     venv\Scripts\python.exe tools/hitl_feedback_bridge.py --action set_eave_offset --offset 0.50 --layer CLADIRI_SOL_ANCPI
     ```

## 3. Attribute-Based Review Workflow (Batch Mode)

For surveyors reviewing dozens of buildings simultaneously:
1. Open Attribute Table on layer `CLADIRI_SOL_ANCPI`.
2. Edit column `rev_status`:
   - `APROBAT` (green): Confirmed valid cadastral footprint.
   - `RESPINS` (red): False positive to be eliminated.
   - `REPARA` (yellow): Needs automatic morphological repair.
3. Edit column `rev_issue` (optional reason):
   - `DINTI_RASTER`, `FRAGMENTAT`, `FALS_POZITIV`, `FARA_FOTO`.
4. Press `Ctrl + S` in QGIS.
5. In chat, type: *„Procesează revizuirile din QGIS.”*
   - Controller runs:
     ```powershell
     venv\Scripts\python.exe tools/hitl_feedback_bridge.py --action process_reviews
     ```
