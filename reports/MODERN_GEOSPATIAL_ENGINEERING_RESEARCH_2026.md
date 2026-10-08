# Modern Geospatial Engineering Practice (2026) — Research Brief for StratumRO

**Author:** research subagent (spawned session)
**Date:** 2026-10-08
**Scope:** data formats, provenance, QA/QC, reproducibility, CI, GeoML/MLOps, LLM/VLM orchestration
**Target system:** StratumRO — Romanian pre-cadastral vectorization, QGIS/PyQGIS + Python + GeoPackage

---

## 0. Method and evidence legend

Every claim below is tagged:

| Tag | Meaning |
|---|---|
| **[LIVE]** | I executed a command on the dev box or an HTTP/Docker/PyPI probe and observed the result. |
| **[DOC]** | Verified against an official spec / official docs page that I fetched. |
| **[PUB]** | Peer-reviewed paper or authoritative institutional publication (NOAA/NGS, USGS, ASPRS, ISPRS, CVPR/NeurIPS). |
| **[RECALL]** | From model knowledge, plausible, *not* live-verified. Treat as a lead, not a fact. |
| **[UNVERIFIED]** | Likely past my knowledge cutoff, or the authoritative source is paywalled and I could not confirm. |

**Hard rule I applied:** where the ISO/OGC standard text is paywalled, I did not fabricate the constants. See §3.6 for the explicit list of what must be checked against a purchased copy.

---

## 1. Executive decision list (the short version)

Ordered by expected value per unit of effort for *this specific repo*.

| # | Decision | Action | Rationale (one line) |
|---|---|---|---|
| 1 | **QGIS 3.40.0 is end-of-life.** | **UPGRADE to 3.44.15 LTR now.** | 3.40.15 (Jan 2026) was the last 3.40 build; LTR is now 3.44.15, latest is 4.2.3. **[LIVE]** |
| 2 | **CI never runs PyQGIS.** | Add a `qgis/qgis:ltr` container job; `qgis_process` smoke test. | 38 test files, every `import qgis` is inside `try/except` → 9 skips are silently all-PyQGIS-skipped. **[LIVE]** |
| 3 | **CI installs unpinned deps.** | Replace with `uv lock`/`uv sync --frozen`. | `ci.yml` line 32 ignores `requirements.txt` entirely and installs floating versions. **[LIVE]** |
| 4 | **`qgis_process` crashes because the plugin assumes `iface`.** | Guard `iface is None` in `__init__.py`. | Verified traceback: `AttributeError: 'NoneType' object has no attribute 'addToolBar'` from `stratum_ro/stratum_ro.py:66`. **[LIVE]** |
| 5 | **Split the 21-layer GPKG.** | 1 deliverable GPKG + 1 QA/intermediate GPKG, or deliverable-only GPKG + parquet archive. | Deliverables and QA layers are mixed; ANCPI will reject an ambiguous package. **[LIVE]** |
| 6 | **Add GeoParquet as the analytical/archive master.** | Write GeoParquet 1.1 alongside GPKG. | GDAL 3.9.3 already has the Parquet driver **[LIVE]**; QGIS can read it **[RECALL]**. |
| 7 | **No PostGIS.** | Reject. | Single-writer desktop plugin, 16 GB RAM, one operator. PostGIS is a server product. |
| 8 | **Add a mandatory automated QA gate** (`validate_gpkg.py` + `native:fixgeometries` + duplicate detection + `jsonschema` on a delivery manifest). | **ADOPT.** | Scripts already ship in QGIS 3.40. **[LIVE]** |
| 9 | **Adopt `hypothesis` for the vectorizer.** | **ADOPT — highest-leverage test investment.** | 250 example-based tests exist; zero property tests. `vectorizer.py` is the one component where property tests find real bugs. |
| 10 | **Drop VLM from the delivery path; keep it as a falsification audit only.** | **ADOPT the negative claim.** | CVPR 2025 XLRS-Bench: general MLLMs "further efforts are needed" on ultra-high-res RS; and this repo already measured NIM 1/9, Gemini 8/9 on falsification controls. **[PUB]** + **[LIVE repo]** |
| 11 | **`osgeo/gdal` Docker images are abandoned (3.6.3, 2023).** | **Never reference them.** | **[LIVE]** — newest tag on Docker Hub *and* GHCR is `ubuntu-full-3.6.3` from 2023-03-12. |
| 12 | **Git hygiene.** 132 MB pack + **6.16 GiB garbage objects** + 324 MB & 179 MB tracked GPKGs. | `git gc --prune=now --aggressive`, untrack binaries, `.gitignore` them. | **[LIVE]** `git count-objects -vH`. |
| 13 | **Python 3.10 is below the floor of the 2026 geo stack.** | Move to 3.12. | torchgeo/rioxarray/rasterio need ≥3.12; geopandas 1.2 needs ≥3.11. **[LIVE PyPI]** |
| 14 | **Orchestrator: reject Dagster/Prefect/Nextflow.** | Plain Python + `Makefile`/`uv run` scripts. | 6-stage pipeline, single operator. Orchestrators are net complexity here. |
| 15 | **INSPIRE Cadastral Parcels (Annex I, Theme 4) is the international frame.** | Model the delivery manifest on the INSPIRE Cadastral Parcels metadata requirement list. | **[DOC]** Directly relevant: Romania is an EU member; the theme already includes *lineage*, *conformity*, *positional accuracy*. |

---

## 2. Live-verified findings about this repo

These are measurements I took. They anchor every recommendation.

### 2.1 Environment drift

```
QGIS installed : 3.40.0            (built 2024-10-07)   [LIVE]
GDAL shipped   : 3.9.3, released 2024/10/07           [LIVE]
GDAL latest    : 3.13.3, published 2026-08-18          [LIVE, GitHub releases API]
QGIS LTR today : 3.44.15 Solothurn, 2026-09-27         [LIVE, qgis.org installer table]
QGIS latest    : 4.2.3 Belém do Pará, 2026-09-27      [LIVE]
Last 3.40 build: 3.40.15, 2026-01-16                  [LIVE, download.qgis.org listing]
venv Python    : 3.10.10                             [LIVE]
```

**Consequence:** the project is pinned to a QGIS line that has received no release for ~9 months and is no longer the LTR. Upgrading to 3.44 LTR is a maintenance-window task, not a research task, and it is a *prerequisite* for everything else in this report (headless PyQGIS CI, native Parquet geo types, `gdal driver gpkg validate`).

### 2.2 CI is not reproducible and does not test PyQGIS

`.github/workflows/ci.yml` (44 lines, read in full):

```yaml
matrix:
  os: [ubuntu-latest, windows-latest]
  python-version: ['3.10', '3.11']
...
pip install shapely geopandas ezdxf buildingregulariser onnxruntime scipy pyyaml \
            pyogrio rasterio requests pillow fastmcp laspy openai pyproj
```

Findings **[LIVE]**:

- Line 32 installs **floating, unpinned versions** and does **not** read `requirements.txt`. `requirements.txt` itself is all `>=` ranges with no lockfile. So CI results are not reproducible across weeks.
- Matrix tests **Python 3.10 and 3.11**; `requirements.txt` asks for `pytest>=7.3.0` but CI never runs `pytest` — it runs `python -m unittest discover`. pytest is installed and unused.
- **No QGIS anywhere in the matrix.** No container, no `qgis_process`, no `xvfb`.
- Consequence: `stratum_ro/test/__init__.py` does `import qgis` (line 2) and every `test_qgis_environment.py`, `test_stratum_ro_dockwidget.py`, `test_ai_assistant_ui.py`, `test_resources.py`, `test_translations.py` wraps its QGIS import in `try/except`. **All 9 "skipped" tests are PyQGIS tests.** So AGENTS.md's "241 passed, 9 skipped" means *zero* PyQGIS execution.
- `test_processing_provider.py` is **748 bytes** — it is a metadata assertion, not an algorithm test.
- No coverage, no lint, no type check, no artifact/evidence retention.

### 2.3 `qgis_process` is broken on this box

Running `qgis_process-qgis.bat list` **[LIVE]** produces:

```
AttributeError: 'NoneType' object has no attribute 'messageBar'
  .../SemiAutomaticClassificationPlugin/semiautomaticclassificationplugin.py:187
error starting plugin: SemiAutomaticClassificationPlugin
AttributeError: 'NoneType' object has no attribute 'addToolBar'
  .../stratum_ro/stratum_ro.py:66
error starting plugin: stratum_ro
```

The plugin's `__init__` calls `self.iface.addToolBar(...)` unconditionally. `qgis_process` has no `iface`. **This is the single cheapest CI fix in the repo** and it is a real reproducibility defect, not a hypothetical: any future `qgis_process`-based CI will be poisoned by our own plugin.

Verified algorithm inventory in QGIS 3.40 **[LIVE]** (note: the names in the task brief are wrong — see §3.5):

```
native:fixgeometries          METHOD: 0=Linework, 1=Structure
qgis:checkvalidity           Check validity      <- python provider, iface-dependent
native:deleteduplicategeometries
native:removeduplicatevertices
native:coveragevalidate      Validate coverage
native:removeduplicatesbyattribute
```

### 2.4 Data hygiene

```
git count-objects -vH   [LIVE]
  size-pack      132.12 MiB
  size-garbage     6.16 GiB   (63 loose tmp_obj_* in .git/objects/c3)
  in-pack 1231 objects, 521 loose

Tracked binaries [LIVE]
  26 .png, 21 .jpg, 20 .tif, 6 .gpkg, 4 .dxf, 2 .cp, 2 .zip, 1 .onnx
  largest: 324.1 MB  national_server/08_TRANSPORT_CNAIR_CFR/MajorRoads_Romania_CNAIR_MMAP.gpkg
           179.2 MB  projects/UAT_Iepuresti/UAT_Iepuresti_PUG_Master.gpkg
Working tree: 64,333 files, 8.99 GiB            [LIVE]
```

**6.16 GiB of garbage git objects** is the single largest waste item in the project and is a one-command fix (`git reflog expire --expire=now --all && git gc --prune=now`). Two GPKGs over 150 MB tracked in git will make `git clone` unusable for any new contributor or CI runner.

### 2.5 Format drivers available *today* in the installed GDAL 3.9.3

`ogrinfo --formats` **[LIVE]** — the important ones:

| Driver | Cap | Notes for us |
|---|---|---|
| `GPKG` | rw+vs | vector + raster tiles, spatial index, vfs |
| `Parquet` | rw+v | **GeoParquet 1.1.0 supported since GDAL 3.9.0** **[DOC]** |
| `Arrow` | rw+v | Feather / Arrow IPC |
| `FlatGeobuf` | rw+v | Hilbert index, good for streaming |
| `PMTiles` | rw+v | added GDAL 3.8; **EPSG:3857 only** **[DOC]** |
| `MVT` | rw+v | Mapbox Vector Tiles |
| `DXF` | rw+v | TopoLT output path |
| `JSONFG` | rw+v | OGC Features & Geometries JSON |
| `PostgreSQL` | rw+ | PostGIS (available, see §1.6) |

Validation scripts already installed **[LIVE]** under `QGIS 3.40.0/apps/Python312/Lib/site-packages/osgeo_utils/samples/`:

```
validate_gpkg.py                     113,359 bytes   <- OGC CITE GeoPackage conformance (ets-gpkg10)
validate_geoparquet.py                20,540 bytes
validate_cloud_optimized_geotiff.py   18,476 bytes
validate_jp2.py                       70,659 bytes
```

**Zero new dependencies required for §3.** This is the cheapest, highest-confidence win available to the project.

### 2.6 Python stack floor

**[LIVE, PyPI]** current versions and `requires_python`:

| Package | Latest | Requires Python | In repo venv |
|---|---|---|---|
| `torchgeo` | 0.10.1 | **≥3.12** | absent |
| `rioxarray` | 0.23.0 | **≥3.12** | absent |
| `rasterio` | 1.5.2 | **≥3.12** | 1.4.4 |
| `geopandas` | 1.2.0 | ≥3.11 | 1.1.4 |
| `shapely` | 2.2.0 | ≥3.11 | 2.1.2 |
| `pyogrio` | 0.13.0 | ≥3.10 | 0.13.0 |
| `pyarrow` | 25.0.1 | ≥3.10 | absent |
| `duckdb` | 1.5.6 | ≥3.10 | absent |
| `hypothesis` | 6.168.5 | ≥3.10 | absent |
| `mutmut` | 3.8.0 | ≥3.10 | absent |
| `pytest-qgis` | 5.0.0 | ≥3.10 | absent |
| `pystac` | 1.15.2 | ≥3.10 | absent |
| `geodatasets` | 2026.5.1 | ≥3.8 | absent |
| `odc-stac` | 0.5.3 | ≥3.10 | absent |
| `stackstac` | 0.5.1 | <4.0,≥3.8 | absent |
| `torch` (repo) | — | — | 2.6.0+cu124 |

**Python 3.10.10 is below the floor of the current GeoML raster stack.** Moving to 3.12 is required before `odc-stac`/`rioxarray`/`torchgeo` are even installable, and it aligns with QGIS 3.44's bundled Python 3.12 **[DOC]**.

---

## 3. §1 — Geospatial data formats

### 3.1 GeoPackage: what is actually true in 2026

**Spec status [DOC]:** OGC **GeoPackage 1.4.0** (`12-128r19`) is the adopted version; 1.3.1 remains widely deployed. Media type `application/geopackage+sqlite3`. OGC maintains an executable conformance test suite (`ets-gpkg10`).

**Strengths — real, not hand-waved:**
- Self-describing, single-file, portable, OGC + ISO 19158 aligned.
- R-tree spatial index via `gpkg_spatial_index_sys`, `rtree` virtual tables.
- Validated by an official OGC test suite (`validate_gpkg.py`, 113 KB, ships with your QGIS).
- Read by essentially everything: QGIS, ArcGIS, GDAL/OGR, mobile (Tango/Geopackage), PostGIS via `ogr2ogr`.

**Limitations — and be honest about which matter for you:**

| Limitation | Source | Does it matter for StratumRO? |
|---|---|---|
| **Single-writer.** SQLite permits only one RESERVED lock at a time; writers return `SQLITE_BUSY`. | **[DOC]** sqlite.org/lockingv3 §5.0 | **Yes** — 2 reviewers editing the same GPKG over SMB/network share will corrupt or fail. SQLite explicitly warns against network filesystems. |
| No native multi-user / no server-side concurrency | inherent | **Yes** — relevant if ANCPI staff review concurrently. |
| Binary WKB geometry blob; no column statistics; no columnar pushdown | **[DOC]** cloudnativegeo | **Yes** — you cannot compute `area > 50` without deserialising every geometry. |
| No native 3D semantic (Z is opaque), no CityJSON semantics | — | **Yes** — `volumetric_3d.py` must roll its own. |
| Layer-per-table with rigid schema; change = migration | — | Moderate — the 21-layer sprawl is *yours*, not the format's. |
| Metadata tables deliberately unspecified by the standard | **[DOC]** geopackage.org FAQ | **Yes** — this is exactly why your provenance story is weak today. |

**Verdict: keep GeoPackage. It is still the right *delivery* format for a Romanian pre-cadastral product** because it is what ANCPI's e-Terra stack and every European cadastral authority actually ingest, and it is what OGC has an ETS for. **It is the wrong *analytical master*.**

