# City 3D Domain Pack — StratumRO

**Canonical 3D Volumetric Extrusion, LoD1 Solid Shell Modeling & OGC CityJSON v1.1 Export**  
*Maturity Level:* **MATURE**  
*Canonical Implementation:* [`builder.py`](file:///c:/Users/lefpa/Downloads/QGIS-AI/stratum_ro/domain/city_3d/builder.py)  
*Legacy Compatibility Entrypoint:* [`stratum_ro/volumetric_3d.py`](file:///c:/Users/lefpa/Downloads/QGIS-AI/stratum_ro/volumetric_3d.py)

---

## 1. Purpose

The `city_3d` domain pack transforms 2D regularized cadastral building footprints and LiDAR elevation models into valid, watertight 3D architectural representations. It serves municipal GIS workflows, urban planning analyses, and 3D cadastral registries by generating standard OGC CityJSON v1.1 files and 3D GeoPackage layers.

---

## 2. Capabilities

1. **LoD1 Solid Shell Extrusion:**  
   Extrudes 2D polygon footprints into true 3D watertight solid shells (`MultiPolygonZ` geometries with 1 horizontal floor face, 1 horizontal roof face, and $N$ vertical rectangular wall faces).
2. **LoD1 2.5D Roof Surface Generation:**  
   Generates horizontal roof polygon geometries at $Z = Z_{\text{ground}} + H_{\text{building}}$.
3. **RANSAC 3D Roof Plane Fitting:**  
   Fits 3D planes ($Ax + By + Cz + D = 0$) to LiDAR roof point clusters to estimate roof typology (`TERASA`, `DOUA_APE`, `MANSARDA_INCLINATA`), slope tilt in degrees, and ridge elevation ($Z_{\text{coama}}$).
4. **OGC CityJSON v1.1 Export:**  
   Serializes multi-building 3D LoD1 models into standard CityJSON v1.1 with deduplicated vertices, Stereo 70 (EPSG:3844) CRS metadata, building attributes (`measuredHeight`, `elevationGround`, `groundArea_m2`), and 3D solid boundaries.

---

## 3. Input Contract

- **`poly_2d`:** `shapely.geometry.Polygon` representing a clean 2D building footprint (projected in Stereo 70, minimum area $\ge 2.0\,\text{m}^2$).
- **`height_m`:** Building height in meters (clamped to minimum $1.5\,\text{m}$ for physical validity).
- **`ground_z`:** Optional terrain elevation in meters from LiDAR DTM (defaults to $345.0\,\text{m}$ if omitted).
- **`roof_points_xyz`:** Optional $N \times 3$ NumPy array of 3D point cloud coordinates for RANSAC fitting (requires $\ge 6$ points).

---

## 4. Output Contract

- **`MultiPolygonZ`:** Watertight 3D solid composed of $N + 2$ 3D polygon faces with coordinate triples $(X, Y, Z)$ rendered natively in QGIS 3D Map Views.
- **OGC CityJSON v1.1 File:** JSON document conforming to CityJSON schema with vertices rounded to $1\,\text{mm}$ precision ($0.001\,\text{m}$).

---

## 5. Dependencies & Isolation

- **Core Dependencies:** Python standard libraries (`os`, `json`, `math`, `typing`), `numpy`, `shapely.geometry`.
- **Zero QGIS GUI Coupling:** Completely importable and executable in headless batch environments.
- **Zero LLM / AI Coupling:** Pure mathematical and geometric algorithms. No dependence on external API keys or language models.

---

## 6. Contracts & Interfaces

- Fulfills the domain interface contracts defined in `stratum_ro.contracts.domain.IDomainPack`.

---

## 7. Tests & Verification

- **Dedicated Unit Tests:** [`stratum_ro/test/test_volumetric_3d.py`](file:///c:/Users/lefpa/Downloads/QGIS-AI/stratum_ro/test/test_volumetric_3d.py) (6 tests covering extrusion, RANSAC, CityJSON export, edge cases, and forwarder equivalence).
- **Golden Baseline Fixture:** [`workspace/baseline/city3d_golden_baseline.json`](file:///c:/Users/lefpa/Downloads/QGIS-AI/workspace/baseline/city3d_golden_baseline.json).

---

## 8. Known Limitations

- **LoD2 Roof Planes:** Current RANSAC fitting estimates planar tilt and typology, but does not yet construct multi-pitch geometric solids (LoD2 remains an active R&D capability).
- **Courtyards / Interior Rings:** Polygons with interior holes (donut courtyards) currently extrude exterior boundaries.
