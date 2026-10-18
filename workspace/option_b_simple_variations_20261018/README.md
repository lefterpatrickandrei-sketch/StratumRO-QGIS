# B: simpler shapes and explicit alternatives

Owner authorized automatic simplification of B and suitable shape variations per case, 2026-10-18. Reuse `roof_simple_geometry` ring fitting through `RegionalRoofRefiner.shape_variations` and the existing PlatformService/mosaic. No new detector, GPU inference, training, dependencies or template drawn from cadastral references.

Candidates: oriented rectangles, orthogonal runs at several physical simplification scales, previous simple B proposal, topology-preserving oblique line fits and original observation. Describe rectangle, L, U, ambiguous T/offset, articulated orthogonal, courtyard, irregular. Do not infer legal bodies from shape. Keep rejected rectangle visible when it erases wings. Preserve existing holes. Rank eligible candidates by corner count then agreement with observation; development thresholds 92% support/coverage, 8% area, 1.5 m boundary, 1 m shortest outer edge. These are not cadastral accuracy limits. RGB validity, optical contrast and neighbor overlap may block selection. Every result remains PENDING_OWNER_REVIEW.

Fresh local outputs: `workspace/reviews/option_b_simple_variations_20261018/`. Every case gets actual-image panels before/selected/alternatives. Existing results and owner acceptance stay intact. Code/docs/JSON/manifests in local Git; GIS/images local under the latest artifact policy. No push or merge.

Primary research consulted:
- https://www.informatik.uni-wuerzburg.de/en/algo/research/geographic-information-systems/simplification-of-building-footprints/ (reduce edges, preserve shape/topology/neighbors)
- https://www.mdpi.com/2220-9964/12/12/469 (dominant orientation and orthogonal reconstruction; full text rate-limited, abstract inspected).

This is a bounded heuristic extension of existing code, not an implementation of the papers' global optimization or a guarantee of universal roof recognition.