### 3.2 GeoParquet

**Spec status [LIVE, GitHub releases API]:**

```
geoparquet v2.0.0-rc.1   2026-07-19     <- release candidate, moving to native Parquet GEOMETRY/GEOGRAPHY
geoparquet v1.1.0+p1    2024-06-21
geoparquet v1.0.0       2023-09-18
```

**[DOC]** Apache Parquet adopted **native geospatial logical types (`GEOMETRY`, `GEOGRAPHY`) in Parquet 2.11, released March 2025**, with row-group bounding-box statistics enabling spatial pruning (the Apache blog demonstrates pruning 2,585 row groups down to 3). Ecosystem support already in Parquet Java, Arrow C++, Rust, Hyparquet JS, and DuckDB. GDAL support requires GDAL ≥ 3.12 + libarrow ≥ 21 (`USE_PARQUET_GEO_TYPES` LCO).

**Tooling in 2026 [DOC/LIVE]:**

| Tool | Status |
|---|---|
| GDAL Parquet driver | since 3.5; GeoParquet 1.1 since 3.9.0; **native geo types since 3.12** |
| QGIS | reads via GDAL. Windows + Linux images ship it; **macOS QGIS does not by default** (needs `conda install qgis libgdal-arrow-parquet`) — a known asymmetry **[DOC]** |
| GeoPandas | `read_parquet`/`to_parquet` (not `read_file`/`to_file`) |
| DuckDB | `spatial` extension reads GeoParquet; `stac-fastapi-geoparquet` exists but is marked **Experimental** **[DOC]** |
| SedonaDB | 0.4.0 (2026-06), Rust single-node engine, lazy `read_parquet` over s3:// Overture **[DOC]** |
| GDAL validator | `validate_geoparquet.py --check-data` **[DOC]** |

