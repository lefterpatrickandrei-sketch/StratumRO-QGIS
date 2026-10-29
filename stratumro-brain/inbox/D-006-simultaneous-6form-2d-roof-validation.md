---
id: D-006
type: decision
status: proposed
author: antigravity
source_type: owner
sources:
  - path: stratum_ro/core/qa_qc/simultaneous_2d_validator.py (commit e31f00d)
  - path: tools/deduplicate_and_audit_opera_review.py (commit e31f00d)
  - path: compute/colab/jobs/continuous_2d_a100.yaml (commit e31f00d)
confidence: high
created: 2026-10-29
recheck_by: 2027-04-29
cssclasses:
  - note-decision
supersedes: []
---
# D-006 Phase 1 2D RGB Roof Extraction and Simultaneous 6-Form Validation (PROPOSED)

Decision (one sentence): Decouple Phase 1 (2D roof shape extraction from 3-channel RGB orthophotos, generalizable to any UAT/zone without LiDAR heights) from Phase 2 (3D LOD1/LOD2 reconstruction with heights), rename `CALCAN_ERROR` to `AJUSTARE_CONTUR`, deduplicate overlapping polygons hierarchically (`ADMIS > AJUSTARE_CONTUR > MUTILAT_DEFORMATIE_MODEL > ELIMINAT_EROARE_MAJORA`), and evaluate all 6 validation forms (`V1..V6`) simultaneously in the Colab Pro `A100` loop [REPO: commit `e31f00d`, 2026-10-29].

Why (the number or gate it serves): Single-metric geometric scoring previously marked tree-bitten roofs (`OPT_B_009:C1`, `OPT_B_075:C1`, `OPT_B_161:C1`) as 98% valid and left 53 spatial overlaps among the 242 Opera GX review cards [CALC: `tools/deduplicate_and_audit_opera_review.py`, 2026-10-29]. Evaluating `V1` (visual chip edge SNR), `V2` (whole-roof continuation), `V3` (tree-bite vs real `L/U/T` courtyard), `V4` (90/45 deg orthogonality), `V5` (NoData border & semantic purity), and `V6` (planar NMS) simultaneously prevents false promotions.

Alternatives rejected and why:
- 4-channel RGB+nDSM coupling in Phase 1: rejected because LiDAR nDSM is unavailable in many target zones/UATs.
- Single-metric IoU/orthogonality gate: rejected because it fails to distinguish tree-crown occlusion from real `L`-shaped buildings.

Consequences / what stops being done: `CALCAN_ERROR` is replaced by `AJUSTARE_CONTUR`; overlapping `ELIMINAT` polygons never overwrite `ADMIS` roofs (`ignore_index=255` used on incomplete roofs and `NoData` borders). What was not checked: live execution on a remote Colab Pro `A100` runtime (awaited owner approval).

Approved by / date: Pending owner promotion to `canon/`.
