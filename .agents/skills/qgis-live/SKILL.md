---
name: qgis-live
description: QGIS Desktop 3.40 live interaction, spectator mode orchestration, and visual canvas inspection
---

# QGIS Live: Desktop Runtime Orchestration

This skill guides the agent in orchestrating, inspecting, and interacting with QGIS Desktop 3.40 on Windows.

## Capabilities & Workflows

### 1. Launching Live Spectator Mode
When a visual audit or surveyor demonstration is required:
```powershell
cmd.exe /c run_qgis_spectator.bat
```
- Automatically uses `C:\Program Files\QGIS 3.40.0\bin\o4w_env.bat`.
- Loads the workspace project (`workspace/output/StratumRO_Rezultate.qgz` or `StratumRO_Inspectie_Vizuala.qgz`).
- Runs `tools/live_qgis_spectator.py` to animate layers and highlight building candidates.

### 2. Live QGIS MCP Communication
When QGIS MCP is active in QGIS Desktop:
- Host: `127.0.0.1`
- Agent can:
  - List loaded layers (`vector`, `raster`, `pointcloud`)
  - Query feature attributes and geometries
  - Zoom canvas to coordinates: `[x_min, y_min, x_max, y_max]` in Stereo 70 (`EPSG:3844`)
  - Capture map canvas screenshots to verify symbology and alignment

### 3. Layer Validation Checklist
Before concluding visual inspection:
- [ ] Orthophoto RGB bands correctly displayed (no contrast blowout)
- [ ] LiDAR nDSM elevation heights range between 0m and 45m
- [ ] Cadastral building layer (`1CC` / `2CC`) sits on ground footprint (-0.40m retracted from eaves)
- [ ] Vertices layer (`VARFURI`) matches polygon corners without rogue floating points
- [ ] No overlapping polygons within the same cadastre parcel sector
