# STRATUMRO — FINAL CORE REPOSITORY MAP (PHASE 3)

**Status:** `EXTRACTED, ISOLATED & VERIFIED`  
**QGIS Dependencies in Core:** `0`  
**AI/LLM Dependencies in Core:** `0`  

```text
stratum_ro/core/
├── __init__.py           # Master export for Core API
├── geometry/
│   ├── __init__.py
│   ├── regularizer.py    # 90° regularization, acute spikes removal
│   ├── cleaning.py       # CoreGeometryEngine implementing IGeometryEngine
│   └── metrics.py        # IoU, Hausdorff, Boundary RMSE, Centroid shift
├── geodesy/
│   ├── __init__.py
│   ├── crs.py            # CoreCRSManager implementing ICRSManager
│   └── transformer.py    # CoreTransformer implementing ITransformer (always_xy=True)
├── qa_qc/
│   ├── __init__.py
│   └── validator.py      # CoreGeometryValidator implementing IValidator
├── raster/
│   ├── __init__.py
│   └── reader.py         # CoreRasterReader (rasterio windowed reading & diff)
└── pointcloud/
    ├── __init__.py
    └── processor.py      # CorePointCloudReader (laspy reading & filtering)
```

---

## DEPENDENCY DIRECTION COMPLIANCE (§70)

```text
CLIENT (QGIS / Web / CLI)
      ↓
ADAPTER (IQgisAdapter)
      ↓
WORKFLOW (TaskGraph)
      ↓
DOMAIN (cadastre_ro, topography, city_3d)
      ↓
CORE (geometry, geodesy, qa_qc, raster, pointcloud)
```
