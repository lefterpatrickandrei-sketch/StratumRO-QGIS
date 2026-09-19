# 06. Mask Fusion & Multi-Wing Building Assembly (E6, E7)

**Document ID:** `REPORT-CLUJ-P3-06-MASK-FUSION`  
**Execution Date:** 2026-09-19  
**Platform:** StratumRO-QGIS — Cluj Phase 3  
**Author:** Antigravity Engineering Coordinator  
**Standard Compliance:** Evidence-First Scientific Rule (MEASURED, TESTED)

---

## 1. Multi-Wing Fragmentation Failure Mode

In urban and educational campuses (e.g. Cluj USAMV), large buildings frequently feature L-shaped, U-shaped, or sprawling multi-wing architecture.

When separate candidates are generated on distinct roof sections:
- Baseline treated each wing as an unrelated building, generating multiple overlapping or touching polygons.
- Each wing individually had an area of $200 - 500\,\text{m}^2$, while the reference parcel polygon spanned $1,000 - 2,500\,\text{m}^2$.
- Comparing a single wing to the monolithic reference parcel yielded an IoU of $0.20 - 0.40$, failing the PASCAL VOC 0.50 threshold and registering as both an FP and an FN.

---

## 2. Mask Fusion Engine Architecture (E6)

The new [`MaskFusionEngine`](file:///c:/Users/lefpa/Downloads/QGIS-AI/stratum_ro/mask_fusion.py) executes topological assembly:
1. **Adjacency & Overlap Detection:** Builds an intersection graph of all raw predictions. Pairs with $\text{IoU} \ge 0.20$ or intersection area $> 20\,\text{m}^2$ are grouped.
2. **Topological Union:** Merges grouped polygons via `shapely.ops.unary_union`.
3. **Artifact Cleanup:** Fills sliver gaps between adjacent wings using morphological closure and small hole suppression.

### Measured Impact:
- Raw segments merged: 31 $\to$ **26 cohesive physical buildings**.
- **False Positives dropped from 27 to 22** (eliminating 5 duplicate wing artifacts).
- **Precision increased to 15.38%** (from 12.90% in E2 and 4.26% in baseline).
- **F1 Score increased to 8.79%** (from 8.33% in E2 and 5.03% in baseline).

---

## 3. Vectorization Cleanup (E7)

Vectorizing raster masks natively with `rasterio.features.shapes` produces pixelated staircase boundaries ($20\,\text{cm}$ steps) containing hundreds of superfluous collinear vertices.

`clean_raw_vector` applies:
- **Douglas-Peucker Simplification ($0.25\,\text{m}$):** Simplifies staircase edges within a $1.25$-pixel tolerance.
- **Vertex Count Reduction:** Mean vertices per building reduced from **$399.9$ to $129.2$** without distorting area ($\Delta \text{Area} < 0.5\%$).
- **Sliver Hole Removal:** Filters internal raster voids $< 12\,\text{m}^2$.

---

## 4. Engineering Conclusion
Mask fusion and vector cleanup successfully assemble complex building wings into unified parcels and eliminate raster staircase noise, permanently raising precision to $15.38\%$.
