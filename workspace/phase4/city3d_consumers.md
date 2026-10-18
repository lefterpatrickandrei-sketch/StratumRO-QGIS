# City 3D Consumers Inventory — StratumRO Phase 4.3

**Comprehensive Inventory of All Importers and Callers of `stratum_ro.volumetric_3d`**  
*Status as of 2026-09-20 — Evaluated via Full Working Tree AST & Text Search*

---

## 1. Consumer Classification Table

| Consumer File | Import Statement | Symbols Used | Consumer Classification | Operational Role |
| :--- | :--- | :--- | :--- | :--- |
| `stratum_ro/ai/tools/vector_tools.py` | `from stratum_ro.volumetric_3d import Volumetric3DBuilder` | `Volumetric3DBuilder` | **PRODUCT RUNTIME** | Generates 3D GeoPackage layer with MultiPolygonZ solids |
| `stratum_ro/pug_product.py` | `from .volumetric_3d import Volumetric3DBuilder` | `Volumetric3DBuilder` | **PRODUCT RUNTIME (PROTOTYPE)** | PUG 3D zoning height adapter |
| `stratum_ro/test/test_volumetric_3d.py` | `from stratum_ro.volumetric_3d import Volumetric3DBuilder, _extract_polygons` | `Volumetric3DBuilder`, `_extract_polygons` | **TEST** | Dedicated unit test suite verifying LoD1 extrusion, CityJSON, and RANSAC |
| `.kilo/worktrees/geode-barber/...` | `from stratum_ro.volumetric_3d import Volumetric3DBuilder` | `Volumetric3DBuilder` | **WORKTREE** | Ephemeral Git worktree tracking branch `geode-barber` |
| `.kilo/worktrees/lowly-vanilla/...` | `from stratum_ro.volumetric_3d import Volumetric3DBuilder` | `Volumetric3DBuilder` | **WORKTREE** | Ephemeral Git worktree tracking branch `lowly-vanilla` |

---

## 2. Consumer Impact Analysis

- **Direct Coupling:** Only 2 active production files (`vector_tools.py`, `pug_product.py`) and 1 test file (`test_volumetric_3d.py`) directly import `volumetric_3d`.
- **Zero QGIS GUI Coupling:** `stratum_ro_dockwidget.py` does NOT directly import `volumetric_3d` (it calls vector tools).
- **Forwarder Guarantee:** By converting `stratum_ro/volumetric_3d.py` into a compatibility forwarder re-exporting `Volumetric3DBuilder` and `_extract_polygons`, 100% of existing consumers and external scripts will continue to execute seamlessly without requiring code modifications.
