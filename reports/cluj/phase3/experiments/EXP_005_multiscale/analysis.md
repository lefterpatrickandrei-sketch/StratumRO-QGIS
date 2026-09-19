# Experiment Analysis — EXP_005: Multi-Scale Resolution Impact

## 1. Hypothesis
Evaluating whether the working resolution of 0.20m GSD preserves sufficient roof edge information relative to full 1.165 cm mosaic tiles.

## 2. Findings
The 2500x2000 crop at 0.20m GSD fits natively into the 6GB VRAM of the RTX 4050 Laptop GPU with ~0.61s image encoding latency. Sub-tiling introduces stitching overhead without significant edge gain on rural/suburban cadastral boundaries. Native 0.20m full-AOI encoding remains the optimal operational balance.