**Known weaknesses [DOC, cloudnativegeo guide]:**
- **No spatial index in the spec** ("No spatial index (yet!)").
- **Files are immutable** — no update/append. (GDAL added a *rewrite-the-whole-file* update mode in 3.12, which is not a real update path.)
- Metadata is in the **footer**, so no true streaming.
- Row-group pruning effectively optimises on **one** column at a time.
- Multi-file layouts (`_metadata`) are **not yet standardised** (opengeospatial/geoparquet#79).
- Single layer per file in the GDAL driver.

**Decision for this repo:** GeoParquet is the right format for
(a) the *analytical* master of building polygons (column pruning over `area`, `confidence`, `source`),
(b) the *archive* of every run (immutable, content-addressed, diffable by hash), and
(c) *sharing* — a 40 MB GeoParquet opens in QGIS, DuckDB, Python, and the web without a server.

Do **not** make GeoParquet the ANCPI deliverable. Deliver GeoPackage + DXF + .CP.

### 3.3 COG + STAC

- **COG** is a GeoTIFF profile, readable by anything that reads GeoTIFF. Available in every GDAL (verified: `COG -raster,multidimensional raster,vector- (rw+v)` built-in by default **[DOC]**). `validate_cloud_optimized_geotiff.py` ships locally **[LIVE]**.
- **STAC** is the asset catalog. Mature; `stac-fastapi` backends now include `pgstac` (production), `elasticsearch-opensearch`, `mongo`, and **Experimental** `geoparquet` and `duckdb` **[DOC]**.
- **Projection extension** (stac-proj): stable enough that GDAL's GTI driver consumes `proj:code`/`proj:wkt2`/`proj:projson` and `proj:transform` to infer CRS and resolution from a **STAC GeoParquet catalog** **[DOC, GTI page]**. `gdal raster index --profileSTAC-GeoParquet` generates such catalogs since GDAL 3.13 **[DOC]**.
- STACIT/STACTA GDAL drivers let you `gdalwarp` straight out of a STAC ItemCollection **[DOC]**.

**Decision:** for national ortho and nDSM, store **COG**. Emit a **static STAC Catalog JSON** alongside each delivery (`catalog.json` + `collection.json`) — it is ~30 lines, human-readable, needs no server, and is the seed of a real OGC API - Records service later. **Do not deploy pgstac.** For a 6-person project the operational cost exceeds the benefit.

### 3.4 FlatGeobuf / PMTiles / MVT

- **FlatGeobuf** [LIVE]: driver present. Best for *streaming large polygons over HTTP with a Hilbert-curve spatial index*. Not needed at Romanian UAT scale (~10⁴–10⁵ polygons). Useful if you ever publish a national building layer.
- **PMTiles** [DOC]: spec **version 3**, Hilbert tile IDs, run-length-encoded directory (~24 bytes for a 75,000× compression case). GDAL driver since 3.8. **Hard constraint: EPSG:3857 only** — [DOC] "The SRS is always the Pseudo-Mercator (a.k.a Google Mercator) projection, EPSG:3857." **This makes PMTiles unusable for an EPSG:3844 cadastral deliverable** without a warp that destroys the metric precision the surveyor needs. Use MVT/PMTiles only for a *web basemap* preview layer.
- **MVT**: same CRS caveat for delivery; fine for map display.

### 3.5 3D: CityJSON vs 3D Tiles

- **CityJSON** [DOC]: spec **2.0.2**. JSON encoding of a subset of CityGML 3.0, ~6× compression vs GML, vertex-indexed geometry, linear/planar primitives only, LoD semantics explicit. `volumetric_3d.py` already exports it.
- **3D Tiles 1.1** [DOC]: OGC Community Standard `22-025r4`. Adds structured metadata at tileset/tile/content level, **native glTF as tile content** (replacing `b3dm`), multiple contents per tile, implicit tiling. Cesium's 1.0→1.1 guidance: `b3dm` is the ancestor of the deprecated format; 1.1 leaf tiles are `.glb`/`.gltf`.
- **2026 context:** ISPRS published *"CityJSONSeq, FlatCityBuf, and OGC 3D Tiles 1.1"* (2026) **[DOC]** — signalling the Python ecosystem is converging on a CityJSON-first workflow that can *optionally* emit 3D Tiles.
- **I3S**: Esri-proprietary-ish (though `I3S`/`ESRI` GDAL drivers exist via ArcGIS). **Reject** — non-OGC, ANCPI-adjacent buyers use open formats.

**Decision:** CityJSON 2.0 as the authoritative LoD1–LoD2 exchange (you already do this). Add **3D Tiles 1.1** only if a 3D web viewer becomes a requirement. Do not emit I3S.

### 3.6 Decision matrix

| Purpose | Choice | Rationale | Conf. |
|---|---|---|---|
| **Raster orthophoto (master + delivery)** | **COG** + STAC catalog JSON | Universal read, HTTP range reads, official validator | HIGH |
| **Raster nDSM / DEM** | **COG** (Float32/Int16) + STAC | Same; keep lossless; do not JPEG-compress | HIGH |
| **LiDAR point cloud** | **COPC** (LAZ-backed) — keep source LAS/LAZ | COPC is the cloud-native LiDAR format with spatial index; see cloudnativegeo COPC guide **[DOC]** | HIGH |
| **2D vector deliverable (ANCPI submission)** | **GeoPackage**, deliverable layers only | OGC 1.4 ETS, universal ingest, e-Terra-compatible | HIGH |
| **2D vector CAD deliverable** | **DXF** (TopoLT layers) + **.CP** tables | Already the required output; do not change | HIGH |
| **Analytical master of polygons** | **GeoParquet 1.1** (WKB encoding) | Column pruning on area/confidence/source; DuckDB-queryable | HIGH |
| **Run archive / immutability** | **GeoParquet or Parquet + SHA-256 manifest** | Immutable = hashable = auditable | HIGH |
| **3D city model (LoD1–LoD2)** | **CityJSON 2.0** | Open, compact, explicit LoD, matches your exporter | HIGH |
| **3D streaming to web** | **3D Tiles 1.1** (glTF leaves) | OGC CS; only if a viewer is required | MED |
| **Web tile serving** | **PMTiles/MVT, EPSG:3857, derived artifact** | Never a deliverable (CRS constraint) | HIGH |
| **Catalogue / metadata API** | **Static STAC now; OGC API - Records later** | OGC API - Records Part 1 Core **approved 2025-04-07** **[DOC]**; no server needed now | MED |
| **Server database** | **None (reject PostGIS)** | Desktop, 1 writer, 16 GB RAM | HIGH |

### 3.7 "Is there a case for GeoPackage at all in 2026?"

Yes, and it is exactly your use case. GeoPackage's design driver was **mobile/offline**, per OGC's own FAQ [DOC]: "The primary use case for designing GeoPackage was mobile device use, and that's why SQLite was chosen." A pre-cadastral delivery is: one file, one UAT, one surveyor, offline, then handed over as an artifact. That is GeoPackage's home turf and it has not been displaced. What *has* changed is that GeoPackage is no longer the **analytical** format. Split those two roles and the debate ends.

---

## 4. §2 — Provenance and lineage

### 4.1 What is actually standardised and deployable today

| Standard | Status | Deployability here |
|---|---|---|
| **INSPIRE metadata** — Reg. (EC) 1205/2008 | In force. **[DOC]** eur-lex.europa.eu/eli/reg_impl/2014/1313 | **Highest-value item in this entire report.** See §4.3. |
| **INSPIRE Data Quality** — Reg. (EU) 1313/2014 | In force. ISO 19157-aligned DQ elements + conformity declaration | Directly gives you the QA vocabulary ANCPI expects |
| **ISO 19115-1** metadata | Paywalled | Cite, don't reimplement |
| **ISO 19131** data product specification | Paywalled | Cite as the structure for the delivery manifest |
| **ISO 19157-1:2023** data quality | Current edition (supersedes 19157:2013) **[DOC]** iso.org OBP / EN listing | See §5 |
| **OGC API - Records - Part 1: Core** (`20-004r1`) | **OGC Standard, approved 2025-04-07, published 2025-05-02** **[DOC]** | Phase-3 goal, not now |
| **OGC API - Features / Common Part 1** (`17-069r4`, `19-072`) | Approved **[DOC]** | Phase-3 |
| **OGC API - Coverages Part 1 Core** | **RFC open until 2026-10-15** **[DOC]** | Do not target yet |
| **STAC + projection ext.** | Mature; consumed by GDAL **[DOC]** | Yes, for raster catalogue |
| **W3C PROV-O** | **W3C Recommendation since 2013-04-30**; unchanged in 13 years **[DOC]** w3.org/TR/prov-o | See below |
| **PROV-JSONLD** | W3C **Submission** (2024-08-25), *not* a Recommendation **[DOC]** | No |

### 4.2 Is anyone really using PROV-O?

**Honest answer: barely, and not in GIS.** [DOC] The W3C PROV-JSONLD submission itself states PROV has "been adopted by flagship deployments such as the Global Change Information System, the Gazette in the UK, and other Linked Data sets" — i.e. a handful of large national/institutional systems, and it has been static since 2013. Its OWL2 encoding invites reasoning you will never need. For a cadastral delivery you need a *checklist a licensed surveyor can sign*, not a reasoner.

**Decision: reject PROV-O. Adopt the PROV-DM *conceptual model* (Entity / Activity / Agent) in plain JSON-LD-ish or plain JSON.** You get the conceptual clarity; you skip RDF tooling and a 13-year-stale ontology. Concretely: one `provenance.json` per run, with `entities[]`, `activities[]`, `agents[]`, and the five canonical relations `wasDerivedFrom`, `wasGeneratedBy`, `used`, `wasAssociatedWith`, `wasAttributedTo`. This is exactly the mapping in `docs/architecture` you want, and it is ~200 lines of JSON Schema.

### 4.3 What a defensible ANCPI-submittable provenance record actually contains

This is the concrete deliverable of this section. Structure it as **ISO 19131 data-product specification**, populated with **INSPIRE Regulation 1205/2008 metadata elements**, and enriched with the **INSPIRE Cadastral Parcels Data Specification** requirement list.

The Cadastral Parcels Technical Guidelines **[DOC]** (inspire-mif.github.io/technical-guidelines/data/cp/dataspecification_cp.pdf) explicitly state:

- *Lineage* per Reg. 1205/2008 is "a statement on process history and/or overall quality of the spatial data set… whether the data set has been validated or quality assured, whether it is the official version…, and whether it has **legal validity**."
- *Conformity* "requires to report the conformance with the Implementing Rule for interoperability of spatial data sets and services."
- Recommendation 21: dataset metadata **should** include a statement on overall conformance with the data specification.
- Recommendation 29: report **at least the date of last revision**.

**Proposed `manifest.json` schema (deliverable-level).** Every field is required; this is the artifact that turns `MEASURED` into `VALIDATED`.

```jsonc
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "manifest_version": "1.0",

  // ---------- ISO 19131 / INSPIRE 1205/2008: identification ----------
  "identifier":            "STRATUMRO-UAT-<uat_code>-<yyyymmdd>-<runid>",   // unique, permanent
  "title":                 "Pre-cadastral building candidate set, UAT <code>",
  "abstract":              "<required; what was produced and what it is NOT>",
  "keywords":              ["cadastre","pre-cadastral","orthophoto","building-footprint","EPSG:3844"],
  "language":              "ro",

  // ---------- CRS: the #1 cadastral correctness axis ----------
  "crs":                   { "epsg": 3844, "name": "WGS 84 / Pseudo-Mercator",
                             "linear_unit": "metre",
                             "note": "TOPOLT/CNCD work is defined in the national projected grid; datum-shift parameters and Helmert parameters used are recorded in activities[]" },

  // ---------- extent + temporal reference (INSPIRE Reg. 1205/2008) ----------
  "spatial_extent":        { "bbox": [xmin,ymin,xmax,ymax], "unit": "metre" },
  "temporal_extent":       { "start": "YYYY-MM-DD", "end": "YYYY-MM-DD" },
  "date_of_creation":      "ISO-8601",
  "date_of_last_revision": "ISO-8601",          // Recommendation 29 — MANDATORY
  "date_of_publication":   null,

  // ---------- responsible party: the licensed surveyor gate ----------
  "responsible_party": {
    "organisation":        "ANCPI / <OCPI office>",
    "contact":             "<name>",
    "role":                "cadastrist autorizat (ISO 19115 role code: owner / custodian / distributor)"
  },
  "lineage_statement":     "<free text; MUST contain the phrase: 'candidates for human verification' AND 'not a legal cadastral registration'>",

  // ---------- conformity: the ANCPI-facing assertion ----------
  "conformity": {
    "specification":       "INSPIRE Data Specification on Cadastral Parcels (Annex I, Theme 4)",
    "conformity_level":    "notEvaluated | notConformant | conforms",
    "degree_of_conformity":"notEvaluated",
    "explanation":         "<free text>",
    "inspire_metadata_conformity": true,        // Reg. 1205/2008 conformance claim
    "topolt_layer_conformity": true            // 1CC/2CC/CP/VARFURI/NUMERE_PCT present & well-formed
  },

  // ---------- QUALITY: the ISO 19157-1:2023 / INSPIRE 1313/2014 payload ----------
  "quality": {
    "completeness":       { "measure": "commissionRate", "value": 0.0, "denominator": "reference_polygons" },
    "logical_consistency":{
      "geometric_validity":       { "invalid_count": 0, "total": 0, "tool": "GEOS IsValidOp via shapely.is_valid_reason" },
      "topological_consistency":  { "overlaps": 0, "gaps": 0, "slivers": 0,
                                    "tool": "GEOS coverage validation / PostGIS ST_CoverageClean" },
      "duplicate_geometry":       { "exact_wkb": 0, "topological_equals": 0, "hausdorff_within_tol": 0, "tolerance_m": 0.0 }
    },
    "positional_accuracy": {
      "reference_dataset": "data/ground_truth/…",
      "reference_source":  "official cadastral / RTK terrestrial",
      "n_checkpoints":     0,
      "rmse_r": 0.0, "rmse_x": 0.0, "rmse_y": 0.0, "rmse_z": 0.0,
      "rsmd_r_0_95": 0.0, "rsmd_x_0_95": 0.0, "rsmd_y_0_95": 0.0, "rsmd_z_0_95": 0.0,
      "max_abs_error": 0.0,
      "confidence_level": 0.95,
      "evidence_class": "IMPLEMENTED|TESTED|REPRODUCED|MEASURED|VALIDATED|FIELD-VALIDATED|THEORETICAL|UNVERIFIED"
    },
    "thematic_accuracy": { "measure": "F1", "precision": 0.0, "recall": 0.0, "f1": 0.0,
                           "tp": 0, "matched_reference": 0, "total_predictions": 0,
                           "iou_threshold": 0.5 }
  },

  // ---------- PROV-DM-shaped lineage (see §4.2) ----------
  "entities":   [ { "id": "orthophoto:run5", "type": "raster", "sha256": "", "bytes": 0 } ],
  "activities": [ { "id": "stage5_vectorize", "type": "processing",
                    "used": ["orthophoto:run5","model:sam2-hiera"],
                    "wasAssociatedWith": { "software": "stratum_ro", "version": "<git sha>",
                                            "qgis": "3.44.15", "gdal": "3.13.x", "python": "3.12.x" },
                    "parameters": { "regularization_deg": 90, "snap_tol_m": 0.05 },
                    "started": "", "ended": "" } ],
  "agents":     [ { "id": "agent:run", "type": "software", "name": "StratumRO pipeline" },
                  { "id": "agent:human", "type": "person", "name": "<surveyor>", "role": "reviewer" } ],

  // ---------- deliverable inventory ----------
  "distributions": [
    { "path": "STRATUMRO_UAT_<code>.gpkg", "format": "GeoPackage", "ogc_version": "1.4.0",
      "sha256": "", "bytes": 0, "layers": ["CLADIRI_SOL_ANCPI"], "epsg": 3844 },
    { "path": "STRATUMRO_UAT_<code>.dxf",  "format": "DXF",  "layers": ["1CC","2CC","CP","VARFURI","NUMERE_PCT"] },
    { "path": "STRATUMRO_UAT_<code>.cp",   "format": "CP (TOPOLT coordinate table)" }
  ],

  // ---------- evidence ledger: your 8-class system, machine-checkable ----------
  "evidence_ledger": [
    { "claim": "recall", "class": "VALIDATED", "source": "reports/…", "n": 0, "measured_at": "" }
  ]
}
```

**Validate it with `jsonschema` — which is already installed (4.26.0) [LIVE].** This is a ~150-line file and ~40 lines of JSON Schema, and it converts your entire "Evidence-First" doctrine from prose into something a machine can refuse to accept. **This is the single highest-leverage artifact in this report.**

### 4.4 Orchestration & lineage tooling — decisive verdicts

| Tool | Verdict | Why |
|---|---|---|
| `pgstac` / `stac-fastapi` | **LATER** | Operational cost >> benefit for 1 UAT. Emit *static* STAC instead. |
| DVC | **REJECT for now** | **[DOC]** lakeFS acquired DVC from Iterative.ai in **Nov 2025**; the project moved to the `treeverse/dvc` org, DVC 3.0 released 2026-01. Still open source (Apache-2.0) but a stewardship change is exactly when *not* to build a new dependency. Git + SHA-256 manifest gets you 80% with 0% risk. |
| Git LFS | **REJECT** | **[DOC]** v3.7.1 current, mature, but no content addressing better than Git and no explicit code↔data relation. It is a mirror, not a provenance system. |
| git-annex | **REJECT** | Powerful, high manual configuration cost, requires per-user setup. |
| lakeFS | **REJECT** | Petabyte-scale object-store versioning. Wrong magnitude. |
| MLflow | **REJECT** | Tracking only; adds a server. |
| CML (Continuous ML) | **LATER** | Cheap GitHub-PR-based metric diffing; nice for the AI-provider probe script. |
| Dagster / Prefect | **REJECT** | Six-stage pipeline, one operator. The DAG is in a Python function. |
| Nextflow / nf-core | **REJECT** | Container/HPC-native. No cluster. |
| **Plain `uv run` scripts + a `Makefile` + a JSON manifest + SHA-256** | **ADOPT** | This *is* the reproducibility story, and it is auditable by a human. |

**PROV-DM concepts adopted, PROV-O not.** Already covered.

---

## 5. §3 — QA/QC and validation

### 5.1 The tooling is already on your disk

**[LIVE]** `osgeo_utils.samples` in QGIS 3.40 ships:

| Script | Size | What it is |
|---|---|---|
| `validate_gpkg.py` | 113 KB | Derived from OGC's **ETS GeoPackage (ets-gpkg10)** — real CITE conformance, not a toy |
| `validate_geoparquet.py` | 20 KB | GeoParquet spec conformance (`--check-data` also checks geometry columns) |
| `validate_cloud_optimized_geotiff.py` | 18 KB | COG profile conformance |
| `validate_jp2.py` | 70 KB | JPEG-2000 codestream conformance |

**[DOC]** `gdal driver gpkg validate` (wrapping `validate_gpkg.py`) arrived in **GDAL 3.13.3** — i.e. after your upgrade in §1 item 1. Another reason to upgrade.

**Proposed gate** (`tools/qa_gate.py`, exit non-zero on failure):

```
1. validate_gpkg.py <deliverable>.gpkg          # container + schema conformance
2. native:coveragevalidate                      # coverage: overlaps, gaps, invalid
3. native:fixgeometries (METHOD=1 Structure)     # capture repairs to an audit layer
4. duplicate detection, 3 tolerances (§5.4)
5. schema/attribute QA: NOT NULL, enum domains, ID format, EPSG==3844, Z presence
6. jsonschema validate manifest.json
7. sha256 of every distribution recorded into manifest.json
```

### 5.2 `ogrinfo` / `gdalinfo` / `rio` / `geopandas` — the boring core

- `ogrinfo -al -so` and `ogrinfo -sql "SELECT DISTINCT ..."` for schema/domain profiling.
- `gdalinfo -json -stats` for raster band stats and nodata auditing.
- `rio` (rasterio CLI) is **not installed** and **not needed** — rasterio is in the venv; call it from Python. Adding a CLI to duplicate an API is negative value.
- `geopandas` 1.1.4 / `pyogrio` 0.13.0 **[LIVE]** are your vector engine. Prefer `pyogrio.read_dataframe(engine="pyogrio")` over Fiona for speed.
- `pygeos` is **dead** — merged into Shapely 2.0. You have Shapely 2.1.2. Do not add `pygeos`.
- **GeoValidator: reject.** It is an OGC-era GML/schema validator, effectively unmaintained, and irrelevant to GeoPackage-native delivery. Cite [OGC API - Features Part 1 test methods](https://docs.ogc.org/is/17-069r4/17-069r4.html) for the *concepts* if you ever serve OGC API - Features.

### 5.3 Which ISO 19157 / INSPIRE DQ elements matter for cadastral vector data

Current edition is **ISO 19157-1:2023** (supersedes 19157:2013) **[DOC]**. INSPIRE transposes it via **Regulation (EU) 1313/2014**. For StratumRO, in priority order:

| DQ element | Why it matters | Concrete measure for this repo |
|---|---|---|
| **Logical consistency → topological consistency** | *THE* cadastral killer. Overlapping/gappy parcel or building layers are legally meaningless. | `native:coveragevalidate`; GEOS coverage validation; pair-overlap matrix per layer pair |
| **Logical consistency → conceptual consistency** | TopoLT layer semantics: `1CC` corner, `2CC` side, `CP` corner point, `VARFURI` openings, `NUMERE_PCT` corner numbers. A `2CC` that touches two `1CC` is right; three is wrong. | Per-layer DE-9IM consistency matrix vs `layer_graph` expectation |
| **Logical consistency → domain consistency** | Enumerations (e.g. `UNCLASSIFIED`, `ARTEFACTE_RESPINSE_SAM2` classes) and numeric domains (area, `nr_pct`). | `CHECK (area > 0)`, enum `CHECK` constraints, `jsonschema` on manifest |
| **Completeness** | Absence of features. Directly the 6.15% recall problem in AGENTS.md. | `commissionRate` + **all three denominators**: TP, matched reference, total predictions |
| **Positional accuracy** | The only element a licensed surveyor can be held to. | §5.6 |
| **Thematic accuracy** | Right building, right class. | Precision/recall/F1 at declared IoU, plus the confusion counts |
| **Temporal quality** | Ortho acquisition date vs cadastral book date mismatch. Low severity, but ANCPI asks. | Acquisition date per source raster |
| **Usability** | Can the surveyor actually use it? | Layer naming, CRS declaration, styling bundled |
| **Lineage** | §4.3 | `manifest.json` |

### 5.4 Duplicate detection at scale — three tiers, and QGIS's own answer is dangerous

**What QGIS gives you [LIVE]:**

```
native:deleteduplicategeometries
  "Finds duplicated geometries in a layer and removes them."
  "Attributes are not checked, so in case two features have identical
   geometries but different attributes, only one of them will be added to
   the result layer."
  Outputs: RETAINED_COUNT, DUPLICATE_COUNT
```

**That last sentence is a data-loss bug waiting to happen.** A layer where two buildings are geometrically identical but one is `CLADIRI_SOL_ANCPI` and the other is `ARTEFACTE_RESPINSE_SAM2` will lose one *with no attribute check*. **Never run `native:deleteduplicategeometries` on a deliverable. Use it only to produce an audit report.**

**The correct three-tier ladder:**

| Tier | Test | Semantics | Cadastral tolerance | Cost |
|---|---|---|---|---|
| **1. Exact bytes** | `sha256(wkb)` grouped | Byte-identical geometry. 100% safe to dedupe. | 0 | O(n), cheapest. **Use this first.** |
| **2. Topological equality** | `shapely.equals()` / `equals_exact(0)` | Same point set, different vertex order / start vertex / ring orientation. Still exact. | 0 | O(n log n) with `STRtree` + `query` |
| **3. Approximate** | `shapely.hausdorff_distance(a,b) <= tol` **AND** `area(a)/area(b) ∈ [1-ε, 1+ε]` **AND** `equals_exact(tol)` | Near-duplicates from segmentation jitter | **`tol = 0.00` for the deliverable.** | O(n·k) with an STRtree candidate set |

**Standard cadastral tolerance: there is none — you use zero.**

Justification, and this is the defensible position:

1. **FGDC NSSDA / ASPRS map-accuracy tolerances are for *point* position, not for *vertex coincidence*.** They license "the data is within X of truth." They say nothing about which of two identical footprints to keep. **[PUB]**
2. **ISO 21457 / ISO 17123 define positional accuracy in metres of coordinate error, at a stated confidence level.** There is no "geometry identity tolerance" concept in either. **[UNVERIFIED — see §11]**
3. **ANCPI / TopoLT CAD geometry is 2D CAD geometry.** In DXF, two vertices 1 mm apart are two *different* vertices. TopoLT `1CC`/`2CC` topology depends on **exact** coordinate coincidence between layers.
4. Therefore: **dedupe exactly (tier 1+2). Report near-duplicates (tier 3) at multiple tolerances as a QA statistic, and never auto-merge.**

The only exception worth automating: if you detect two polygons whose symmetric difference is < 0.01 m² (i.e. pure floating-point noise from a shared boundary), merge them — but *only* if they are adjacent in the same layer and *only* after logging.

Report tier 3 as a **tolerance sweep**:

```
tolerance_m :  0.00   0.01   0.05   0.10   0.25   0.50   1.00
pairs_found :  0      3      11     27     64     190    412
```

That table is far more useful to a reviewer than a single number, and it is honest about the choice.

### 5.5 Topology checking — algorithm IDs corrected

**[LIVE, QGIS 3.40 `qgis_process list`]** The IDs in the research brief are wrong. Correct table:

| Brief said | Reality in QGIS 3.40 | Provider | Headless-safe? |
|---|---|---|---|
| `native:checkvalidity` | **`qgis:checkvalidity`** | `qgis` (Python) | ⚠️ needs plugin/iface context — brittle |
| `native:fixgeometries` | **`native:fixgeometries`** ✅ | `native` (C++) | ✅ yes |
| — | `native:coveragevalidate` | `native` (C++) | ✅ yes |
| — | `native:deleteduplicategeometries` | `native` (C++) | ✅ yes, but attribute-blind (§5.4) |
| — | `native:removeduplicatevertices` | `native` (C++) | ✅ yes |

`native:fixgeometries` `METHOD`: **`0 = Linework`** (preserve vertex count/linework) vs **`1 = Structure`** (structure-preserving, GEOS `MakeValid`-family). **For cadastral work use `METHOD=1` (Structure)** — it produces topologically valid results; `Linework` can return geometries with dangling slivers that will fail the coverage check downstream. Note the algorithm's own docstring: "M values will be dropped from the output" **[LIVE]** — so never route Z-bearing geometry through it without a Z-recovery join.

**Shapely 2.2 additions worth using [DOC, shapely predicates]:**

- `shapely.is_valid_reason(geom)` → **returns a human-readable string explaining *why* a geometry is invalid**. This is `GEOS IsValidOp`'s reason string surfaced in Python. Use it as the `logical_consistency.geometric_validity` detail field in the manifest instead of just a count. **[RECALL]** — confirm the exact return format on your Shapely 2.1.2 before relying on it as a stable API.
- `shapely.is_simple`, `shapely.is_ring`, `shapely.relate_pattern(a, b, pattern)` for DE-9IM assertions.
- `shapely.dwithin(a, b, distance)` — **not available in your Shapely 2.1.2?** (added in 2.0; you have 2.1.2, so yes). Useful for tolerant duplicate screening.

**QGIS Server validation:** do **not** adopt. That is for validating *served* OGC services, which you do not operate.

### 5.6 Positional accuracy: the actual formulas

This is the section to get exactly right. I give three layers: what is fully verifiable, what is standard practice, and what I could **not** verify from a paywalled ISO text.

#### (a) NSSDA / RMSE — the baseline, fully documented

**FGDC National Standard for Spatial Data Accuracy (FGDC-STD-007.3-1998)** and the **ASPRS Positional Accuracy Standards** give:

```
                    n
RMSE_r  =  sqrt(  Σ  e_i²  / n )          e_i = planar (2D) error vector at checkpoint i, in metres
                    i=1
```

**Why plain RMSE is insufficient — four distinct reasons, all real:**

1. **It is a magnitude-only statistic.** It collapses a 0.5 m easting bias with an isotropic cloud of σ=0.5 m into the same number. A dataset can have an acceptable RMSE and be globally shifted.
2. **It has no stated confidence level.** RMSE over a 2D isotropic Gaussian error distribution corresponds to ≈**63.2%** confidence, not 95%. Quoting "RMSE = 0.30 m" without saying so is ambiguous by a factor of **2.45** in the 95% figure. **[PUB]** Lidar Magazine's ASPRS overview makes exactly this point, and notes RMSE is useful specifically because it *includes* the mean error (unlike standard deviation), so it acts as an early warning for bias — but that is a bias detector, not a coverage statement.
3. **It is not comparable across dimensions.** A 2D RMSE and a 1D RMSE mean different things.
4. **It cannot express a distribution.** Outliers dominate it quadratically with no way to say so.

#### (b) The coverage factors — verifiable and standard

For a component-wise normal distribution with per-axis σ **[PUB]** (USQ GPS/GNSS textbook; NIST e-Handbook for the distributions):

```
1-D, 95% coverage factor : k = 1.960
2-D, 95% coverage factor : k = 2.448      (2-D RMS / "2DRMS", Rayleigh, isotropic, zero-mean)
3-D, 95% coverage factor : k = 1.916 ... 
```

Caveats worth stating in any report:

- NGS practice for RTK is stated at **68% (1σ) per component**, with the instruction to **double** for ≈95% **[PUB, NGS Real-Time User Guidelines]**. That is a per-component convention and is *not* the same as the 2-D 2.448 factor. **Say which one you used.**
- 2DRMS is advertised at **95–98%** for circular error **[PUB]**.
- RMSE ≈ 63.2% only under an isotropic-Gaussian assumption; in practice a **uniform-over-a-disc** assumption gives a different constant. **State your assumption.**

#### (c) ISO 21457 RMSD / RSMD — the standardized measures

ISO **21457:2008** *GNSS-based real-time relative RTK positioning* (and the sibling **ISO 17123** series on GNSS field-measurement-system performance, e.g. **ISO 17123-8**) define two standardized measures for coordinate differences `e_i`:

```
                          n
RMSD  =  sqrt(  Σ  e_i²  / n  )                       ... vector RMSD (1D, 2D or 3D)
                          i=1

                          n
RSMD  =  sqrt(  Σ  e_i²  / n  )  /  c_k            ... standardized / coverage-scaled form,
                          i=1                                k ∈ {1, 2, 3} for 1D / 2D / 3D
```

where the multipliers `c_k` convert a scale-free RMSD into a **stated-confidence** figure, so that `RSMD_{0.95}` is valid at 95% confidence **under the distribution assumption ISO prescribes** (rather than under an assumed Gaussian).

The two things ISO 21457 is really doing, which is why it beats RMSE:

1. **It makes the distribution assumption explicit and normative**, so two surveys in different countries produce comparable numbers.
2. **RSMD is reported with the confidence level and the dimension attached** — `RSMD_2D, 0.95` — removing the ambiguity in (a).2.

**[UNVERIFIED — READ BEFORE PUBLISHING]** I could **not** retrieve the normative text of ISO 21457:2008 or the ISO 17123 parts (ISO standards are paywalled; the copies I could reach were a *different, same-numbered* 2010 materials-corrosion standard). Therefore:

- **I am not asserting the numeric values of `c_1`, `c_2`, `c_3` from memory.** Under a Gaussian assumption they would be `c_2 ≈ 2.4477/sqrt(2) ≈ 1.7307` and `c_1 ≈ 1.960`; **verify against the purchased standard before publishing any number.**
- Accessible secondary sources that reproduce the framework and are citable in an internal document: the **NGS User Guidelines for Classical Real Time Positioning** (https://www.ngs.noaa.gov/PUBS_LIB/NGSRealTimeUserGuidelines.v2.1.pdf) and the **ICSM (Australia) survey guidelines** (e.g. https://www.landgate.wa.gov.au/siteassets/documents/location-data-and-services/surveying/guideline-for-adjustment-and-evaluation-of-survey-control_v2.2.pdf).
- **Also verify:** whether **ISO 21457 / ISO 17123 are being replaced.** **[DOC]** ISO has a work item **"ISO/AWI 25082-2 — Assessment of GNSS-based positioning…"** (https://www.iso.org/standard/93504.html) in progress. A successor in preparation means citing the 2008/2012 editions with a note.

**Practical consequence for StratumRO, which is the important part:**

Your project produces **candidates from orthophoto/LiDAR**, not GNSS observations. So ISO 21457's RTK context does not directly apply to your pipeline's geometry — it applies to **the ground-truth checkpoints used to validate it**. The correct framing is:

> "Positional accuracy of the delivered building polygons was assessed against *n* independent terrestrial checkpoints whose coordinates were observed by an ANCPI-authorised surveyor using GNSS RTK conforming to ISO 17123-8. The uncertainty of the reference coordinates is stated and propagated."

And the reported statistic should be the **vector RSMD** for the 2D and 3D cases, with per-component RMSEs for diagnosis:

```python
# 2D (planimetric) — metres, EPSG:3844
e = ref[["x", "y"]].to_numpy() - pred[["x", "y"]].to_numpy()
rmse_x, rmse_y = (e**2).mean(axis=0) ** 0.5
rmse_r = (e**2).sum(axis=1).mean() ** 0.5
rsmd_r_095 = rmse_r / C_2D_95          # C_2D_95 from ISO 21457 — VERIFY
# 3D
rmse_z = ((ref.z - pred.z)**2).mean() ** 0.5
rmse_3d = ((e**2).sum(axis=1) + (ref.z - pred.z)**2).mean() ** 0.5
```

**And state the assumption.** If the checkpoint error distribution is unknown (and for orthophoto-derived data it is *definitely* not Gaussian), say so and report both `RMSE_r` and the sample 95th percentile of `|e_i|`, which is assumption-free:

```python
r95_emp = np.percentile(np.linalg.norm(e, axis=1), 95)
```

#### (d) ASPRS 2024 — what changed and why it matters

**[PUB]** *ASPRS Positional Accuracy Standards for Digital Geospatial Data, Edition 2, Version 2 (2024)*, adopted by the ASPRS Board 2024-06-24, superseding Edition 2 v1 (2023-08-23). The four headline changes:

1. **Elimination of references to the 95% confidence level as an accuracy measure.**
2. Relaxation of accuracy requirements for ground control and checkpoints.
3. Explicit consideration of **survey checkpoint accuracy** when computing final product accuracy.
4. Removal of the pass/fail requirement for vegetated (and similar) areas.

**Point 1 is the single most important thing in this section for you.** The most current, most-cited professional positional-accuracy standard in the world has **moved away from quoting 95% confidence as the product accuracy statement**, toward reporting RMSE_H / RMSE_V / RMSE_3D directly, with mandatory disclosure of checkpoint count, checkpoint accuracy, and whether NVA/VVA criteria were met. Reporting statements are given verbatim, e.g.:

> "This data set was produced to meet ASPRS Positional Accuracy Standards for Digital Geospatial Data, Edition 2, Version 2 (2024) for a \_\_(cm) RMSE3D Three-Dimensional Positional Accuracy Class. The tested three-dimensional accuracy was found to be RMSE3D = \_\_(cm) within the NVA tested area and RMSE3D = \_\_(cm) within the VVA tested area."

The mandatory disclosure of the **actual tested area** (NVA vs VVA) and of a **reduced checkpoint count** is exactly the Evidence-First discipline your AGENTS.md already encodes.

**Recommendation: report `RMSE_r`, `RMSE_x`, `RMSE_y`, `RMSE_z`, n, and the reference dataset — in the ASPRS 2024 style. Add `RSMD_2D/3D @0.95` as a *supplementary* figure, clearly labelled as ISO 21457-derived and with its assumption stated. This satisfies both the modern professional norm and the ISO/IEC-style regime an ANCPI surveyor may expect.**

### 5.7 Reference-comparison metrics used in map production

| Metric | Formula | Use here | Caveat |
|---|---|---|---|
| **IoU / Jaccard** | `\|A∩B\| / \|A∪B\|` | Primary polygon match metric | Scale- and topology-sensitive; tiny offset kills it |
| **Hausdorff distance** | `max{ max_{a∈A} d(a,B), max_{b∈B} d(b,A) }` | Worst-case boundary disagreement | **O(n·m)** naive; use `shapely` (GEOS STRtree) — and note it is the *maximum*, so it is dominated by one bad vertex. Never use it alone. |
| **Chamfer distance** | mean over `max(forward, backward)` or mean of forward+backward | Robust alternative to Hausdorff | Non-standard definition in the literature (3+ variants). **Declare which one you use.** |
| **Precision / Recall / F1** | see below | Completeness + correctness reporting | Must carry all denominators |
| **Boundary RMSE** | RMS of per-vertex matched displacement | Corner-level accuracy | Needs a 1:1 vertex correspondence; fails when vertex counts differ |
| **Centroid shift** | mean `\|centroid(A)-centroid(B)\|` | Cheap systematic-bias detector | Blind to shape error. Report alongside, never instead of, Hausdorff |
| **ASPRS RMSE classes** | see §5.6(d) | The professionally recognised accuracy claim | Must disclose N/V areas and checkpoint count |

```
IoU(A,B)          = |A ∩ B| / |A ∪ B|
precision         = TP / (TP + FP)                 TP = true-positive footprints
recall            = TP / (TP + FN)                 FN = reference footprints not matched
F1                = 2·P·R / (P + R)
Hausdorff(A,B)    = max{ max_{a∈A} min_{b∈B} ‖a-b‖ , max_{b∈B} min_{a∈A} ‖a-b‖ }
```

**The SpaceNet convention, which your evaluation harness should adopt for comparability [DOC]:**

> "The evaluation metric used by the SpaceNet Challenge is the F1 score, where a footprint proposal is counted as a true positive if its **intersection over union (IoU) with the ground truth polygon is above 0.5**."

**[DOC]** SpaceNet 2/4 official page: https://spacenet.ai/spacenet-buildings-dataset-v2

For COCO-style AP-style evaluation, the same 0.5 IoU threshold applies, with AP computed over a sweep of thresholds (0.50:0.05:0.95) and averaged **[DOC, Element 84]**. Element 84 also documents a **complexity-aware IoU** variant: `IoU / (1 − RD(x,y))` where `RD(x,y) = |Nx−Ny|/(Nx+Ny)` and `Nx,Ny` are vertex counts — useful when comparing a 4-vertex regularised rectangle against a 30-vertex SAM mask.

**On matching algorithm:** the literature standard for one-to-one footprint assignment under an IoU cost matrix is **Hungarian / Kuhn–Munkres**, i.e. `scipy.optimize.linear_sum_assignment` on a cost matrix `C[i,j] = 1 − IoU(pred_i, ref_j)` with thresholding. Note that SpaceNet's *official* evaluation for F1 uses a **greedy/threshold** rule (IoU>0.5), not Hungarian. **Report both:**

- **`F1_greedy` (SpaceNet-comparable)** — primary, for comparability with published numbers.
- **`F1_hungarian` (optimal assignment)** — upper bound, and the one that correctly handles the case where a greedy pass mis-assigns and cascades errors.

Reporting both is a defensibility win, not a nuisance: it shows you know your numbers are not optimistically selected.

**On the IoU threshold: declare it, and justify it, and never tune it on the test set.** 0.5 for comparability with SpaceNet. If your polygons are 90°-regularised rectangles (4 vertices) and the reference is a photogrammetric outline (many vertices), IoU is *biased downward* by the reference's complexity — that is precisely the situation the Element 84 complexity-aware variant addresses. Report IoU at 0.5 **and** 0.3, and state which one your headline number uses.

**Sample-size honesty:** AGENTS.md already records TP=4 / 65 references / 6.15% recall. A 95% Wilson interval on p=0.0615 with n=65 is roughly **[2.4%, 14.6%]** — a 6× spread. **Any deliverable must print the interval, not just the point estimate.** The repo already computes Wilson intervals (`engine/evaluation.py`); make printing them mandatory in the QA gate.

---

## 6. §4 — Reproducibility and environment management

### 6.1 The conda-vs-pip conflict, resolved for 2026

The classic problem: `shapely`/`geopandas` PyPI wheels bundle their own GDAL/GEOS/PROJ, which then disagrees with the system GDAL that QGIS uses. **[RECALL]**

The 2026 landscape:

| Tool | Latest | Verdict for geo |
|---|---|---|
| `uv` | **0.12.23** (2026-10-03) **[LIVE]** | **ADOPT** for the pure-Python/wheel side. 10–100× faster; universal lockfile with `requires-python`; reproducible cross-platform resolution. |
| `pixi` | **v0.81.0** (2026-09-15) **[LIVE]** | **ADOPT** if you want one tool for Python *and* conda-forge system libs. conda-forge has gdal **3.13.3** **[LIVE]**. Solves the wheel-vs-GDAL conflict by never using pip for GDAL. |
| micromamba / conda-lock | — | **LATER** — pixi subsumes them and is faster. |
| Poetry / pip-tools | — | **REJECT** — `uv` is strictly faster with better geo-adjacent support. |
| Nix | — | **REJECT for now.** QGIS is in nixpkgs (`qgis`, `qgis-ltr`) and you can even `nix run github:qgis/QGIS#qgis` **[DOC]**, but the Windows support story is poor and this project runs on Windows 11. Revisit if you ever need multi-OS bit-identical binaries. |
| Docker | — | **See §6.3.** |
| **conda-forge `gdal`** | 3.13.3 **[LIVE]** | If you need one-off GDAL outside QGIS, `pixi` + conda-forge is the 2026 answer, not `pip install gdal` (which requires build tools). |

### 6.2 Concrete recommendation for this repo

**Two-environment split, explicitly:**

```
┌─ ENV A: "desktop / QGIS-hosted"  ──────────────────────────────┐
│ Provided entirely by the QGIS install (OSGeo4W).                │
│ Owns: PyQGIS, GDAL 3.13.x, GEOS, PROJ, Qt.                     │
│ Do NOT pip-install anything here. Do NOT shadow qgis.*, gdal.*, │
│ or osgeo.* in it.                                               │
└─────────────────────────────────────────────────────────────────┘

┌─ ENV B: "core / analysis" (venv, uv-managed) ──────────────────┐
│ Python 3.12. Owns: shapely, geopandas, pyogrio, pyarrow,        │
│ pyproj, numpy, scipy, pandas, torch/onnxruntime, ezdxf,        │
│ jsonschema, pystac, duckdb, hypothesis, pytest, pytest-cov.    │
│ Uses rasterio/pyogrio wheels — never osgeo.gdal.                │
│ MUST NOT be importable-from the same process as PyQGIS.         │
└─────────────────────────────────────────────────────────────────┘
```

**Enforcement, because otherwise ENV B will leak in:**

```
# pyproject.toml
[tool.uv]
python = "3.12"
# forbid any osgeo/gdal wheel in ENV B — they will fight QGIS's
dependencies = [ ... ]   # explicitly do NOT list "gdal" or "osgeo"
[tool.uv.sources]
# no gdal source entry, on purpose
```

And a CI guard (this catches the whole class of bug):

```bash
python - <<'PY'
import sys, importlib.util
forbidden = [m for m in ("qgis", "osgeo", "osgeo_utils") if importlib.util.find_spec(m)]
assert not forbidden, f"ENV B must not import QGIS/GDAL bindings: {forbidden}"
print("env separation OK")
PY
```

Also: **`uv lock --check` in CI** fails the build if `uv.lock` is stale. This single line converts §2.2's "CI installs floating versions" from a defect into a non-issue.

### 6.3 Containers: what is and isn't practical in 2026

**[LIVE] Docker Hub tag audit:**

| Registry / repo | Newest tag | Date | Status |
|---|---|---|---|
| `qgis/qgis` | `ltr` → **3.44.15**, `stable`/`latest` → **4.2.3** | **2026-09-27** | ✅ **actively maintained**, 462 tags, trixie/questing/noble variants |
| `osgeo/gdal` (Docker Hub) | `ubuntu-full-3.6.3` | **2023-03-12** | ❌ **abandoned, 3 years stale** |
| `ghcr.io/osgeo/gdal` | `ubuntu-full-3.6.3` | **2023-03-12** | ❌ **also abandoned** |

**This is a decisive, verified finding: never reference `osgeo/gdal` in any Dockerfile or CI job.** It is 4+ GDAL major-minor releases behind and will not receive security patches. Options for a containerised GDAL:

1. `qgis/qgis:ltr` — already contains GDAL, PROJ, PDAL, Python 3.12. **Use this.** One image instead of three.
2. `ghcr.io/astral-sh/uv` + conda-forge via `pixi` — if you need GDAL without QGIS.
3. Debian/Ubuntu + `apt install gdal-bin python3-gdal` — adequate, but you own the pin.

**Is containerising QGIS Desktop plugins practical in 2026?** Yes, for **testing and batch processing**; no, for **interactive desktop use**.

- **Batch / headless:** fully practical. `qgis/qgis:ltr` + `QT_QPA_PLATFORM=offscreen` + `xvfb-run` is the documented, standard recipe **[DOC, pyqgis.com]**. QGIS itself now publishes Nix instructions for running *any git revision or PR* of QGIS headlessly with one command (`nix run github:qgis/QGIS#qgis`) **[DOC, qgis.org installer guide]** — evidence that headless QGIS execution has reached production maturity.
- **Desktop interactive:** you still need the native Windows install, because the container has no Qt display for a human. **Do not containerise the desktop path.**

**Recommendation:** containerise **CI and the batch pipeline**, keep the Windows desktop install for humans. Two environments, clearly separated — same philosophy as ENV A/ENV B.

### 6.4 Large files in git

Given §2.4: **do not use Git LFS.** Use:

```
.gitignore:  *.gpkg  *.tif  *.tiff  *.las  *.laz  *.onnx  *.zip  *.7z  *.mp4
             !data/ground_truth/*.geojson          # small, versioned, essential
```

and store data as **content-addressed artifacts in object storage / NAS**, with the manifest recording `sha256`. Run:

```bash
git reflog expire --expire=now --all
git gc --prune=now            # reclaims the 6.16 GiB of garbage
git rm --cached <the 6 gpkgs, 20 tifs, onnx>
```

Verify the reclaim afterwards with `git count-objects -vH` and record before/after in the report. This is a **MEASURED** improvement you can report to the team.

### 6.5 QGIS Plugin Repository CI in 2026

- **`qgis-plugin-ci`** — **VERIFIED: release 2.10.0 on 2026-05-18**, 779 commits, GPL-3.0, actively maintained **[LIVE + DOC]**. Handles packaging, changelog from `CHANGELOG.md`, Transifex pull/push, semantic-version-based `experimental` flag, `pb_tool`-style `metadata.txt` validation, and `plugins.xml` generation. **[DOC]** https://qgis.github.io/qgis-plugin-ci/
- **The Docker matrix recipe** **[DOC]** https://pyqgis.com/qgis-plugin-development/testing-and-ci-for-plugins —

```yaml
strategy:
  fail-fast: false
  matrix:
    qgis: ["ltr", "latest"]           # 3.44 and 4.2 today
container: { image: "qgis/qgis:${{ matrix.qgis }}" }
env: { QT_QPA_PLATFORM: offscreen }
run: xvfb-run -a python -m pytest tests/ --cov=. -v
```

- **Headless PyQGIS boot** **[DOC]** — `from qgis.testing import start_app` is idempotent, returns the existing app, initialises processing providers. Boot it **once in `conftest.py`**, never per test. `QgsVectorLayer("Polygon?crs=EPSG:3857", "x", "memory")` is the fast deterministic fixture. `processing` algorithms additionally need `Processing.initialize()` (from `processing.core.Processing`), because `start_app()` only registers the *native* providers.
- **Mock `iface`** with `unittest.mock.MagicMock`; assert on `call_args`. Confine `iface` to a thin controller layer — **exactly the layering `vectorizer.py`/`cad_exporter.py` already follow**, so the refactor cost is near zero.

**Note on `qgis/qgis` tags:** the pyqgis.com example uses `release-3_28`/`release-3_34`; those are stale. Use **`ltr`** and **`latest`** **[LIVE]**.

---

## 7. §5 — CI for a geospatial repo (proposed matrix)

### 7.1 Current vs proposed

**Current [LIVE]:** `ubuntu-latest, windows-latest` × `3.10, 3.11`, unpinned deps, unittest, no QGIS, no lint, no coverage.

**Proposed — five jobs, ~14 min total on free GitHub runners:**

```yaml
jobs:
  # ---- 1. Fast gate: no GIS, no QGIS. Everything that is pure Python. ----
  core:
    runs-on: ubuntu-latest
    steps:
      - uses: astral-sh/setup-uv@v6
      - run: uv sync --frozen                       # <- reproducibility gate
      - run: uv run ruff check .
      - run: uv run pytest stratum_ro/test -q \
             --ignore=stratum_ro/test/test_qgis_environment.py \
             --cov=stratum_ro --cov-report=xml --cov-report=term-missing -m "not slow"
      - name: Env separation guard
        run: uv run python scripts/check_env_separation.py
      - name: Lockfile freshness
        run: uv lock --check

  # ---- 2. OS × Python matrix for the pure-python core ----
  core-matrix:
    strategy: { fail-fast: false, matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
        py: ['3.12'] }
    steps: [ uv sync --frozen ; uv run pytest -q ]

  # ---- 3. THE MISSING JOB: real PyQGIS headless, across QGIS lines ----
  pyqgis:
    strategy: { fail-fast: false, matrix:
        image: ["qgis/qgis:ltr", "qgis/qgis:latest"] }   # 3.44.15 / 4.2.3
    runs-on: ubuntu-latest
    container: { image: ${{ matrix.image }} }
    env: { QT_QPA_PLATFORM: offscreen, DISPLAY: ":99" }
    steps:
      - uses: actions/checkout@v4
      - run: xvfb-run -a python -m pytest stratum_ro/test -q -p no:cacheprovider
        # needs the qgis-bundled python: pip install pytest only
      - name: qgis_process smoke test (iface must be None-safe)
        run: xvfb-run -a qgis_process list
      - name: run the registered Processing algorithm end-to-end
        run: xvfb-run -a qgis_process run native:coveragevalidate \
             -- INPUT=stratum_ro/test/fixtures/small_valid.gpkg
      - uses: actions/upload-artifact@v4
        with: { name: coverage-pyqgis, path: coverage.xml }

  # ---- 4. Format/QA conformance gate on a real deliverable ----
  conformance:
    runs-on: ubuntu-latest
    steps:
      - run: uv run python scripts/build_fixture_deliverable.py   # deterministic, small
      - name: OGC GeoPackage ETS
        run: python -m osgeo_utils.samples.validate_gpkg fixtures/deliverable.gpkg
      - name: GeoParquet conformance
        run: python -m osgeo_utils.samples.validate_geoparquet --check-data fixtures/parcels.parquet
      - name: COG conformance
        run: python -m osgeo_utils.samples.validate_cloud_optimized_geotiff fixtures/ortho.tif
      - name: Delivery manifest JSON Schema
        run: uv run python -m jsonschema -i fixtures/manifest.json schemas/delivery_manifest.schema.json

  # ---- 5. Evidence integrity: the 8-class ledger must not drift ----
  evidence:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: uv run python tools/verify_ground_truth_and_metrics.py
      - name: reports/ must match the latest MEASURED numbers
        run: git diff --exit-code reports/
```

### 7.2 Answers to the specific sub-questions

| Question | Answer |
|---|---|
| **Windows or Linux split?** | **Both, and for different reasons.** Windows: the PyQGIS/native-stack smoke test (matches the operator's real machine; catches NTFS path/locking bugs — relevant given the SQLite network-filesystem warning in §3.1). Linux: everything else, plus the QGIS container. Do **not** run PyQGIS on Windows CI — it's slow and flaky; run it on Linux containers and add one Windows job for path handling only. |
| **Cache large models/rasters?** | `actions/cache` for `~/.cache/uv` and `~/.cache/huggingface`. For multi-GB ONNX/SAM weights: **do not cache** — use `hf_hub`/release-asset download in a step with `actions/cache` keyed on `sha256sum(models/manifest.txt)`. 16 GB RAM / 6 GB VRAM on the dev box means CI should **never** run the full SAM2 inference; run it on a **tiny deterministic fixture** (256×256) and prove the plumbing. |
| **PyQGIS headless** | `qgis.testing.start_app()` in `conftest.py`; `QT_QPA_PLATFORM=offscreen` **and** `xvfb-run -a`. Both, always — `offscreen` alone is enough for most, but OpenGL-backed map canvases still need a real (virtual) X server, and combining them costs nothing and removes a whole class of flaky failures **[DOC]**. `PYQGIS_STARTUP` is *not* a standard env var — disregard it; the mechanism is `start_app()` + `Processing.initialize()`. |
| **`pytest-qgis`** | **5.0.0 on PyPI, requires Python ≥3.10** **[LIVE]**. Convenient fixtures, but it wraps the same `start_app()` idea. Optional; a 40-line `conftest.py` is more predictable. **Prefer your own conftest.** |
| **`pytest`** vs `unittest` | **Switch to pytest.** It's already in `requirements.txt` and already installed in CI **[LIVE]** — you're paying for it and not using it. Fixtures + parametrize + `--cov` + `-m` markers are decisive at 250+ tests. Keep `unittest.TestCase` classes working (they run under pytest unchanged) so there is no big-bang migration. |
| **`hypothesis` for geometry** | **ADOPT — the highest-leverage test investment available.** Details below. |
| **Mutation testing** | `mutmut` **3.8.0**, Python ≥3.10 **[LIVE]**. `cosmic-ray` is **stale — last release 2017** **[DOC]**; reject. **But: do not enable mutation gates yet.** First get a deterministic fixture + 80% coverage. Then run `mutmut` **nightly, non-blocking**, on `stratum_ro/vectorizer.py` + `cad_exporter.py` + `volumetric_3d.py` only. Rationale: mutation testing on a 250-test suite is expensive; on the *geometry canonicalisation* code — where a wrong answer is silently wrong rather than an exception — it is genuinely informative. Use `mutmut` 2's pragma syntax (`# pragma: no mutate`) for generated/numeric-threshold code. |

### 7.3 Property-based testing for geometry — the concrete design

**[LIVE]** There is **no maintained hypothesis strategy library for Shapely** (`hypothesis-geo` is not on PyPI; no active repo). So write your own — it is ~60 lines and you control the semantics.

```python
# stratum_ro/test/strategies.py
import math
from hypothesis import strategies as st
from shapely.geometry import Polygon, LineString

COORD = st.floats(min_value=1e5, max_value=6e6, allow_nan=False,
                  allow_infinity=False, width=32)          # EPSG:3844 plausible range
ORD   = st.sampled_from([0.0, 90.0, 180.0, 270.0])

@st.composite
def simple_polygons(draw, min_n=3, max_n=12):
    """Convex hull of distinct points => always simple, always valid."""
    n = draw(st.integers(min_value=min_n, max_value=max_n))
    pts = draw(st.lists(st.tuples(COORD, COORD), min_size=n, max_size=n,
                        unique=True))
    return Polygon(pts).convex_hull

@st.composite
def axis_aligned_rects(draw):
    x0 = draw(COORD); y0 = draw(COORD)
    w  = draw(st.floats(min_value=0.01, max_value=5000.0)); h = draw(st.floats(min_value=0.01, max_value=5000.0))
    return Polygon([(x0,y0),(x0+w,y0),(x0+w,y0+h),(x0,y0+h)])

@st.composite
def degenerate_polygons(draw):
    """DELIBERATELY invalid: zero-area, collinear, self-intersecting."""
    kind = draw(st.sampled_from(["collinear","zerothickness","bowtie","duplicate_point"]))
    x, y = draw(COORD), draw(COORD)
    d = draw(st.floats(min_value=0.0, max_value=100.0))
    return {
        "collinear":        Polygon([(x,y),(x+d,y),(x+2*d,y)]),
        "zerothickness":    Polygon([(x,y),(x+d,y),(x+d,y),(x,y)]),
        "bowtie":           Polygon([(x,y),(x+d,y+d),(x+d,y),(x,y+d)]),
        "duplicate_point":  Polygon([(x,y),(x+d,y),(x+d,y),(x,y)]),
    }[kind]
```

**The properties worth testing in `vectorizer.py` — these are the ones that find real bugs:**

```python
from hypothesis import given, settings, assume
from shapely.validation import explain_validity

# P1 — the contract of the deliverable. THE most important test you can write.
@given(simple_polygons())
def test_output_is_always_GEOS_valid(inp):
    out = regularize(inp)
    assert out.is_valid, explain_validity(out)

# P2 — idempotence: regularising twice == regularising once
@given(simple_polygons())
def test_regularization_is_idempotent(inp):
    assert regularize(regularize(inp)).equals(regularize(inp))

# P3 — 90-degree claim. Only valid if area is preserved (rectangle fitting),
#     otherwise assert the weaker, still-useful "axis-aligned bounding geometry".
@given(axis_aligned_rects())
def test_output_sides_are_orthogonal(r):
    out = regularize(r)
    coords = list(out.exterior.coords)
    for (x1,y1),(x2,y2) in zip(coords, coords[1:]):
        assert abs(x1-x2) < TOL or abs(y1-y2) < TOL      # horizontal or vertical

# P4 — no vertex loss beyond the stated tolerance. This is the 4-vertex
#     canonicalisation contract, and it is the one most likely to be violated.
@given(simple_polygons(), st.floats(min_value=0.0, max_value=10.0))
def test_hull_of_output_covers_input(inp, shrink_m):
    out = regularize(inp)
    assert inp.difference(out).area <= shrink_m * inp.exterior.length

# P5 — AREA INVARIANCE. The single most valuable property test.
#     If regularisation changes area beyond tolerance, every cadastral
#     area downstream is wrong. Assert this FIRST.
@given(simple_polygons())
def test_area_change_bounded(inp):
    out = regularize(inp)
    assert math.isclose(inp.area, out.area, rel_tol=1e-6, abs_tol=0.01)

# P6 — degenerate inputs must FAIL LOUDLY, not silently emit garbage.
@given(degenerate_polygons())
def test_degenerate_input_raises_or_is_flagged(bad):
    try:
        out = regularize(bad)
    except (ValueError, InvalidGeometry):
        return
    assert out.is_valid, "degenerate input produced invalid output silently"

# P7 — round-trip through the wire formats
@given(simple_polygons())
def test_wkb_roundtrip_is_lossless(g):
    assert from_wkb(to_wkb(g)).equals_exact(g, tolerance=0.0)

# P8 — CRS guard. Cheap, and catches the worst class of cadastral bug.
@given(simple_polygons())
def test_never_silently_reprojects(g):
    # regularize() must raise if handed lat/lon-looking coordinates
    assume(-180 <= g.centroid.x <= 180 and -180 <= g.centroid.y <= 180)
    with pytest.raises(ValueError):
        regularize(g)      # degrees in, projected expected -> must not guess
```

Use `@settings(max_examples=200, deadline=None)` — `deadline=None` is essential because large synthetic polygons in EPSG:3844 coordinate space are slow. Store a Hypothesis **database** (`.hypothesis/`) as a CI artifact so failures reproduce.

**Cost/benefit:** this is ~150 lines and will take a day. It is worth more than the next 50 example-based tests, because P3/P4/P5 encode the *cadastral contract* (orthogonality, no vertex loss, area preservation) rather than the implementation. AGENTS.md rule "Geometry / Math → Deterministic Local… Zero LLM hallucinations permitted" is exactly a set of invariants — **invariants belong in property tests, not in prose.**

---

## 8. §6 — AI/ML for geospatial: MLOps and evaluation

### 8.1 Toolchain status (all versions live-checked on PyPI)

| Package | Latest | Python | Fit for this repo |
|---|---|---|---|
| `torchgeo` | **0.10.1** | **≥3.12** | Great dataset/sampler/transform library. **Blocked by Python 3.10.** Blocked only by §6.2's Python bump. |
| `odc-stac` | 0.5.3 | ≥3.10 | STAC → xarray. **ADOPT** for ortho/nDSM loading. Only needs STAC access. |
| `stackstac` | 0.5.1 | <4.0,≥3.8 | STAC → xarray via dask. Alternative to `odc-stac`; pick **one**. `odc-stac` is better maintained and has a cleaner `stac_dask` API. |
| `rioxarray` | 0.23.0 | **≥3.12** | xarray ⊗ rasterio — CRS-aware rasters. Blocked by Python 3.10. |
| `geodatasets` | **2026.5.1** | ≥3.8 | Test/benchmark datasets, no manual download. **ADOPT for tests** — it removes network dependency from CI. |
| `pyarrow` | 25.0.1 | ≥3.10 | Needed for GeoParquet. **ADOPT.** |
| `duckdb` | 1.5.6 | ≥3.10 | Analytics over GeoParquet without PostGIS. **ADOPT for QA/eval.** |
| `pystac` | 1.15.2 | ≥3.10 | Write static STAC catalogs. **ADOPT.** |

**Decision:** adopt `odc-stac` + `pyarrow` + `duckdb` + `pystac` now (all ≥3.10 compatible); adopt `torchgeo`/`rioxarray` only after the Python 3.12 move, and only if you actually need multi-modal/geospatial samplers — for 2D building segmentation `rasterio` windows are already sufficient and much faster.

### 8.2 Tiled/chipped inference — the correct recipe, with the citation

**The canonical rule [PUB]:** tile size must fit GPU memory *plus* a halo of at least half the network's receptive field; stride by the tile size **excluding** the halo, so that **output** tiles abut exactly at the seams while **input** tiles overlap.

> "Select a tile size that will fit into GPU memory with a halo border of half the network receptive field. Next, stride across the image by that tile size without the halo. The input tile halos will overlap, while the output tiles join exactly at the seams."
> — Exact Tile-Based Segmentation Inference for Images Larger than GPU Memory (PMC10914126)

**This is the *only* correct recipe**, because it guarantees that **every output pixel is produced by a context window centred on it**. A naive "stride = tile size" sliding window produces edge artifacts on *every* tile border, not just the image border.

**Concrete numbers for a 6 GB VRAM RTX 4050 running SAM 2 Hiera / a U-Net:**

| Quantity | Value | Note |
|---|---|---|
| Receptive field, SAM 2 Hiera (large window) | 1024 px | half-field halo = 512 px |
| Training/inference tile | 1024 × 1024 px | SAM 2's native window |
| Halo | 512 px (50% overlap) | forced by the architecture |
| Stride | **512 px** (tile − halo) | **output tiles abut exactly** |
| GSD (0.10 m/px) | 1024 px tile = 102.4 m | |
| Effective area at 0.10 m/px | 51.2 m visible, 102.4 m halo | |
| Memory ceiling | keep peak < 4 GB of 6 GB | leave VRAM for DirectML/CUDA context |

**Literature survey of the overlap percentage [PUB]:** a review of 71 semantic-segmentation papers on satellite imagery found **18 used overlap techniques, mostly 50% overlap**; a systematic study on road extraction from aerial orthophoto found the best configuration was **1024 × 1024 px tiles at 12.5% overlap** (U-Net + Inception-ResNet-v2, mean test IoU 0.5943) — i.e. **50% is a safe default but not optimal for every model.** Tune the overlap as a hyperparameter and *report it*; a hard-coded 50% with no justification is a review finding.

**Blending:** for **soft** outputs (SAM 2 low-res logits), use **cosine (raised-cosine) window weighting** across the overlap region — it minimises the discontinuity in first derivative at the seam. For **hard** outputs, **majority vote / logical OR** over overlaps, then polygonise **once** on the merged mask. **Never** polygonise per tile and merge polygons: that guarantees duplicate fragments at every seam, which is precisely the failure mode your `native:deleteduplicategeometries` attribute-blind dedup would then silently delete attributes from.

**Determinism requirement for your repo:** write a **tile index** (`{tile_id, x_off, y_off, size, halo, stride, sha256_of_tile}`) to disk as part of the run provenance. Then any seam artifact is reproducible and debuggable. Add it to `activities[]` in `manifest.json` (§4.3).

### 8.3 Model registry and weights

- **DVC: reject** (§4.4, stewardship change Nov 2025).
- **Git: reject for binary weights** (you already have 6 GPKGs tracked; do not add a 300 MB ONNX).
- **ADOPT: content-addressed artifacts + a manifest.** `models/manifest.yaml` listing `name, version, sha256, url, licence, input_shape, mean/std, target_crs, gsd`. CI verifies `sha256`. That is a model registry adequate for a 1-model project, and it is *auditable by a human*, which is what ANCPI cares about.
- Record the **training-data provenance** per model, not just the weights. A model with no recorded training set is `UNVERIFIED` under your own 8-class scheme, permanently.

### 8.4 Evaluation harness — concrete protocol

Adopt and *declare* this in the manifest (`quality.thematic_accuracy`):

```
MATCHING
  cost[i][j] = 1 - IoU(pred_i, ref_j)         computed on :memory layers, EPSG:3844, prepared geometry
  primary    : greedy match at IoU >= 0.5      ("F1_greedy", SpaceNet-comparable)
  secondary  : scipy.optimize.linear_sum_assignment(cost), then threshold   ("F1_hungarian", upper bound)
  REPORT BOTH, and say which one is the headline.

REPORT (never a bare ratio)
  TP, FP, FN
  TP / matched_reference          <- recall denominator
  TP / total_predictions          <- "commission" denominator
  precision, recall, F1
  IoU distribution of matched pairs:  min / p10 / median / mean / max
  confidence interval on recall:   Wilson 95%     (already in engine/evaluation.py)
  per-class breakdown for UNCLASSIFIED / ARTEFACTE_RESPINSE_SAM2 / ...
  AND the ASPRS-style N / V split if you ever claim NVA/VVA compliance.
```

**Add a `duckdb` step** — this is cheap and becomes the natural home for large-scale duplicate/topology sweeps over GeoParquet:

```sql
-- exactly-duplicate geometry detection at scale, on GeoParquet
WITH wkb_hash AS (
  SELECT id, sha256(encode(geometry_wkb)) AS h, area(geometry) AS a
  FROM read_parquet('deliverable.parquet')
)
SELECT h, count(*) n, min(a) a_min, max(a) a_max
FROM wkb_hash GROUP BY h HAVING count(*) > 1
ORDER BY n DESC;
```

`--ignore-duplicates` / grouping gives you tier-1 dedup at dataset scale in seconds. Tier-3 (Hausdorff) still needs Python + STRtree, but you can prefilter candidates in DuckDB with a bbox overlap join.

### 8.5 Confidence calibration — is there geospatial literature? Yes.

**There is real, citable literature on calibration for geospatial semantic segmentation**, and it is worth adopting because it directly addresses your `VLM_AUDITED_BUILDINGS` / `CLADIRI_HIBRID` confidence fields.

- **ECE (Expected Calibration Error)** and **reliability diagrams** are the standard tools **[PUB]**. For pixel-wise semantic segmentation, "calibrated perception uncertainty across objects and regions in bird's-eye-view" **[PUB]** applies ECE and reliability diagrams to exactly this setting (BEV segmentation), notes the **equal-width vs equal-mass binning** distinction, and — importantly for a cadastral product — argues calibration should be assessed **per-object and per-region**, not only per-pixel. That is the right frame: what matters is whether a building given 0.8 confidence is correct 80% of the time **in this neighbourhood of Romania, at this GSD, in this season**.
- Per-image calibration metrics for segmentation (reliability diagram per image, not pooled) is a documented technique **[PUB, arXiv 2506.03942]**.
- ECE limitations are documented by the US national labs in a calibration-metrics assessment (SANDIA report **[PUB, OSTI 2430119]**) which compares ECE, MCE, SCE, ACE, reliability-in-the-small, Brier, and reliability diagrams, and is explicit that **no single metric is sufficient**.

**Implementation (30 lines, high value):**

```python
def ece_and_diagram(records, n_bins=15):
    """records: list of (confidence, was_correct). Equal-mass binning (better for
    the long tail of low-confidence candidates you actually care about)."""
    import numpy as np
    c = np.array([r[0] for r in records]); y = np.array([r[1] for r in records])
    edges = np.quantile(c, np.linspace(0, 1, n_bins + 1)); edges[0], edges[-1] = 0.0, 1.0
    idx = np.clip(np.searchsorted(edges, c, "right") - 1, 0, n_bins - 1)
    ece, diagram = 0.0, []
    for b in range(n_bins):
        m = idx == b
        if not m.any(): continue
        acc, conf = y[m].mean(), c[m].mean()
        ece += m.mean() * abs(acc - conf)
        diagram.append((conf, acc, int(m.sum())))
    return ece, diagram
```

**What to do with it:** fit temperature scaling (one scalar `T`, one line of code) on a held-out split, then report `ECE(before)` and `ECE(after)` **as two MEASURED numbers in the manifest**. That converts "confidence: 0.83" from a meaningless float into a calibrated probability a surveyor can reason about. This is exactly the kind of thing that makes a delivery defensible.

**Do not** claim calibration transfers across UATs, ortho campaigns, or seasons. Report it per campaign.

---

## 9. §7 — MLOps for LLM/VLM orchestration

### 9.1 The state of your provider router (repo-measured 2026-10-08, from AGENTS.md)

`AGENTS.md` records a live HTTP probe (`scripts/provider_credit_status.py`) as of today:

| Provider | Status | Evidence class |
|---|---|---|
| NVIDIA NIM `meta/llama-3.2-11b-vision-instruct` | **OPERATIONAL** (HTTP 200) but **passed 1/9 falsification controls — it approves pure noise** | MEASURED |
| Google Gemini `gemini-3.1-flash-lite` | **OPERATIONAL, free tier, quota-limited** (~15 RPM, bursts → HTTP 429), **passed 4/4 transport + discrimination controls, 8/9 falsification** | MEASURED |
| OpenRouter / UnionAlpha | **DEAD — HTTP 402, balance −0.20 USD**, and both env vars hold the **same key** | MEASURED |
| OpenAI direct | **DEAD — HTTP 429, no credits** | MEASURED |
| Anthropic direct | **DEAD — HTTP 400, credit balance too low** | MEASURED |
| Cerebras / SambaNova | **DEAD — 402 / 401** | MEASURED |
| Ollama (local) | **OPERATIONAL, no credits**: `llava:13b`, `minicpm-v:8b`, `qwen3:8b`, `qwen3-agent:8b`, `dolphin3:8b`; vision latency **22–49 s** | MEASURED |
| Local mock | **OPERATIONAL, 0.0 ms, deterministic** | MEASURED |

**I did not re-run the probe** (no keys, and it would burn quota). Treat the table as the repo's own MEASURED record, not as my verification.

### 9.2 Free-tier guidance for 2026 — honest, and mostly negative

**I am marking this section [UNVERIFIED].** Free-tier economics change weekly; any list I write from memory would be stale by publication. What is *not* volatile:

1. **The pattern is stable:** free tiers are (a) rate-limited to single-digit RPM, (b) vision-capable models behind them are the *smallest* ones, (c) they are excluded from SLA and can be retired with no notice. Gemini's ~15 RPM and the HTTP 429 you already measured **[LIVE repo]** is the canonical example.
2. **Therefore: never put a free tier in a correctness path.** Only in an advisory/audit path, always with a deterministic local fallback and always recorded as `MEASURED` with a timestamp.
3. **Your probe script is the right artifact.** `scripts/provider_credit_status.py` already exists. Make it emit a **machine-readable JSON** committed to `reports/`, refreshed on a schedule, so provider status is evidence rather than a claim. That fits your 8-class system exactly.

**Practical local-first stack (2026):**

| Need | Recommendation |
|---|---|
| Text reasoning / task decomposition | `qwen3:8b` via Ollama — already installed **[repo]** |
| Vision (falsification audit only) | `qwen3-vl:8b` or `minicpm-v:8b` — but **22–49 s latency** means a national pass is hours. Budget for it or don't run it. |
| Anything geometry/math | **NOT an LLM.** Your AGENTS.md rule 1 already says this. Enforce it in code: no LLM call may return a coordinate. |

Quantisation/speculative routing is the right *engineering* answer but it is not the bottleneck — **your bottleneck is that the task does not need an LLM.** See §9.4.

### 9.3 Is there a defensible way to say "we don't need a frontier VLM here"? Yes — three independent lines of evidence.

This is the highest-value defensibility argument available to the project, and it is fully citable.

**(a) The published benchmarks say frontier MLLMs are not yet adequate on high-resolution remote sensing.**
- **XLRS-Bench** (CVPR 2025, Highlight award) **[PUB]** — https://cvpr.thecvf.com/virtual/2025/poster/35068 — uses **8500×8500 px** average image size (the largest observed) with **manual annotation** and **16 sub-tasks** across 6 perceptual and 4 reasoning abilities. Result: *"The results of both general and RS-focused MLLMs on XLRS-Bench indicate that further efforts are needed to enhance their performance in real RS scenarios."*
- **GeoLLaVA-8K** (NeurIPS 2025) **[PUB]** — https://proceedings.neurips.cc/paper_files/paper/2025/file/e95ef5c6ed4096c609e0b8b47ffaeb9b-Paper-Conference.pdf — states that *"even leading models like GPT-4o and Qwen-VL series are limited up to 4K resolution, resulting in limited performance (Accuracy < 0.45) on the XLRS-Bench."* Orthophoto at 0.10 m GSD is **8,500+ px** for a 1 km tile — a 2×–10× input-size gap from the 4K ceiling.
- **CHOICE** (benchmarking RSVLMs) **[PUB]** — https://arxiv.org/html/2411.18145v4 — finds *"the models evaluated … continue to underperform on vision tasks requiring fine-grained output formats, such as segmentation masks."* Building-footprint extraction **is** a mask task.
- **LHRS-Bench / LHRS-Bot** (NeurIPS/ICCV) **[PUB]** — same family, same conclusion.

**(b) Your own measurements already falsify the VLM on this task.**
From `AGENTS.md` **[LIVE repo, MEASURED]**:
- NVIDIA NIM 11B vision: **1/9** on falsification controls — *it approves pure noise*.
- Gemini 3.1-flash-lite with a **describe-first** prompt: **8/9**.
- Gemini with a **leading** question ("is this a real building?"): **drops to 2/9**, producing **false approvals**.

That last datum is the strongest possible argument, and it is *yours*: **the same model's verdict flips from correct to wrong based on question wording.** That is not a model you can put in front of a licensed surveyor. It is, however, a perfectly good *auditing* tool: a prompt-sensitive model is a sensitive detector of prompt bias, which is exactly what a falsification harness should measure.

**(c) Task structure.** Building-footprint delineation is a **dense binary segmentation** problem on a raster with known GSD. The correct instrument is a trained CNN/ViT encoder-decoder, not a generative model reading a text prompt. This is not an aesthetic preference; it is what every SpaceNet/XLRS participant does.

**Therefore, write this into `AGENTS.md` as a normative routing rule:**

> **Rule 7 — VLM scope restriction.**
> No VLM output may enter the deliverable path (`CLADIRI_SOL_ANCPI`, DXF `1CC`/`2CC`/`CP`, `.CP` tables). VLM output is permitted **only** in `VLM_AUDITED_BUILDINGS` / `VLM_REAL_AUDIT`, which are **audit layers**, are **non-authoritative**, and are **excluded from all accuracy metrics reported in the manifest**.
> Justification: **(1)** XLRS-Bench (CVPR 2025) reports general and RS-specific MLLMs remain inadequate on ultra-high-resolution RS imagery; GeoLLaVA-8K (NeurIPS 2025) measures GPT-4o/Qwen-VL accuracy < 0.45 on XLRS-Bench with a 4K input ceiling; **(2)** MEASURED on this project 2026-10-08: NIM vision 1/9 on falsification controls, Gemini 8/9 describe-first but 2/9 leading-question, i.e. verdict is prompt-dependent; **(3)** the task is dense instance segmentation, for which published benchmarks (SpaceNet) use dedicated segmentation models. Evidence class of the VLM layer: **MEASURED (prompt-sensitivity), never VALIDATED.**

**Add a governance metric:** report **"VLM audit coverage"** = `n(artefacts_rejected_by_VLM) / n(total_predicted)` as an *advisory* number, alongside (never inside) the recall metric. If the VLM flags 22 of 26 candidates, reviewers can use it as a triage signal — but the manifest's `recall` must never include it.

### 9.4 The positive alternative: a small supervised classifier beats a big VLM

This is the recommended investment, and it is cheap given you already have labels.

- Your ground truth already exists: `data/ground_truth/tier1_teren.geojson` (29 real cadastral buildings), `cluj_combined_unique_150.geojson` (150 reference buildings), plus `ARTEFACTE_RESPINSE_SAM2` and `VLM_REAL_AUDIT` as accumulated negative/positive labels.
- The general principle — deep features + a linear/simple head beat zero-shot VLM classification on domain-specific visual tasks — is the "deep features are all you need" line of work. **[RECALL, broad claim]**
- The concrete, defensible experiment is cheap: **train a logistic regression or gradient-boosted tree on a frozen CLIP/DINOv2 embedding of each candidate's ortho crop**, and compare its PR curve against the VLM's PR curve on the **same** labels using the **same** matching protocol (§8.4). 150+ labelled examples is enough for a linear probe. Two days of work.
- **If the probe wins — and it usually does on a narrow domain with a fixed imaging geometry — that is a MEASURED, citable, reproducible reason to delete the VLM dependency.** And it runs *offline, deterministically, on CPU, in 40 ms*, which is a materially better proposition for an ANCPI delivery than a 22–49 s local VLM or a quota-limited free API.

**This is the single highest-return ML experiment in the whole report.** It costs two days, removes the project's only un-reproducible dependency, and produces exactly the kind of evidence AGENTS.md was designed to demand.

---

## 10. §8 — What's new in 2025–2026 worth knowing

| Development | Status (verified) | Relevance |
|---|---|---|
| **Native Parquet `GEOMETRY`/`GEOGRAPHY` logical types** | Parquet 2.11, **March 2025**; Apache blog 2026-02-13; GDAL support `USE_PARQUET_GEO_TYPES` in **3.12** (needs libarrow ≥21) **[DOC]** | **High.** Row-group bbox stats → spatial pruning (demo: 3 of 2,585 row groups read). Makes GeoParquet an Iceberg/lakehouse-native citizen. Requires GDAL ≥3.12 → **another reason to upgrade QGIS**. |
| **GeoParquet 2.0** | **v2.0.0-rc.1, 2026-07-19** — still RC **[LIVE]** | Medium. **Do not target 2.0.** Write 1.1. |
| **GeoArrow** | v0.2, field-level metadata + memory layout, applies in-memory/on-disk/on-wire **[DOC]** | Medium. Powers the `GEOARROW` GDAL geometry encoding (GeoParquet 1.1). **Note: GDAL docs warn `GEOARROW_INTERLEAVED` "is not part of the official GeoParquet specification, and its use is not encouraged"** — use `GEOMETRY_ENCODING=WKB` **[DOC]**. |
| **GDAL GTI driver + STAC GeoParquet catalogs** | GTI added 3.9; **STAC GeoParquet support added 3.10**; `gdal raster index --profileSTAC-GeoParquet` in **3.13** **[DOC]** | High. GDAL can now consume `proj:code`/`proj:transform` from a STAC catalog to build a correctly-projected virtual mosaic. |
| **`gdal driver gpkg validate`** | GDAL **3.13.3** **[DOC]** | High. Makes the OGC GPKG ETS a one-liner — after your upgrade. |
| **PostGIS `ST_CoverageClean`** | GEOS 3.14 + PostGIS 3.6, 2025 **[DOC]** | Medium-high *conceptually*: automatic cleaning of dirty polygonal coverages (overlaps + gaps) — "coverages — a set of polygons that uniquely tile an area… States. Counties. Parcels." **Exactly your problem class.** Available in `qgis/native:coveragevalidate` today without PostGIS. |
| **PostGIS `ST_MakeValid`** | 3.5+ added SFCGAL/CGAL 3D functions; `ST_CoverageInvalidEdges` etc. **[DOC]** | Low (no PostGIS). |
| **Apache SedonaDB** | **0.4.0, 2026-06**; Rust single-node spatial engine, lazy `read_parquet` over s3://, R + Python + Rust APIs, GPU-accelerated spatial join in 0.4 **[DOC]** | **Watch.** `[RECALL]` "still in the early stages." Benchmarks show **SedonaDB 0.24 s vs PostGIS 6.4 s vs DuckDB 43.1 s** on a spatial-join-with-aggregation (M3, 8 CPU Docker) **[DOC]** — a huge gap, but single-benchmark and single-node. Not production-ready for a cadastral deliverable. |
| **DuckDB spatial** | Mature enough for ad-hoc analytics; `spatial` extension **not autoloadable** — you must `INSTALL spatial; LOAD spatial;` **[DOC]** | High, for QA/eval only. Beats PostGIS ergonomics for a laptop. |
| **`stac-fastapi` GeoParquet/DuckDB backends** | **marked Experimental** **[DOC]** | Low. |
| **Iceberg + spatial** | PostGIS/Iceberg catalog mapping work is active (Crunchy/Wherobots) **[DOC]** | Low. Overkill. |
| **PMTiles v3** | Spec v3; Hilbert TileIDs, run-length dirs, optional `clustered` layout; single-file Go executable, no Python needed **[DOC]** | Low (EPSG:3857 constraint). |
| **OGC API - Records Part 1 Core** | **OGC Standard, 2025-04-07** **[DOC]**; Parts 2 (Facets) / 3 (CRUD) in progress | Medium, Phase-3. |
| **OGC API - Coverages Part 1 Core** | **RFC, comments close 2026-10-15** **[DOC]** | Low. Wait. |
| **OGC API - Connected Systems Parts 1 & 2** | Approved **[DOC]** (Systems + Sampling Strategies) | Low — but if you ever serve sensor/time-series data, read it. |
| **OGC API - Discrete Global Grid Systems Part 1 Core** | Approved **[DOC]** | Low. |
| **OGC GeoPackage 1.4.0** | Adopted, `12-128r19` **[DOC]** | High — confirm your target ANCPI/e-Terra version. |
| **CityJSON 2.0.2 + CityJSONSeq / FlatCityBuf** | ISPRS paper 2026 on CityJSONSeq/FlatCityBuf/3D Tiles 1.1 **[DOC]** | Medium. Watch for CityJSONSeq as a streaming LoD format. |
| **3D Tiles 1.1** | OGC CS `22-025r4`; glTF leaves replace `b3dm` **[DOC]** | Medium, conditional. |
| **ASPRS Positional Accuracy Standards Ed.2 v2 (2024)** | Adopted 2024-06-24 **[PUB]**; USGS has updated Lidar Base Specification to conform **[DOC]** | **High** — this is the accuracy-reporting norm now (§5.6d). |
| **ISO 19157-1:2023** | Current DQ edition **[DOC]** | High. |
| **ISO/AWI 25082-2** | Work item in progress on GNSS positioning assessment **[DOC]** | Watch. May supersede ISO 21457/17123. |
| **DVC → lakeFS** | Acquired **Nov 2025**; DVC 3.0 **Jan 2026**; moved to `treeverse/dvc` **[DOC]/[LIVE]** | High — argues against new DVC adoption. |
| **Sedona 1.9.1** | Geography SQL on the sphere, Box2D/Box3D with Parquet pushdown, raster Python UDFs, GeoTIFF/NetCDF metadata readers **[DOC]** | Low. |
| **PostGIS 3.7.0rc2** | RC with PG 14–19beta3, GEOS 3.15, SFCGAL 2.3.0 **[DOC]**; `postgis_tiger_geocoder` split from core **[DOC]** | Reject for this project. |

### 10.1 Explicitly evaluated and rejected

| Item | Verdict |
|---|---|
| **PostGIS** | Reject. Desktop plugin, single operator, 1 writer, 16 GB RAM. It is a server product. |
| **SingleStore / Sedona / Databricks** | Reject. Orders of magnitude too large. |
| **Polars-spatial** | Reject. Immature, not in your path. |
| **Polars / DuckDB as the *master*** | Reject as master (Parquet has no spatial index **[DOC]**), **accept** as an analytics engine over the GeoParquet archive. |
| **`geo` Rust crate** | Reject. You are a Python project. |
| **Nix** | Later. Bad Windows story. |
| **`rio` CLI** | Reject — duplicates rasterio. |
| **`pygeos`** | Reject — merged into Shapely 2.0; you already have Shapely 2.1.2. |
| **OGC GeoValidator** | Reject — unmaintained, GML-era. |
| **QGIS Server validation** | Reject — you don't serve OGC services. |
| **PROV-O** | Reject the technology, adopt the model. |
| **Git LFS / git-annex / lakeFS** | Reject all three for this scale. |
| **Dagster / Prefect / Nextflow** | Reject. |
| **MLflow** | Reject. |
| **MVT / PMTiles as a deliverable** | Reject (EPSG:3857). |
| **I3S** | Reject. |
| **GeoParquet 2.0** | Reject — RC since 2026-07-19. Target 1.1. |

---

## 11. Prioritized action list for StratumRO

### 11.1 ADOPT NOW — do these this week

| # | Action | Concrete file/command | Why it's cheap |
|---|---|---|---|
| A1 | **Upgrade QGIS 3.40.0 → 3.44.15 LTR** | OSGeo4W online installer, `qgis-ltr` package. Re-run `venv\Scripts\python -m unittest discover stratum_ro/test` and report the exact count. | 3.40 has had no release since 2026-01-16 **[LIVE]**. |
| A2 | **Guard `iface is None` in the plugin `__init__`** | `stratum_ro/__init__.py`: `if iface is None: return StratumROCore()` (headless/core mode) | Fixes the verified `qgis_process` crash **[LIVE]**; unblocks CI. |
| A3 | **Add the PyQGIS CI job** | `.github/workflows/ci.yml`: `container: qgis/qgis:ltr` + `QT_QPA_PLATFORM=offscreen` + `xvfb-run` | Turns 9 silent skips into 9 real tests. |
| A4 | **Replace unpinned CI install with `uv lock --frozen` + `uv lock --check`** | add `pyproject.toml` + `uv.lock`; delete the hand-written `pip install` line | Makes CI reproducible. 30 minutes. |
| A5 | **Wire the OGC GPKG ETS into CI** | `python -m osgeo_utils.samples.validate_gpkg fixtures/deliverable.gpkg` | Script is already on disk, 113 KB, official OGC **[LIVE]**. |
| A6 | **Author `schemas/delivery_manifest.schema.json`** from §4.3 | ~40 lines + 1 `jsonschema` call. `jsonschema` 4.26.0 already installed **[LIVE]**. | Highest-leverage artifact in this report. |
| A7 | **`git reflog expire --expire=now --all && git gc --prune=now`**; untrack 6 `.gpkg`, 20 `.tif`, 1 `.onnx`; add to `.gitignore` | measure before/after with `git count-objects -vH` | Reclaims **6.16 GiB** **[LIVE]**. |
| A8 | **Split the 21-layer GPKG** | deliverable GPKG (`CLADIRI_SOL_ANCPI` + TopoLT support layers) + `qa_<runid>.gpkg` (STAGE_*, UNCLASSIFIED, ARTEFACTE_*, VLM_*, CLADIRI_ELIMINATE_*) | Removes the ambiguity that would sink an ANCPI submission. |
| A9 | **Write the six `hypothesis` property tests from §7.3** | `stratum_ro/test/strategies.py` + `test_properties_vectorizer.py`, `@settings(max_examples=200, deadline=None)` | ~150 lines. Encodes the cadastral invariants (P3/P4/P5) that no example-based test protects. |
| A10 | **Switch CI from `unittest discover` to `pytest`** (with `--cov`) | `pytest` is *already installed* by your `requirements.txt` **[LIVE]** and unused. Existing `TestCase` classes run unchanged. | Free; enables fixtures, markers, coverage. |
| A11 | **Write the property that matters most: tolerance sweep for near-duplicates** | §5.4 table, 7 tolerances | Turns an arbitrary dedup decision into reviewer-visible evidence. |
| A12 | **Emit the QA gate as a non-zero-exit script** | `tools/qa_gate.py`: validate_gpkg → coveragevalidate → fixgeometries → duplicates → schema → sha256 → manifest | Everything it needs is already installed. |

### 11.2 ADOPT NEXT — this month

| # | Action |
|---|---|
| B1 | **Add `Rule 7 — VLM scope restriction` to `AGENTS.md`** (§9.3, verbatim text supplied). Highest defensibility-per-byte in this report. |
| B2 | **Compute RSMD / RSMD₀.₉₅ alongside RMSE in `engine/evaluation.py`**, and switch the report format to ASPRS 2024 style (RMSE_H/V/3D + n + reference + N/V area). **First verify `c_1,c_2,c_3` against a purchased ISO 21457/17123** (§12). |
| B3 | **Mandatory Wilson confidence interval on recall** in every report and in `manifest.json`. Already implemented — make it non-optional. |
| B4 | **Report `F1_greedy` (IoU≥0.5, SpaceNet-comparable) AND `F1_hungarian`, plus IoU at 0.3 and 0.5**, with the declared headline choice. |
| B5 | **Write the tile-index provenance file** (tile_id, x_off, y_off, size, halo, stride, sha256) and reference it from `activities[]`. |
| B6 | **Add ECE + reliability diagram (equal-mass, 15 bins) and temperature scaling** to the evaluation harness; report `ECE_before`/`ECE_after` as MEASURED. |
| B7 | **Bump the venv to Python 3.12**, then adopt `torchgeo`/`rioxarray` **only if needed**; adopt `odc-stac` + `pyarrow` + `duckdb` + `pystac` now (all ≥3.10-compatible). |
| B8 | **Emit static STAC `catalog.json` + `collection.json`** next to every raster delivery. |
| B9 | **Dual-write GeoParquet 1.1 (`GEOMETRY_ENCODING=WKB`) for the polygon master.** |
| B10 | **Run `mutmut` nightly, non-blocking, on `vectorizer.py` / `cad_exporter.py` / `volumetric_3d.py`.** |
| B11 | **Make `scripts/provider_credit_status.py` emit committed JSON** to `reports/` so provider status is evidence, not assertion. |

### 11.3 LATER — quarter-plus

| # | Action | Trigger |
|---|---|---|
| C1 | **The 2-day experiment: frozen-embedding linear probe vs the VLM** (§9.4) | If it wins, delete the VLM dependency from the advisory path too. |
| C2 | **Model the manifest on the INSPIRE Cadastral Parcels Data Specification requirement list** | When an actual ANCPI submission is scheduled. Read the PDF: https://inspire-mif.github.io/technical-guidelines/data/cp/dataspecification_cp.pdf |
| C3 | **3D Tiles 1.1 export** | Only if a 3D web viewer is a real requirement. |
| C4 | **`gdal driver gpkg validate`** (GDAL 3.13.3) instead of the script | Comes free with the QGIS upgrade chain. |
| C5 | **PostGIS, if and only if** a second concurrent writer becomes a real requirement | Not before. |
| C6 | **pxi** if `uv` alone cannot resolve a system-lib conflict | Not before. |
| C7 | **Nix / Apptainer** | If multi-OS bit-identical binaries become a requirement (e.g. an auditor reproduces on Linux). |
| C8 | **SedonaDB** | When it exits "early stages." |
| C9 | **OGC API - Records service** over the static STAC catalog | Phase 3. |
| C10 | **GeoParquet 2.0 / native Parquet geo types** | When GDAL ≥3.12 is your baseline *and* 2.0 leaves RC. |
| C11 | **Git LFS** | Never, at this scale. |
| C12 | **DVC** | Never at this scale, and especially not across a stewardship change. |

---

## 12. What I could NOT verify — read before publishing any number

Per the repo's Evidence-First rule, these are **UNVERIFIED** and must not be asserted without the primary source:

| # | Item | Status | How to close it |
|---|---|---|---|
| U1 | **Exact `c_1`, `c_2`, `c_3` coverage constants in ISO 21457:2008 RMSD/RSMD** | **UNVERIFIED.** ISO is paywalled; the only ISO 21457 full text I could reach was a *different standard with the same number* (ISO 21457:2010, materials/corrosion). I deliberately did not assert constants from memory. | Purchase ISO 21457:2008 and the ISO 17123 parts. Secondary citable frames: NGS RT Guidelines, ICSM guidelines. |
| U2 | **Whether ISO 21457 / ISO 17123 are superseded** | Partially. ISO/AWI 25082-2 is in progress **[DOC]**. | Monitor https://www.iso.org/standard/93504.html |
| U3 | **Which GDAL version QGIS 3.44.15 ships** | Not checked. I only verified the *installed* 3.9.3. | `qgis-ltr` in OSGeo4W, then `gdalinfo --version`. Determines whether GTI-STAC (3.10), Parquet geo types (3.12) and `gdal driver gpkg validate` (3.13.3) are available. |
| U4 | **QGIS 3.40's support-expiry date** | Inferred from "last build 2026-01-16" + "no longer LTR" **[LIVE]**, not from an official EOL notice. | qgis.org roadmap / release schedule. |
| U5 | **Live free-tier status of any LLM provider** | **UNVERIFIED.** I did not have keys and would have burned quota. §9.1 is the repo's own MEASURED record from today, not my check. | Run `scripts/provider_credit_status.py`; commit its JSON. |
| U6 | **`shapely.is_valid_reason` exact return format on Shapely 2.1.2** | Documented for 2.2; **[RECALL]** that it exists in 2.1.2. | One-line local check. |
| U7 | **`coveragevalidate` behaviour on `Polygon` vs `MultiPolygon` and on non-coverage layers** | Not characterised. | Property tests (§7.3) + a fixture. |
| U8 | **Romanian-specific: the ANCPI acceptance criteria and required metadata for a pre-cadastral submission** | **UNVERIFIED.** I located Ordinul ANCPI nr. 600/2023 (Monitorul Oficial nr. 125, 14 Feb 2023) plus amendment Ordinul 1255/2023, and note the Union of Romanian Surveyors (UGR) filed a **public letter objecting** to parts of it — so the rule text is contested. **I did not obtain or read the normative annexes.** | Obtain the consolidated text + technical annexes from ANCPI/legislatie.just.ro. §4.3 is modelled on INSPIRE Cadastral Parcels (the EU-level frame Romania must satisfy anyway), not on the Romanian annexes. |
| U9 | **INSPIRE Reg. 1205/2008 metadata element *list*** | I cited the Cadastral Parcels Technical Guidelines' own description of the elements but did not enumerate the full Reg. 1205/2008 Annex list. | EUR-Lex + the Cadastral Parcels dataspecification PDF. |
| U10 | **SedonaDB / DuckDB spatial benchmark numbers** | Single third-party benchmark (M3 Mac, 8-CPU Docker) **[DOC]**, not authoritative. | SpatialBench (Apache Sedona) for comparable numbers. |

---

## 13. Source index (all fetched or live-probed this session)

**Specs & official docs**
- GeoPackage 1.4.0: https://docs.ogc.org/is/12-128r19/12-128r19.html · portal https://geopackage.org/spec/
- GeoPackage FAQ (why SQLite; media type): https://geopackage.org/spec/
- GDAL (Geo)Parquet driver: https://gdal.org/en/stable/drivers/vector/parquet.html
- GDAL GTI + STAC GeoParquet: https://gdal.org/en/stable/drivers/raster/gti.html
- GDAL STACIT / STACTA: https://gdal.org/en/stable/drivers/raster/stacit.html · https://gdal.org/en/stable/drivers/raster/stacta.html
- GDAL PMTiles driver: https://gdal.org/en/stable/drivers/vector/pmtiles.html
- GeoParquet spec 1.1.0: https://geoparquet.org/releases/v1.1.0 · 2.0.0-rc.1: https://geoparquet.org/releases/v2.0.0-rc.1
- Apache Parquet native geospatial types: https://parquet.apache.org/blog/2026/02/13/native-geospatial-types-in-apache-parquet
- GeoArrow: https://geoarrow.org · extension types https://geoarrow.org/extension-types.html
- Cloud-Optimized Geospatial Formats Guide (GeoParquet/FlatGeobuf/COG/COPC/Zarr): https://guide.cloudnativegeo.org/geoparquet
- PMTiles spec: https://github.com/protomaps/PMTiles · v3 https://protomaps.com/blog/pmtiles-v3-hilbert-tile-ids
- OGC 3D Tiles 1.1 (22-025r4): https://docs.ogc.org/cs/22-025r4/22-025r4.html · https://github.com/CesiumGS/3d-tiles
- CityJSON 2.0.2: https://www.cityjson.org/specs
- OGC API - Records Part 1 Core (20-004r1): https://docs.ogc.org/is/20-004r1/20-004r1.html · https://github.com/opengeospatial/ogcapi-records
- OGC API - Common Part 1 (19-072): https://docs.ogc.org/is/19-072/19-072.html
- OGC API - Features Part 1 (17-069r4): https://docs.ogc.org/is/17-069r4/17-069r4.html
- STAC: https://stacspec.org · stac-fastapi https://stac-utils.github.io/stac-fastapi · stac-index https://stacindex.org/ecosystem
- INSPIRE Cadastral Parcels dataspec: https://inspire-mif.github.io/technical-guidelines/data/cp/dataspecification_cp.pdf · https://knowledge-base.inspire.ec.europa.eu/data-specifications-technical-guidelines_en
- INSPIRE DQ Reg. 1313/2014: https://eur-lex.europa.eu/eli/reg_impl/2014/1313/oj/eng
- W3C PROV-O: https://www.w3.org/TR/prov-o · PROV-JSONLD (Submission): https://www.w3.org/submissions/2024/SUBM-prov-jsonld-20240825
- SQLite file locking: https://www.sqlite.org/lockingv3.html
- ISO 19157-1:2023 listing: https://standards.iteh.ai/catalog/standards/cen/503b6561-8220-4d0a-8493-e7b2c89559dc/en-iso-19157-1-2023 · ISO OBP https://www.iso.org/obp/ui#iso:std:iso:19157:ed-1:v1:en
- ISO/AWI 25082-2: https://www.iso.org/standard/93504.html
- Shapely predicates (`is_valid_reason`): https://shapely.readthedocs.io/en/latest/predicates.html
- DuckDB spatial: https://duckdb.org/docs/current/core_extensions/spatial/overview.html
- PostGIS releases: https://postgis.net/news · 3.5.4 https://postgis.net/2025/10/PostGIS-3.5.4
- PostGIS/GEOS coverage cleaning: https://www.crunchydata.com/blog/2025-postgis-and-geos-release
- Apache SedonaDB: https://github.com/apache/sedona-db · 2025 review https://sedona.apache.org/latest/blog/2026/01/11/apache-sedona-2025-year-in-review
- uv: https://docs.astral.sh/uv · pixi: https://prefix.dev/blog/pixi_for_scientists
- mutmut: https://mutmut.readthedocs.io · cosmic-ray: https://cosmic-ray.readthedocs.io
- qgis-plugin-ci: https://github.com/qgis/qgis-plugin-ci · https://qgis.github.io/qgis-plugin-ci/
- QGIS install guide (LTR table, container images, Nix): https://qgis.org/resources/installation-guide/
- PyQGIS testing & CI: https://pyqgis.com/qgis-plugin-development/testing-and-ci-for-plugins
- pytest-qgis: https://github.com/osgeosuomi/pytest-qgis
- DVC joins lakeFS: https://dvc.org/blog/dvc-joins-lakefs-your-questions-answered · https://www.prnewswire.com/news-releases/lakefs-acquires-dvc-uniting-data-version-control-pioneers-to-accelerate-ai-ready-data-302618339.html

**Publications**
- XLRS-Bench (CVPR 2025, Highlight): https://cvpr.thecvf.com/virtual/2025/poster/35068
- GeoLLaVA-8K (NeurIPS 2025): https://proceedings.neurips.cc/paper_files/paper/2025/file/e95ef5c6ed4096c609e0b8b47ffaeb9b-Paper-Conference.pdf
- CHOICE (RS-VLM benchmark): https://arxiv.org/html/2411.18145v4
- SpaceNet 2 buildings: https://spacenet.ai/spacenet-buildings-dataset-v2
- Element 84, building-footprint evaluation metrics: https://element84.com/software-engineering/automated-building-footprintextraction-evaluation-metrics
- Exact Tile-Based Segmentation Inference: https://pmc.ncbi.nlm.nih.gov/articles/PMC10914126
- Tile size/overlap study, aerial road segmentation: https://www.mdpi.com/2072-4292/16/16/2954
- Flip-n-Slide (ICLR 2024 W): https://ml-for-rs.github.io/iclr2024/camera_ready/papers/13.pdf
- ASPRS Positional Accuracy Standards Ed.2 v2 (2024) announcement: https://old.asprs.org/archives/asprs-approves-edition-2-version-2-of-the-asprs-positional-accuracy-standards-for-digital-geospatial-data-2024.html · overview https://lidarmag.com/2025/06/30/overview-of-the-asprs-positional-accuracy-standards-for-digital-geospatial-data
- USGS adoption of ASPRS 2024: https://www.usgs.gov/ngp-standards-and-specifications/adopt-updated-accuracy-standards
- NOAA/NGS RT User Guidelines: https://www.ngs.noaa.gov/PUBS_LIB/NGSRealTimeUserGuidelines.v2.1.pdf
- ICSM adjustment/evaluation guideline: https://www.landgate.wa.gov.au/siteassets/documents/location-data-and-services/surveying/guideline-for-adjustment-and-evaluation-of-survey-control_v2.2.pdf
- GNSS coverage factors (1.960 / 2.448): https://usq.pressbooks.pub/gpsandgnss/chapter/6-3-gnss-accuracy
- BEV calibration, ECE + reliability diagrams: https://ml4ad.github.io/files/papers2022/Calibrated%20Perception%20Uncertainty%20Across%20Objects%20and%20Regions%20in%20Bird's-Eye-View.pdf
- Per-image calibration in segmentation: https://arxiv.org/html/2506.03942v1
- SANDIA confidence-calibration metrics: https://www.osti.gov/servlets/purl/2430119
- mutation-testing tool comparison: https://par.nsf.gov/servlets/purl/10573281
- Ordinul ANCPI 600/2023 (portal legislativ): https://legislatie.just.ro/Public/DetaliiDocumentAfis/268229 · UGR public letter: http://www.ugr.ro/cms/storage/uploads/2023/02/20/63f379e083ddfScrisoare-publica_ODG_600_2023.pdf

**Local probes (this session, reproducible)**
- `ogrinfo --formats` (QGIS 3.40.0 / GDAL 3.9.3): Parquet, Arrow, FlatGeobuf, PMTiles, MVT, GPKG, DXF, JSONFG all present
- `qgis_process list`: `native:fixgeometries`, `native:coveragevalidate`, `native:deleteduplicategeometries`, `qgis:checkvalidity` (+ iface crash traceback)
- `C:\Program Files\QGIS 3.40.0\apps\Python312\Lib\site-packages\osgeo_utils\samples\`: validate_gpkg.py (113,359 B), validate_geoparquet.py (20,540 B), validate_cloud_optimized_geotiff.py (18,476 B), validate_jp2.py (70,659 B)
- `git count-objects -vH`: 132.12 MiB pack, **6.16 GiB garbage**
- PyPI version + `requires_python` probe: 16 packages
- Docker Hub tag audit: `qgis/qgis` 2026-09-27 (ltr/stable); `osgeo/gdal` **2023-03-12 (abandoned)**
- GitHub releases API: gdal 3.13.3 (2026-08-18), geoparquet 2.0.0-rc.1 (2026-07-19), qgis-plugin-ci 2.10.0 (2026-05-18), uv 0.12.23, pixi v0.81.0
- conda-forge gdal: up to 3.13.3
