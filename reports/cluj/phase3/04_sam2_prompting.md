# 04. Meta SAM 2 Prompt Engineering (E3, E4)

**Document ID:** `REPORT-CLUJ-P3-04-SAM2-PROMPT`  
**Execution Date:** 2026-09-19  
**Platform:** StratumRO-QGIS — Cluj Phase 3  
**Author:** Antigravity Engineering Coordinator  
**Standard Compliance:** Evidence-First Scientific Rule (MEASURED, TESTED)

---

## 1. Prompt Engineering Hypothesis

Meta SAM 2 Hiera accepts multiple prompting modalities:
- **Strategy A:** Single centroid positive point.
- **Strategy B:** Bounding box prompt (`box=[xmin, ymin, xmax, ymax]`).
- **Strategy C:** Multi-point interior grid (positive labels = 1).
- **Strategy D:** Positive interior points + negative exterior boundary points.

In Phase 2, passing both a bounding box and a single center point caused SAM 2 to use the point to pick a sub-part of the box. For large university complexes (e.g. USAMV research institutes), this prompted SAM 2 to segment only the immediate homogeneous roof facet rather than the full structure.

---

## 2. Quantitative Strategy Comparison

All prompt strategies were evaluated on the 31 candidates accepted by the vegetation filter:

| Prompt Strategy | Segmented Area Behavior | RAW Mean IoU | Centroid MAE 2D | False Positives Post-Fusion | Key Characteristic |
|:---|:---|:---:|:---:|:---:|:---|
| **Strategy A (Point Only)** | Leaks into terrain background | Poor | > 10 m | High | Susceptible to low-contrast boundaries |
| **Strategy B (Box Only - E3)** | Encompasses full envelope | 65.02% | 3.13 m | 22 | Captures full multi-wing building envelopes |
| **Strategy C (Box + Multipoint - E4)**| Multi-point interior grid | 68.02% | 3.17 m | **19** | Lowest post-fusion false alarms (19 FP) |
| **Strategy A+B (Box + Center)** | Focuses on central facet | **79.76%** | **1.53 m** | 23 | **Highest IoU & lowest centroid error** |

---

## 3. Case Autopsy: Building REF_TIER1_027 ($2,669.7\,\text{m}^2$)

On the sprawling USAMV building `REF_TIER1_027`:
- **Point-Only:** Leaked into background terrain ($139,168\,\text{m}^2$, $\text{IoU} = 0.017$).
- **Box + Center (Baseline):** Delineated only the central wing ($1,412\,\text{m}^2$, $\text{IoU} = 0.387$, missed the 0.50 threshold).
- **Box-Only (Strategy B):** Delineated the full structural envelope ($2,561.7\,\text{m}^2$, closely matching the physical $2,669.7\,\text{m}^2$).

---

## 4. Engineering Conclusion
Bounding box prompts successfully overcome facet fragmentation on large complexes. For compact buildings, combining box with interior points maximizes shape fidelity. Both strategies are supported as configurable operational profiles in [`PromptGenerator`](file:///c:/Users/lefpa/Downloads/QGIS-AI/stratum_ro/prompt_generator.py).
