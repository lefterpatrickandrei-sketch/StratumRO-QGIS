# 02. Candidate Generation & Morphological Optimization (E1)

**Document ID:** `REPORT-CLUJ-P3-02-CANDIDATE-GEN`  
**Execution Date:** 2026-09-19  
**Platform:** StratumRO-QGIS — Cluj Phase 3  
**Author:** Antigravity Engineering Coordinator  
**Standard Compliance:** Evidence-First Scientific Rule (MEASURED, TESTED)

---

## 1. Candidate Generation Problem in Baseline

In Phase 2, candidates were derived from the nDSM using a raw height threshold ($h \ge 2.5\,\text{m}$) and 8-connectivity blob labeling (`scipy.ndimage.label`).

### Critical Flaws Identified:
1. **Rooftop Void Splitting:** Rooftop HVAC units, vents, or sloped shadows caused localized drops below $2.5\,\text{m}$, fragmenting single physical buildings into multiple disjoint blobs.
2. **Narrow Spurious Peaks:** Small clusters of foliage above $2.5\,\text{m}$ passed the naive $25\,\text{m}^2$ area threshold without morphological validation.
3. **Internal Skylight Voids:** Holes inside roof planes disrupted centroid calculation, causing prompt coordinates to land inside courtyards rather than roof surfaces.

---

## 2. Experimental Design (E1)

The new [`CandidateGenerator`](file:///c:/Users/lefpa/Downloads/QGIS-AI/stratum_ro/candidate_generator.py) evaluated five morphological kernels on the 0.20m GSD grid:

| Kernel Configuration | Total Blobs | Blobs $\ge 25\,\text{m}^2$ | Candidate Redundancy Impact |
|:---|:---:|:---:|:---|
| **Raw (No Morphology - Baseline)** | 835 | 94 | High fragmentation |
| **Binary Hole Filling Only** | 779 | 94 | Eliminates internal skylights |
| **Closing $3\times 3$ ($0.6\,\text{m}$)** | 701 | 83 | Merges small roof gaps |
| **Closing $5\times 5$ ($1.0\,\text{m}$) + Hole Fill** | **542** | **75** | **Optimal consolidation** |
| **Opening $3\times 3$ + Closing $5\times 5$** | 400 | 80 | Prunes fine vegetation tendrils |

---

## 3. Measured Results (EXP_001)

Applying **Closing $5\times 5$ + Binary Hole Filling** produced:
- **Candidates Generated:** 75 (down from 94, a **20.2% reduction in candidate noise**)
- **True Positives (TP):** 4 (100% preservation of valid buildings)
- **False Positives (FP):** 71 (reduced from 90)
- **Precision:** $5.33\%$ (improved from $4.26\%$)
- **Mean IoU:** **$71.30\%$** regularized (improved from $70.37\%$)
- **Centroid MAE 2D:** **$2.32\,\text{m}$** (improved from $2.49\,\text{m}$)

---

## 4. Engineering Conclusion
Morphological closing ($5\times 5$) and hole filling are verified positive interventions. They solve rooftop fragmentation and are permanently incorporated into the candidate generator.
