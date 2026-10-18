# Lot4 T21–T30 and visual recheck of Lot3 — 2026-10-17

The owner requested visual checks and the next ten cases in the same QGIS project, with every useful output committed. Lot4 has been source-reviewed, executed through the product roof workflow, inspected in individual native QGIS renders, and integrated into the shared project. This is a local reviewed-candidate evaluation, not a regional automatic detector, unseen holdout, complete building inventory, cadastral ground-footprint survey, or training-label release.

## Current shared QGIS state

- Project: `workspace/reviews/body_recovery_20261013/inspectie_corectii.qgs`.
- New group: `LOT4_T21_T30_IN_REVIZIE`.
- Active data: `workspace/reviews/lot4_20261017/selected/lot4_review.gpkg`.
- `ROOF_HYPOTHESES`: nine candidates. Cyan means visually plausible hypothesis, amber means finishing required. Neither color means owner acceptance.
- `CASES_REVIEW`: all ten target points and agent statuses; the displayed filtered layer marks only unresolved T22 with a red cross and label.
- `REJECTED_CANDIDATES`: rejected T22 mask, hidden diagnostic history. `SEARCH_ENVELOPES`: search windows, hidden; never final contours.
- Ten new native 5 cm detail crops, ten `Lot4 / Txx` bookmarks, ten individual QGIS images, a whole-lot render and live captures are preserved.
- Layer count increased from 49 to 63. All 38 previously visible geometries were checked unchanged. Earlier unsaved project state was preserved before integration; no accepted geometries or owner verdicts changed.

## Visual results: six plausible, three partial, one unresolved

These are **agent findings**, not owner acceptance or an accuracy percentage.

| Case | Shape / result | Agent finding |
|---|---|---|
| T21 | Articulated red roof, 20 corners; west wing retained | Needs finishing: tree-obscured west and small eastern/northern projections. A simpler 10-corner alternative was not adopted because meaningful projections could disappear. |
| T22 | Large red multi-wing complex | Unresolved: masks retain irregular parking fragments. No adopted final outline; bad masks remain diagnostic evidence. |
| T23 | Red hip roof and entrance projection, 11 corners | Visually plausible after excluding canopy/paving with corrected prompts. Detached pale canopy outside this primary-roof target remains unmodeled. |
| T24 | Long red roof with rounded bay, 22 corners | Needs finishing: large contamination improved, but pavement/stair platform around bay and a northern spike remain. Do not call this clean. |
| T25 | Long brown roof, four corners | Visually plausible principal roof. |
| T26 | Red L-shaped roof, six corners | Visually plausible primary roof; gray attachments are not automatically assigned cadastral identities. |
| T27 | Stepped elongated red roof and entrance cover, eight corners | Visually plausible selected roof, neighboring roof separate. |
| T28 | Narrow red roof, four corners | Visually plausible after removing vehicle/ground contamination; corrected prompts and consistency check are preserved. |
| T29 | Complete gray L-shaped hall, 18 corners | Needs finishing: southern spike and terminal-roof offsets. Earlier input window cut the southern arm; this was fixed before inference. |
| T30 | Principal glass greenhouse, four corners | Visually plausible optical result without a Class 6 veto; smaller southern structures remain separate and outside target scope. |

All nine adopted candidates are valid and have no positive-area pairwise intersections. These checks do not measure actual boundary accuracy. Every case remains `PENDING_OWNER_REVIEW`.

## Lot3 recheck

`workspace/reviews/lot4_20261017/lot3_recheck/` contains ten newly rendered full-case QGIS details and `findings.json`. T15/T20 are the most plausible; T14 still needs repair. T11/T12/T13/T16/T17/T18/T19 require finishing or interpretation. In particular, T17's interior contains a smaller covered structure: a polygon hole must not be equated with a wholly proven open courtyard or a complete building inventory. No Lot3 geometry or owner verdict was changed by this audit.

## Reusable product correction

`stratum_ro/cadastral_roof_workflow.py` previously ranked SAM masks by score after checking only the primary anchor. It now checks explicit reviewed prompts:

1. Additional positive points must belong to the anchor component. A higher score cannot justify dropping a known wing.
2. Negative points must remain outside the selected roof, including its boundary. A high-scoring mask containing a reviewed background point is rejected.
3. If no consistent mask exists, return no geometry with `NO_PROMPT_CONSISTENT_MASK`, preserving score/conflict diagnostics.
4. Recheck after refinement. If simplification fills a reviewed background hole or removes a confirmed wing, retain the consistent raw observation and flag `REFINEMENT_VIOLATES_REVIEWED_PROMPTS`; do not quietly publish the simplified geometry.

The gate also detects erroneous human/agent prompts; it does not establish that a prompt was placed correctly. Source inspection found one T28 negative point on red roof and one T22 positive point on vegetation. They were explicitly corrected before final selection, with earlier attempts preserved. Four meaningful regressions cover high-score background leakage, known-wing omission, no consistent candidate and background-hole refilling. Relevant suite: **71 tests passed** in 7.258 s.

No default Class 6 requirement was introduced. Roof geometries remain optical hypotheses; missing LiDAR support does not imply absence of buildings.

## Data preparation and execution provenance

- Original SID source metadata has no CRS. Correspondence with the existing project cache was checked before assigning its EPSG:3844 interpretation without changing XY. This is not independent datum validation.
- Source masks were transferred from the existing cache with nearest-neighbor resampling. Dark pixels alone were not newly classified as NoData. The standard preflight passed on all ten cases before inference; no mask-policy bypass was needed.
- T30's nearly uniform glass patch had local correlation 0.813, while independent whole-window correspondence was 0.9845. Both are recorded; the acceptance threshold was not lowered.
- Original T26 selection was replaced **before inference**, because the modern complex was near the previously rejected T08 candidate. Both the draft and its imagery remain evidence; the actual T26 is a distinct northeastern red L-shaped roof.
- This is a development lot using previously available Cluj imagery, not spatially independent training/evaluation evidence.

`workflow_inputs.json` binds reviewed selection images by SHA-256. `attempt1` holds all ten initial runs. `attempt2` revises four prompts before the new gate. `attempt3_prompt_checked` applies the gate; `attempt4_corrected_points` fixes the two contradictory points. `selected/verification.json` and `implementation_provenance.json` disclose which attempts contributed to each displayed candidate. Only the reviewed six-corner T26 fit was adopted from orthogonal alternatives.

Reusable preparation/inspection/rendering tools are `tools/prepare_roof_lot_sources.py`, `tools/inspect_roof_lot_sources.py` and `tools/render_roof_lot_review.py`. Lot-specific review choices are separate in `tools/build_lot4_review_manifest.py` and `tools/package_lot4_review.py`. The production entry point remains `tools/run_cadastral_roof_review.py`, which enforces preflight. Do not overwrite existing attempt directories or loaded GeoPackages.

## Git and continuation

Preparation checkpoint: `4f97467`. Product prompt gate and real outcomes: `0cdd315`. The final integration checkpoint additionally includes native screenshots, the updated shared project, this handoff, owner-status records and evidence manifests. Code, text, rasters, vectors, images, attempted/rejected results and project backups are included locally. Only transient SQLite WAL/SHM and automatic editor backup files are ignored; database changes are checkpointed before evidence hashing. No remote push was performed.

Next repair targets are T22's roof/parking discrimination, T24's bay versus surrounding platform, T21's occluded/protruding edges and T29's terminal roof. Start from these saved cases rather than replacing failed objects with easier ones. Preserve earlier accepted lots, all ten test identities, failure evidence and owner verdict separation. The current conversation and a provider subscription are not prerequisites for continuing from these repository files.
