StratumRO now preserves the generated B review sites and GIS evidence alongside the code, and uses a shared batch stage to prevent CLI-only geometry corrections.

This draft also includes the earlier verification recovery: restored LiDAR helpers, export regression coverage, corrected metric verification behavior, and the audit of Antigravity Lot4/Lot5 provenance. Independent accuracy is not claimed.

Changes:
- Existing B observations are refined and compared with simpler shape alternatives. All 216 proposal IDs remain; 1026 alternatives are available. The selected review has 112 simpler contours, 3664 to 2798 corners, and 68 to 60 overlapping pairs above 0.05 m². All remain pending owner review.
- `RegionalRoofRefiner.simplify_shapes` centralizes candidate selection, optical validity and joint neighbor guards. The reporting CLI calls this core and renders only after batch QA. No new detector or second core.
- `workspace/building_workflow/CURRENT.json` selects active B; `docs/BUILDING_WORKFLOW.md` documents real integration, limitations and a Mermaid diagram.
- Owner authorized publishing generated websites and useful assets on 2026-10-19: 878 initial evidence files, 157.24 MiB, now included in Git (HTML, images, GIS, JSON, evaluation crops and saved project backups). Raw eight-tile orthophoto/LiDAR datasets and unrelated agents' modifications are not included.
- Six explicitly approved superseded/incomplete B folders were moved to `junk/2026-10-19/option_b_history/`: 401 files, every SHA-256 verified. Paths, reasons and restoration are documented. Active source dependencies stay in place.
- `workspace/reviews/index.html` links the active report and source-stage site using relative resources. GitHub stores the assets; GitHub Pages is not enabled.

Validation:
- 508 software tests: 499 passed, 9 skipped (45.188 s).
- 17 targeted tests pass, including two individually safe simplifications that conflict when applied together; joint QA preserves original shapes independent of input order.
- Real CPU replay after refactor reproduces all 216 published geometries and 1026 alternatives exactly. No new GPU inference.
- 670 relative website links and all 401 archived file hashes verified; local browser entry page inspected.
- Previous QGIS integration retained all 96 layers and added three; common saved project contains 99 valid layers. The pre-existing modified main QGS is not adopted into this checkpoint.

Limits: simplification does not recover missing/truncated buildings such as B120, establish cadastral ground footprints, or measure independent accuracy/recall. Some proposals remain complex or ambiguous. Old MCP refinement contract remains opt-in to its historical path; use the documented shared batch entry for current B.

Keep this PR draft. No merge requested or performed. Checkpoint and migration evidence: `workspace/option_b_consolidation_20261019/`.
