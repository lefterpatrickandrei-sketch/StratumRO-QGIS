# StratumRO QGIS Runtime & Visual Verification Rules

## 1. Real Runtime Over Pure Mocks
- Code must not be judged purely on unit tests running against synthetic mocks.
- Production and deliverable evaluation requires real orthophoto raster layers (`.tif`), airborne LiDAR (`.laz`), and GeoPackage database (`.gpkg`) files.

## 2. QGIS Live Control Plane
- When QGIS Desktop 3.40 is running, the agent should interact with the active project via QGIS MCP or spectator scripts (`run_qgis_spectator.bat`).
- Visual confirmation of candidate regularizations, 3D LoD1 extrusions, and TopoLT layer styles is an integral part of the verification pipeline.

## 3. Sandboxed File Operations
- All pipeline outputs, previews, and exports must be written to `workspace/output/` or `workspace/output/preview/`.
- Never overwrite official ground truth data (`data/ground_truth/`) during normal pipeline operations.
