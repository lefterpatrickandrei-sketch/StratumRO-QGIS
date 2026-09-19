# Experiment Analysis — EXP_007: Vectorization Cleanup

## 1. Hypothesis
Douglas-Peucker simplification (0.25m ~ 1.25 pixels) eliminates raster staircase perimeter artifacts while preserving physical corners.

## 2. Quantitative Results
- **Cleaned Polygons:** 26
- **Vertex Count:** 129.2 vertices/building
- **Detection:** TP=4, FP=22, FN=61
- **Mean IoU:** 66.72%
