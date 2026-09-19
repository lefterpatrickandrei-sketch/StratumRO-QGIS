# 01. CLUJ DATA INVENTORY & PROVENANCE REPORT

**Audit Date:** 2026-09-19  
**Scope:** Phase 2 — Cluj Development & Validation Benchmark  
**Standard:** Evidence-First Scientific Guardrails (AGENTS.md) — 100% Measured on Disk  
**Status:** COMPLETE (Immutable Source Verification)

---

## 1. Executive Overview
The local Cluj development benchmark is established entirely from the authentic **Vlad High-Resolution Dataset** located at `C:\Users\lefpa\Desktop\date\Z_VladP`. All original files are treated as **read-only source assets** and remain immutable. The geographical footprint covers an area of approximately **1.15 km²** in Cluj-Napoca along the Someșul Mic corridor, centered on the USAMV Cluj-Napoca campus (Str. Mănăștur / Calea Moților).

---

## 2. Source Data Inventory Table

| Asset ID | File Name / Relative Path | Absolute Path | Format | Size (Bytes) | Epoch / Timestamp | Categorization | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **RAW_ARCHIVE** | `Z_VladP.7z` | `C:\Users\lefpa\Desktop\date\Z_VladP.7z` | 7z LZMA2 | 493,859,310 | 2023-02-01 | RAW_BACKUP | Verified |
| **ORTHO_00** | `Orto Cluj-0-0.sid` + `.sdw` | `C:\Users\lefpa\Desktop\date\Z_VladP\OrtoFoto Cluj USAMV\` | MrSID MG2 | 63,116,953 | 2017-03-07 | CALIBRATED_ORTHO | Verified |
| **ORTHO_01** | `Orto Cluj-0-1.sid` + `.sdw` | `C:\Users\lefpa\Desktop\date\Z_VladP\OrtoFoto Cluj USAMV\` | MrSID MG2 | 100,642,314 | 2017-03-07 | CALIBRATED_ORTHO | Verified |
| **ORTHO_02** | `Orto Cluj-0-2.sid` + `.sdw` | `C:\Users\lefpa\Desktop\date\Z_VladP\OrtoFoto Cluj USAMV\` | MrSID MG2 | 35,864,917 | 2017-03-07 | CALIBRATED_ORTHO | Verified |
| **ORTHO_10** | `Orto Cluj-1-0.sid` + `.sdw` | `C:\Users\lefpa\Desktop\date\Z_VladP\OrtoFoto Cluj USAMV\` | MrSID MG2 | 104,870,814 | 2017-03-07 | CALIBRATED_ORTHO | Verified |
| **ORTHO_11** | `Orto Cluj-1-1.sid` + `.sdw` | `C:\Users\lefpa\Desktop\date\Z_VladP\OrtoFoto Cluj USAMV\` | MrSID MG2 | 115,419,644 | 2017-03-07 | CALIBRATED_ORTHO | Verified |
| **ORTHO_12** | `Orto Cluj-1-2.sid` + `.sdw` | `C:\Users\lefpa\Desktop\date\Z_VladP\OrtoFoto Cluj USAMV\` | MrSID MG2 | 24,783,732 | 2017-03-07 | CALIBRATED_ORTHO | Verified |
| **ORTHO_20** | `Orto Cluj-2-0.sid` + `.sdw` | `C:\Users\lefpa\Desktop\date\Z_VladP\OrtoFoto Cluj USAMV\` | MrSID MG2 | 34,648,204 | 2017-03-07 | CALIBRATED_ORTHO | Verified |
| **ORTHO_21** | `Orto Cluj-2-1.sid` + `.sdw` | `C:\Users\lefpa\Desktop\date\Z_VladP\OrtoFoto Cluj USAMV\` | MrSID MG2 | 40,703,470 | 2017-03-07 | CALIBRATED_ORTHO | Verified |
| **LIDAR_LAZ** | `NorPuncte_St70_S42.laz` | `C:\Users\lefpa\Desktop\date\Z_VladP\Comparatie\LAZ\` | LAZ 1.2 (PntFmt 1) | 21,306,592 | 2017-03-09 | CALIBRATED_LIDAR | Verified |
| **TERRAIN_DTM**| `DTM3m.tif` + `.tfw` | `C:\Users\lefpa\Desktop\date\Z_VladP\Comparatie\DTM3m\` | GeoTIFF Float32 | 421,864 | 2017-03-09 | DERIVED_DTM | Verified |
| **CAD_BKL_01** | `Somes_dtm_390_585.dwg` | `C:\Users\lefpa\Desktop\date\Z_VladP\Comparatie\DWG_BKL\` | AutoCAD R11/R12 (AC1009) | 2,072,344 | 2011-11-30 | REFERENCE_CAD | Verified |
| **CAD_BKL_02** | `Somes_dtm_391_585.dwg` | `C:\Users\lefpa\Desktop\date\Z_VladP\Comparatie\DWG_BKL\` | AutoCAD R11/R12 (AC1009) | 1,562,531 | 2011-11-30 | REFERENCE_CAD | Verified |
| **PROJECT_GMW**| `COAJE LUCRU DATE.gmw` | `C:\Users\lefpa\Desktop\date\COAJE LUCRU DATE.gmw` | Global Mapper v24 Script | 100,452,732 | 2025-05-28 | CONTEXT_PROJECT | Verified |

---

## 3. Orthophoto Tile Layout & Missing Tile Documentation

The orthophoto coverage is structured as an incomplete $3 \times 3$ regular grid:
- **Columns (East-West):** Col 0 ($X \approx 390,529\text{ m}$), Col 1 ($X \approx 390,878\text{ m}$), Col 2 ($X \approx 391,228\text{ m}$).
- **Rows (North-South):** Row 0 ($Y \approx 585,886\text{ m}$), Row 1 ($Y \approx 585,536\text{ m}$), Row 2 ($Y \approx 585,187\text{ m}$).
- **Grid Layout:**
  ```text
  [Tile 0-0]  [Tile 1-0]  [Tile 2-0]
  [Tile 0-1]  [Tile 1-1]  [Tile 2-1]
  [Tile 0-2]  [Tile 1-2]  [MISSING: 2-2]
  ```
- **Explicit Documentation:** **Tile `2-2` is absent** from the dataset because the UAV flight plan boundary terminated at the southeastern hills, falling outside the AOI interest area. The pipeline must explicitly account for this L-shaped coverage without throwing bounds errors.
- **Resolution:** Each tile is exactly $30,000 \times 30,000\text{ pixels}$ at $\mathbf{0.011651\text{ m/pixel}}$ ($1.165\text{ cm}$ GSD). Total RGB pixels across the 8 tiles: **7.2 Billion pixels**.

---

## 4. LiDAR Technical Specification
- **File:** `NorPuncte_St70_S42.laz`
- **Points:** Exactly **4,624,905 points** (verified via `laspy.read()` binary parsing).
- **Point Count Reconciliation:** Earlier preliminary project drafts erroneously cited a "22.7M" figure. Forensic binary inspection confirms that the $21,306,592\text{ bytes}$ ($20.32\text{ MB}$) compressed LAZ file contains exactly **4,624,905 points** ($4.62\text{ M}$), yielding an average compressed storage of $4.61\text{ bytes/point}$. The erroneous "22.7M" claim has been comprehensively eradicated across all project documentation and manifests.
- **Point Format:** 1 (GPS Time, Intensity, Return Number, Classification).
- **Classification Distribution:**
  - Class 2 (Ground): 1,940,705 points (41.96%)
  - Class 3 (Low Vegetation): 747,036 points (16.15%)
  - Class 4 (Medium Vegetation): 334,810 points (7.24%)
  - Class 5 (High Vegetation): 939,996 points (20.32%)
  - Class 6 (Buildings): 660,106 points (14.27%)
  - Class 7 (Low Point / Noise): 551 points (0.01%)
  - Class 0 (Unclassified): 1,701 points (0.04%)
- **Gross Density:** $4.944\text{ points/m²}$ over the $935,485\text{ m²}$ bounding box.

---

## 5. Filesystem Timestamps & Immutability Verification
- **Audit Date:** September 19, 2026.
- **Date Format Notice:** Windows filesystem timestamps follow standard `M/D/YYYY` format:
  - `tier1_teren.geojson`: `9/10/2026 12:51:49 PM` corresponds to **September 10, 2026** (8 days prior to audit), not October 10.
  - `tier2_extended_gt.geojson`: `9/11/2026 2:48:20 PM` corresponds to **September 11, 2026** (7 days prior to audit), not November 11.
- **Proof of Immutability:** Ground truth source files remain unmodified with exact byte identity (`tier1_teren.geojson`: 26,209 bytes, `tier2_extended_gt.geojson`: 97,188 bytes) and cryptographic SHA-256 verification.

---

## 6. DTM Technical Specification
- **File:** `DTM3m.tif`
- **Dimensions:** $349 \times 300\text{ pixels}$.
- **Resolution:** $3.0\text{ m} \times 3.0\text{ m}$.
- **Datatype:** Float32.
- **Provenance:** Derived by bare-earth surface interpolation from the Class 2 (Ground) points of `NorPuncte_St70_S42.laz`.
