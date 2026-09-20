# StratumRO Geometry & Deterministic Math Rules

## 1. Local Deterministic Computation Only
- **Zero LLM Coordinates:** Large Language Models (LLMs) are strictly forbidden from calculating or modifying polygon coordinates, vertex coordinates, transformation matrices, or geodetic residuals.
- **Python / GEOS / GDAL / Shapely:** All spatial calculations (Helmert 2D transformations, 90° CAD orthogonalization, eave retraction offsets, polygon areas, perimeters, PAD coordinate tables, and topology cleanup) MUST be executed through local deterministic Python math via `shapely`, `geopandas`, `gdal`, and `pyproj`.

## 2. Coordinate Reference System (CRS)
- **Official Projection:** Romania Stereo 70 (`EPSG:3844`).
- **Vertical Datum:** Cota Marea Neagră 1975 (`EPSG:5781`).
- All vector layers, orthophoto chips, and LiDAR point clouds must maintain strict CRS integrity. Reprojection on-the-fly without geodetic datum shift parameters is prohibited.

## 3. Cadastral & TopoLT Conventions
- **Layer Nomenclature:** Enforce TopoLT standard layer naming:
  - `1CC`: Cadastral parcel boundary
  - `2CC`: Auxiliary boundary / construction footprint
  - `CP`: Cadastral parcel polygon
  - `VARFURI`: Boundary vertices
  - `NUMERE_PCT`: Vertex numbering text
- **Eave Retraction:** Apply mandatory ground footprint offset ($-0.40\text{ m}$) from roof eaves to comply with ANCPI Ordinul nr. 600/2023.
- **Topology:** Enforce 0 self-intersections, 0 duplicate vertices, and strict planar partitioning (0 slivers, 0 overlapping construction geometries).
