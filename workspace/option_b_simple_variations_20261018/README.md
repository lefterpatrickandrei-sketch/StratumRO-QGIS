# B: simpler shapes and explicit alternatives

Owner authorized automatic simplification of B and suitable shape variations per case, 2026-10-18. Reuse `roof_simple_geometry` ring fitting through `RegionalRoofRefiner.shape_variations` and the existing PlatformService/mosaic. No new detector, GPU inference, training, dependencies or template drawn from cadastral references.

Candidates: oriented rectangles, orthogonal runs at several physical simplification scales, previous simple B proposal, topology-preserving oblique line fits and original observation. Describe rectangle, L, U, ambiguous T/offset, articulated orthogonal, courtyard, irregular. Do not infer legal bodies from shape. Keep rejected rectangle visible when it erases wings. Preserve existing holes. Rank eligible candidates by corner count then agreement with observation; development thresholds 92% support/coverage, 8% area, 1.5 m boundary, 1 m shortest outer edge. These are not cadastral accuracy limits. RGB validity, optical contrast and neighbor overlap may block selection. Every result remains PENDING_OWNER_REVIEW.

Fresh local outputs: `workspace/reviews/option_b_simple_variations_20261018/`. Every case gets actual-image panels before/selected/alternatives. Existing results and owner acceptance stay intact. Code/docs/JSON/manifests in local Git; GIS/images local under the latest artifact policy. No push or merge.

Primary research consulted:
- https://www.informatik.uni-wuerzburg.de/en/algo/research/geographic-information-systems/simplification-of-building-footprints/ (reduce edges, preserve shape/topology/neighbors)
- https://www.mdpi.com/2220-9964/12/12/469 (dominant orientation and orthogonal reconstruction; full text rate-limited, abstract inspected).

This is a bounded heuristic extension of existing code, not an implementation of the papers' global optimization or a guarantee of universal roof recognition.


## Executed result, completed 2026-10-19

The initial 2026-10-18 folder contains diagnostic images from an interrupted run: joint overlap QA found B033 and B203 needed preservation. It is NOT the selected output. Selected complete output is `workspace/reviews/option_b_simple_variations_20261018_v2/`; all 216 image hashes verified. Joint QA now reverts both affected changed shapes and regenerates their panels and decisions. No result source was overwritten.

- 216 inputs/outputs, 1026 alternatives; 112 objects have fewer corners, 3664 to 2798 total vertices.
- 68 to 60 pairwise intersections >0.05 m²; existing errors/identities remain unresolved. No new pairwise area increase >0.05 m² versus prior shapes.
- Selected descriptive families: 81 rectangle, 6 L, 3 ambiguous T/offset, 15 courtyard, 65 oblique/irregular, 46 unresolved. U is supported and unit tested but no final selected U appears in these 216. More articulated orthogonal shapes are supported without asserting a letter family. This is not every possible architectural shape or semantic recognition.
- Every result PENDING_OWNER_REVIEW. No changes to accepted original contours. No new detection, missing-building recovery, model training or SAM2 inference.
- B006 10 to 4 corners; B046 21 to 8. B169 stays 13 under neighbor conflict guard. Source-mask agreement and optical contrast do not prove accuracy. A 1.5 m allowed shift is a development generalization limit, NOT survey tolerance; inspect positional quality.
- New `RegionalRoofRefiner.shape_variations` is reachable through the existing PlatformService factory. Existing `refine` default and live MCP tool contract were not silently changed; callers must opt into this new method. CLI uses it for every B case.
- Local browser report: http://127.0.0.1:8768/index.html . Expand each case to compare old/selected and up to six alternatives. Magenta = rejected alternative, green = eligible by software gates, cyan = proposed selection. Eligibility never means owner acceptance. Some long rejection labels are truncated on panels; full reasons are in report JSON.
- QGIS was closed after interruption; no running desktop instance/9876 listener was found. Opened the saved common project once with the task script. Loaded three new layers under `B_FORME_SIMPLE_SI_VARIATII_20261018`, preserved all 96 earlier layer IDs, saved total 99; invalid layers zero. Earlier group hidden reversibly. Actual live canvas captured in `live_qgis.png` and inspected at B046. Some remaining shapes still need refinement; screenshots do not establish independent accuracy.
- `venv/Scripts/python.exe -m unittest discover -s stratum_ro/test -q`: 507 tests, 498 passed, 9 skipped, 39.794 s. First attempted pytest unavailable; used existing unittest environment without installing packages. 16 targeted tests also passed.
- GIS/images/HTML/source project backup stay local under latest owner policy; versioned report/manifests bind their paths and hashes. Main QGS modifications include previous live user state and are not staged. Foreign modified comparison GPKG and two untracked audit tools untouched.
- Initial implementation checkpoint `ae2434f`. Completion checkpoint follows in Git log; no push/merge.

## Continue

Use the common rules and this handoff in any agent. Inspect actual imagery for per-case refinements before relaxing mask gates further. Do not use the simple output as clean training labels until accepted. No generic ability to recover every missing building is demonstrated. Review the remaining 60 overlaps and unresolved optical/identity cases separately from simplification.
