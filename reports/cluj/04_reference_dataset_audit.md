# 04. REFERENCE DATASET AUDIT & DEDUPLICATION REPORT

**Audit Date:** 2026-09-19  
**Scope:** Reference Data Lineage, Deduplication, and Derived Benchmark Structure  
**Standard:** Evidence-First Scientific Guardrails (AGENTS.md)

---

## 1. Executive Summary
The project previously reported an inflated evaluation count of **179 buildings**. A forensic spatial intersection audit proved that the 150-feature `data/ground_truth/tier2_extended_gt.geojson` file contained the 29 features of `tier1_teren.geojson` in its first 29 rows with an exact $\text{IoU} = 1.000$. Summing $29 + 150 = 179$ counted the 29 validated primary buildings twice. 

In this phase, without altering or overwriting the original files, we established a **derived, strictly disjoint reference structure**:
- **Tier 1 (Primary Ground-Truth):** 29 buildings (Terrestrial cadastral survey validated).
- **Tier 2 (Complementary Reference):** 121 buildings (Deduplicated expert digitization).
- **Total Unique Benchmark Features:** **Exactly 150 unique structures**.

---

## 2. Duplicate Identification Evidence

A pairwise geometric intersection between `tier1_teren.geojson` and `tier2_extended_gt.geojson` was executed on the metric geometry:

$$\text{IoU}_{i,j} = \frac{\text{Area}(T1_i \cap T2_j)}{\text{Area}(T1_i \cup T2_j)}$$

### Findings Table (Sample of First 10 Pairs):

| Tier 1 Index | Tier 1 ID | Tier 2 Index | Tier 2 ID | Overlap Area (m²) | IoU | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `0` | `REF_TIER1_001` | `0` | `EXT_GT_001` | 294.61 m² | **1.0000** | **DUPLICATE** |
| `1` | `REF_TIER1_002` | `1` | `EXT_GT_002` | 1257.34 m²| **1.0000** | **DUPLICATE** |
| `2` | `REF_TIER1_003` | `2` | `EXT_GT_003` | 1569.02 m²| **1.0000** | **DUPLICATE** |
| `3` | `REF_TIER1_004` | `3` | `EXT_GT_004` | 1790.81 m²| **1.0000** | **DUPLICATE** |
| `4` | `REF_TIER1_005` | `4` | `EXT_GT_005` | 1442.70 m²| **1.0000** | **DUPLICATE** |
| `5` | `REF_TIER1_006` | `5` | `EXT_GT_006` | 1126.83 m²| **1.0000** | **DUPLICATE** |
| `6` | `REF_TIER1_007` | `6` | `EXT_GT_007` | 818.32 m² | **1.0000** | **DUPLICATE** |
| `7` | `REF_TIER1_008` | `7` | `EXT_GT_008` | 448.59 m² | **1.0000** | **DUPLICATE** |
| `8` | `REF_TIER1_009` | `8` | `EXT_GT_009` | 148.47 m² | **1.0000** | **DUPLICATE** |
| `9` | `REF_TIER1_010` | `9` | `EXT_GT_010` | 114.68 m² | **1.0000** | **DUPLICATE** |

*All 29 indices ($0$ through $28$) in Tier 2 matched Tier 1 with $\text{IoU} = 1.000$.*

---

## 3. Derived Clean Benchmark Structure

To ensure 100% reproducibility while maintaining complete immutability of the source data, the clean benchmark layers were exported to `data/derived_reference/`:

1. **`data/derived_reference/tier1_primary_29.geojson`**
   - 29 features with tag `benchmark_tier: TIER1_PRIMARY_SURVEY`.
   - Used for primary high-confidence geodetic evaluation (centimeter-level survey ground truth).
2. **`data/derived_reference/tier2_additional_121.geojson`**
   - 121 features with tag `benchmark_tier: TIER2_COMPLEMENTARY_REFERENCE`.
   - Used for extended spatial coverage and AOI-wide recall assessment.
3. **`data/derived_reference/cluj_combined_unique_150.geojson`**
   - Exactly 150 unique features indexed from `CLUJ_REF_001` to `CLUJ_REF_150`.
   - Zero internal overlaps or duplicates.

---

## 4. Immutability Verification
- Original file `data/ground_truth/tier1_teren.geojson` SHA-256 remains unmodified.
- Original file `data/ground_truth/tier2_extended_gt.geojson` SHA-256 remains unmodified.
- The 179-building count is officially archived as a historical artifact caused by duplicate concatenation.
