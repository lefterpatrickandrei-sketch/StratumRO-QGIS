# Executable evaluation checks for all agents

Read this before creating or rerunning any visual building test lot. Implementation:
`stratum_ro/evaluation_preflight.py`; first integration:
`tools/run_lot3_evaluation.py`. These are prerequisites, not an automatic roof judge.

## Current state and why this exists

Owner questioned Lot 3 selection and geometry. Codex review found T14 centered on
grass, T20 on vegetation/NoData, T12:C1 includes pavement and neighboring roofs,
and T17 ends inside a roof that continues beyond its contour. T12:C2 also needs
visual rectification. Existing manifest and outputs are historical, unaccepted
evidence. Do not silently rewrite them or label all eight misses genuine recall
failures. Live QGIS contains the lot, but the delivered overview screenshot did
not show its markers. Historical claims that T12:C2/T17 are clean are superseded.

## Before inference

Create a reviewed manifest revision; preserve the original and record changed
IDs, original manifest path, and reasons. Do not replace genuine failed buildings
just because inference failed. Invalid selections can be corrected transparently.

Required manifest fields: `schema_version: 2`, `crs: EPSG:3844`, nonempty `cases`.
Each case needs unique `test_id`, `tile`, `search_center`, `search_bbox`,
`target_extent`, and `selection_review`.

- `search_center`: a point actually on the intended roof, not a parcel centroid.
- `target_extent`: a loose rectangle containing the entire intended object; this
  is a search envelope, not a manually drawn prediction or ground-truth polygon.
- `search_bbox`: must contain target_extent. Tile/mosaic must contain the search
  plus the retry stage's padding, with valid RGB in all three bands throughout.
- `selection_review`: `object_kind: BUILDING`, `point_on_roof: true`,
  `full_target_visible: true`, nonempty `reviewer` and `observations`, `image`,
  `image_sha256`. Image paths are relative to the manifest or absolute; tile paths
  are relative to the tile cache or absolute. Inspect the actual image first.
  Observations describe the roof/material/neighbors before assigning an archetype.
  Hash using `sha256_file`; do not invent inspection records to satisfy a schema.

The preflight checks actual file hashes, image readability, numeric extents,
point containment, duplicate IDs, raster CRS, RGB coverage and NoData. It blocks
unreviewed records or non-building targets. It cannot prove a reviewer identified
a building honestly or that target_extent covers an unseen wing. NoData must be
resolved in input preparation; do not label it a model failure or bypass the check.
Class 6 is not required at the selected point: sparse LiDAR must not exclude real
glass/low roofs by definition. Sensor completeness still needs its own diagnosis.

Run without inference:

    venv\Scripts\python.exe tools/run_lot3_evaluation.py --manifest <reviewed-manifest.json> --preflight-only

Exit 0 means prerequisites passed, NOT correct extraction or owner acceptance.
The legacy Lot 3 manifest intentionally fails. After review, use a fresh directory:

    venv\Scripts\python.exe tools/run_lot3_evaluation.py --manifest <reviewed-manifest.json> --output-dir <new-directory>

Existing directories cannot be overwritten. Reports disclose
`LOCAL_RETRY_ONLY_NOT_FULL_PRODUCTION_PIPELINE` and bind selection by SHA256.
This runner tests local recovery; use the actual full pipeline for full-pipeline
claims. New runners must call validate_selection + require_ready before inference.

## After inference

Preserve every raw attempt and result. Inspect target correspondence, omitted
wings, pavement included as roofs, merging, and real L/U shapes. A support score
measures agreement with a mask; it cannot establish that the mask is a building.
Record agent findings separately from explicit owner verdict. Nothing in this
module changes owner acceptance or automatically corrects roof geometry.

## QGIS integration

The Lot 3 integration script now aborts on wrong shared project, unsaved project
or editable layers, missing/incorrect baseline layer counts, failed save, RPC
error/timeout, stderr, caught Python exception or missing success marker. It is
the historical baseline integrator, not a general integrator for revised outputs.
Revised lots must update expected sources/counts explicitly and verify readback.
Layer checks occur after loading: an abort is not a transaction rollback; inspect
live state before retrying. Respect user edits rather than automatically discarding
or saving them.

Screenshot correctness still needs actual visual inspection. An existing PNG,
successful RPC or enabled layer does not prove the image shows the intended lot.
Do not declare integration complete until the actual new screenshot shows the
expected markers, outlines and labels in the shared project.

## Continuing independently of chat/provider

All agents use this repository and AGENTS.md. These checks do not depend on ChatGPT
Plus or access to chat history. Read the latest owner feedback and this document;
do not bypass guards to reproduce a historical success claim. QGIS source:
`workspace/reviews/body_recovery_20261013/inspectie_corectii.qgs`.
Coordinate writes; do not run competing project/GPKG writers.

## Executed verification, 2026-10-13

- `python -m unittest stratum_ro.test.test_evaluation_preflight`: 10 tests, OK.
- `python -m unittest discover stratum_ro/test`: 385 discovered, 375 passed,
  9 skipped, 1 failed in 35.113s. Failure: frozen hash of
  `stratum_ro/domain/city_3d/builder.py`; already reported by the preceding T10
  worker. This change does not edit builder.py or alter the freeze manifest.
- Legacy Lot3 runner `--preflight-only`: exit 1, SELECTION_BLOCKED, before
  LiDAR processing/SAM2 initialization; no baseline outputs overwritten.
- Runner/integrator syntax checked without executing inference/QGIS mutations.
- Live integration guard is implemented and unit-tested on RPC responses, but
  its mutating QGIS path was intentionally not executed during this change.

Remaining work for Antigravity: visually review and transparently revise Lot3
selection, use full input coverage, diagnose segmentation, repair extraction,
and deliver verified per-case/native QGIS images for the owner's decision.
