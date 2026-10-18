# STRATUMRO — SUBSYSTEM 4: RASTER CORE EXTRACTION REPORT

**Subsystem:** Core Raster I/O & Windowed Slicing  
**Status:** `EXTRACTED & VERIFIED`  
**Date:** 2026-09-20  

---

## 1. COMPONENTE EXTRASE
- **Pachet Țintă:** `stratum_ro/core/raster/`
- **Module Create:**
  1. `stratum_ro/core/raster/reader.py` (`RasterMetadata`, `CoreRasterReader`, windowed reading, difference computation).
  2. `stratum_ro/core/raster/__init__.py`

## 2. AUDIT DEPENDENȚE
- **Dependențe:** `rasterio`, `numpy`
- **Dependență QGIS:** `ZERO` (Pure Python)
- **Dependență Domeniu:** `ZERO` (I/O Raster pur, fără modele de clădiri)
