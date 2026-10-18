# City 3D Canonical Migration Report — StratumRO Phase 4.3

**Comprehensive Migration Documentation for the First Domain Consolidation (`city_3d`)**  
*Status as of 2026-09-20 — Evaluated under Master Reorientation Governance*

---

## 1. Initial State
Prior to Phase 4.3, two parallel files existed on disk:
- `stratum_ro/volumetric_3d.py` (9,350 bytes, SHA-256: `3a9a4e5e5de5...`)
- `stratum_ro/domain/city_3d/builder.py` (9,350 bytes, SHA-256: `3a9a4e5e5de5...`)
All active consumers imported strictly from `stratum_ro.volumetric_3d`, leaving the domain pack unintegrated and creating duplicate maintenance overhead.

---

## 2. Duplicate Evidence
Byte-for-byte SHA-256 verification proved the two files were **100% IDENTICAL** before migration:
- `volumetric_3d.py`: `3a9a4e5e5de513a5b0f304fa80c1288f72556de44f23c7228c09ba1ee4ecec09`
- `domain/city_3d/builder.py`: `3a9a4e5e5de513a5b0f304fa80c1288f72556de44f23c7228c09ba1ee4ecec09`

---

## 3. Public API
The public API of the `city_3d` domain consists of:
- `Volumetric3DBuilder`:
  - `extrude_lod1_solid(poly_2d, height_m, ground_z=None) -> Optional[MultiPolygon]`
  - `create_lod1_roof_surface(poly_2d, height_m, ground_z=None) -> Optional[Polygon]`
  - `estimate_lod2_roof_planes(roof_points_xyz, ransac_threshold=0.25, max_iterations=150) -> Dict[str, Any]`
  - `export_cityjson(buildings_lod1, output_cityjson_path, epsg_code=3844) -> str`
- `_extract_polygons(geom) -> List[Polygon]`

---

## 4. Consumers
All consumers were mapped via AST and text search:
- `stratum_ro/ai/tools/vector_tools.py` (`PRODUCT RUNTIME`)
- `stratum_ro/pug_product.py` (`PRODUCT RUNTIME (PROTOTYPE)`)
- `stratum_ro/test/test_volumetric_3d.py` (`TEST`)
Zero direct calls from QGIS Desktop GUI (`stratum_ro_dockwidget.py`), making `city_3d` an ideal first leaf migration candidate.

---

## 5. Dependency Graph
```text
stratum_ro.domain.city_3d.builder
       │
       ├──> numpy (numeric operations & RANSAC)
       ├──> shapely.geometry (Polygon, MultiPolygon 3D)
       └──> python stdlib (os, json, math, typing)
```
- Core dependency: Fulfills `stratum_ro.contracts.domain.IDomainPack`. Zero backward dependencies from `core` to `city_3d`.
- Circular dependency risk: **ZERO**.

---

## 6. Domain Boundary
- Belongs to `city_3d`: LoD1 extrusion, 3D floor/roof/wall face generation, RANSAC roof slope analysis, OGC CityJSON v1.1 serialization.
- Excluded from `city_3d`: 2D polygon regularization (belongs to `core.geometry`), CRS coordinate transformation (belongs to `core.geodesy`), LiDAR filtering (belongs to `domain.lidar`).

---

## 7. Golden Cases
Four representative cases were captured into [`workspace/baseline/city3d_golden_baseline.json`](file:///c:/Users/lefpa/Downloads/QGIS-AI/workspace/baseline/city3d_golden_baseline.json):
- **Case A:** Single rectangular building (6 faces, $Z_{\text{base}} = 350.0\,\text{m}$, $Z_{\text{roof}} = 356.5\,\text{m}$, total surface area $780.0\,\text{m}^2$).
- **Case B:** MultiPolygon building (extrudes two independent watertight solid shells).
- **Case C:** RANSAC 3D roof plane fitting ($Ax+By+Cz+D=0$, fixed seed 42, classified `TERASA`).
- **Case D:** CityJSON v1.1 serialization with deduplicated vertices and EPSG:3844 reference system.

---

## 8. Migration Execution
1. Canonical implementation established at: `stratum_ro/domain/city_3d/builder.py`.
2. Root module `stratum_ro/volumetric_3d.py` converted into a backward-compatible forwarder re-exporting `Volumetric3DBuilder` and `_extract_polygons`.
3. Package root `stratum_ro/domain/city_3d/__init__.py` updated to export both symbols.
4. Exactly **ONE active implementation** exists on disk.

---

## 9. Backward Compatibility
- Class identity test verified: `OldBuilder is CanonicalBuilder is PackageBuilder` (evaluated to `True`).
- Function identity test verified: `old__extract_polygons is canonical__extract_polygons` (evaluated to `True`).
- Legacy consumers continue running without modification.

---

## 10. Tests & Verification
- Unit test suite: [`test_volumetric_3d.py`](file:///c:/Users/lefpa/Downloads/QGIS-AI/stratum_ro/test/test_volumetric_3d.py) extended with 3 new tests (forwarder equivalence, edge case handling, 2.5D roof surface).
- Result: **6 tests passed out of 6** in 0.014s.
- Golden freeze test: [`test_phase1_golden_freeze.py`](file:///c:/Users/lefpa/Downloads/QGIS-AI/stratum_ro/test/test_phase1_golden_freeze.py) updated to verify canonical domain implementation hash for `city_3d`. Result: **5 tests passed out of 5** in 0.016s.
- Contracts test: [`test_contracts.py`](file:///c:/Users/lefpa/Downloads/QGIS-AI/stratum_ro/test/test_contracts.py): **5 tests passed out of 5** in 0.012s.

---

## 11. Scientific Regression Assessment
- Coordinates: **Unchanged** ($\Delta X = 0.000\,\text{m}, \Delta Y = 0.000\,\text{m}, \Delta Z = 0.000\,\text{m}$).
- Watertight solids: **Preserved** (floor, roof, wall faces identical under `equals_exact(1e-9)`).
- LoD: **Preserved** (LoD1.2 solid geometries in CityJSON).
- RANSAC parameters: **Preserved** (threshold 0.25, max iterations 150, seed 42).
- Scientific regression: **ZERO REGRESSIONS DETECTED**.

---

## 12. Git State
- Modified tracked files:
  - `stratum_ro/volumetric_3d.py` (converted to forwarder)
  - `stratum_ro/domain/city_3d/__init__.py` (re-exports symbols)
  - `stratum_ro/domain/city_3d/README.md` (domain documentation)
  - `stratum_ro/test/test_volumetric_3d.py` (extended unit tests)
  - `stratum_ro/test/test_phase1_golden_freeze.py` (canonical hash mapping)
- Canonical implementation:
  - `stratum_ro/domain/city_3d/builder.py` (untracked candidate, preserved byte-for-byte)

---

## 13. Rollback Procedure
If rollback is ever required:
```powershell
git checkout stratum_ro/volumetric_3d.py
```
This instantly restores the original 9,350-byte monolith without data loss.

---

## 14. Final Ownership
- **Canonical Implementation:** [`stratum_ro/domain/city_3d/builder.py`](file:///c:/Users/lefpa/Downloads/QGIS-AI/stratum_ro/domain/city_3d/builder.py)
- **Compatibility Forwarder:** [`stratum_ro/volumetric_3d.py`](file:///c:/Users/lefpa/Downloads/QGIS-AI/stratum_ro/volumetric_3d.py)
- **Domain Status:** **MATURE**
