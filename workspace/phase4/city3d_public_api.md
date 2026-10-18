# City 3D Public API Inventory — StratumRO Phase 4.3

**Authoritative Inventory of Classes, Methods, Functions, Signatures, and Exceptions**  
*Source File:* `stratum_ro/volumetric_3d.py` & `stratum_ro/domain/city_3d/builder.py`  
*Domain Ownership:* **STRATUMRO PRODUCT (Domain: `city_3d`)**

---

## 1. Symbol Inventory Table

| Symbol | Signature | Return Type | Exceptions Raised | Consumers | Tests | Domain Ownership |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `_extract_polygons` | `(geom: Any) -> List[Polygon]` | `List[Polygon]` | None | Internal helper | `test_volumetric_3d.py` | `city_3d` |
| `Volumetric3DBuilder` | `class Volumetric3DBuilder` | N/A | None | `ai/tools/vector_tools.py`, `pug_product.py` | `test_volumetric_3d.py` | `city_3d` |
| `__init__` | `(default_ground_z: float = 345.0)` | None | None | Instantiation | `test_volumetric_3d.py` | `city_3d` |
| `extrude_lod1_solid` | `(poly_2d: Polygon, height_m: float, ground_z: Optional[float] = None)` | `Optional[MultiPolygon]` | None (returns None on degenerate geom) | `vector_tools.py` | `test_volumetric_3d.py` | `city_3d` |
| `create_lod1_roof_surface` | `(poly_2d: Polygon, height_m: float, ground_z: Optional[float] = None)` | `Optional[Polygon]` | None (returns None on empty geom) | Public API | `test_volumetric_3d.py` | `city_3d` |
| `estimate_lod2_roof_planes` | `(roof_points_xyz: np.ndarray, ransac_threshold: float = 0.25, max_iterations: int = 150)` | `Dict[str, Any]` | None (handles degenerate array safely) | Public API | `test_volumetric_3d.py` | `city_3d` |
| `export_cityjson` | `(buildings_lod1: List[Dict[str, Any]], output_cityjson_path: str, epsg_code: int = 3844)` | `str` (output path) | `OSError` on directory write fail | Public API | `test_volumetric_3d.py` | `city_3d` |

---

## 2. Mathematical & Algorithmic Invariants

1. **Floor Face:** Extruded 3D polygon at $Z = Z_{\text{base}}$ ($Z_{\text{base}} = \text{ground\_z}$ or default $345.0\,\text{m}$).
2. **Roof Face:** Extruded 3D polygon at $Z = Z_{\text{base}} + \max(\text{height\_m}, 1.5\,\text{m})$.
3. **Wall Faces:** Rectangular quadrilateral faces connecting coordinate $(X_i, Y_i, Z_{\text{base}})$ to $(X_{i+1}, Y_{i+1}, Z_{\text{base}})$, $(X_{i+1}, Y_{i+1}, Z_{\text{roof}})$, $(X_i, Y_i, Z_{\text{roof}})$.
4. **Watertight Solid MultiPolygonZ:** A complete closed shell consisting of 1 floor + 1 roof + $N$ walls ($N+2$ faces).
5. **RANSAC 3D Plane Fitting:**
   - Model: $Ax + By + Cz + D = 0$.
   - Fixed random seed (`np.random.seed(42)`).
   - Roof slope tilt classification:
     - `TERASA`: $\text{tilt} < 8.0^\circ$
     - `DOUA_APE`: $8.0^\circ \le \text{tilt} < 45.0^\circ$
     - `MANSARDA_INCLINATA`: $\text{tilt} \ge 45.0^\circ$
6. **CityJSON v1.1 Export:**
   - CRS metadata: `https://www.opengis.net/def/crs/EPSG/0/{epsg_code}` (default EPSG:3844 Stereo 70).
   - Solid boundaries structure: 3-level nested index list matching OGC CityJSON v1.1 specification.
   - Deduped vertices indexed with coordinate rounding to 3 decimal places ($1\,\text{mm}$ precision).
