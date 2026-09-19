# Experiment Analysis — EXP_001: Candidate Generation Optimization

## 1. Hypothesis
Morphological closing ($5\times 5$) and binary hole filling consolidates fragmented rooftop facets and eliminates interior skylight/mechanical voids, reducing spuriously split candidates.

## 2. Quantitative Results
- **Candidates Generated:** 75 (Baseline: 94)
- **Predictions Segmented:** 75 (Baseline: 94)
- **Detection (RAW):**
  - TP: 4 (Baseline: 4)
  - FP: 71 (Baseline: 90)
  - FN: 61 (Baseline: 61)
  - Precision: 5.33% (Baseline: 4.26%)
  - Recall: 6.15% (Baseline: 6.15%)
  - F1: 5.71% (Baseline: 5.03%)
- **Segmentation (RAW):**
  - Mean IoU: 70.47% (Baseline: 69.52%)

## 3. Finding
Candidate consolidation reduced blob fragmentation from 94 to 75. However, vegetation false positives remain dominant without multimodal filtering.
