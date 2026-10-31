---
id: H-005
type: handoff
status: proposed
author: claude-opus-5.5
source_type: measured
sources:
  - path: compute/colab/scripts/vlm_roof_assist.py, vlm_chips.py, vlm_merge_finish.py
  - path: workspace/colab_runs/vlm_v1..vlm_v3 (vlm_report.json)
  - path: workspace/reviews/cladiri_2d_vlm_final_epsg3844.gpkg
confidence: medium
created: 2026-10-31
recheck_by: 2027-01-31
cssclasses:
  - note-handoff
supersedes: []
---
# H-005 Qwen3-VL-8B roof assistant, three QGIS-checked loops (follows [[H-004-roof2d-qgis-reviewed-loops-20261030]])

The owner asked for VLM help, two states (admis / incert), a roof type per building, missing buildings and eave-tight outlines. The method reuses the unmerged B1 design (`5ce4746`).

- VLM1, zero-shot. Agreement with the owner was 0.567 (always-ADMIS scores 0.761). ADMIS precision 0.88, ELIMINAT recall 0. QGIS showed tree crowns kept as new buildings and pitched roofs called flat [CALC: vlm_v1/vlm1/vlm_report.json].
- VLM2, LoRA on owner verdicts plus 160 LiDAR+foliage tree chips. Owner-val agreement 0.569. 95 % of tree chips are rejected (optimistic: they include training chips). New candidates fell from 192 to 30. QGIS showed the LoRA broke hip-roof recognition.
- VLM3: roof type from the base model with the adapter off, a robust LiDAR flat test (p90−p10 < 0.8 m) and an ADMIS_PROPUS threshold of 0.3. At 0.3 the VLM recovers 90.5 % of owner ADMIS roofs at 0.82 precision on the owner set (owner-val agreement 0.611).
- Result: 451 buildings, 328 ADMIS_PROPUS and 123 INCERT, 31 new LiDAR-found buildings, 82 % of buildings with edges snapped to the eave. VLM flat-roof calls agree with LiDAR 91.5 %. Roof types: 186 DOUA_APE, 117 TERASA_PLAT, 79 COMPLEX, 60 O_APA, 7 PATRU_APE, 2 ALTUL.

QGIS check: the hip roof near OPT_B_144 and the flat roofs at OPT_B_068 are right. The chapel dome is called PATRU_APE, and one false positive on the construction site is ADMIS_PROPUS.

Status: ADMIS_PROPUS is advice; owner_verdict stays PENDING_OWNER_REVIEW.
