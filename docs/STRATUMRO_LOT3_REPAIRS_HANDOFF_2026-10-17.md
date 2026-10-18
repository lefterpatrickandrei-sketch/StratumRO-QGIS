# Lot3: native optical repairs integrated in shared QGIS — 2026-10-17

This supersedes the intermediate repair checkpoint. Local reviewed repairs are implemented in StratumRO and displayed in the existing shared QGIS project. They are **not owner accepted**, measured ground footprints, a validated regional automatic run, or training labels.

## Where to continue

- Repository: `C:/Users/lefpa/Downloads/QGIS-AI`.
- Shared project: `workspace/reviews/body_recovery_20261013/inspectie_corectii.qgs`.
- Active group: `LOT3_REPARAT_20261017_NEVALIDAT`.
- Active vector: `LOT3 - 20 ipoteze / NECESITA VERDICT`, cyan outlines.
- Pointer: `workspace/reviews/lot3_repairs_20261017/CURRENT_SELECTION.json`.
- Active package: `workspace/reviews/lot3_repairs_20261017/selected_v3/lot3_repaired.gpkg`, layer `REPAIRED_ROOF_CANDIDATES`.
- Twenty roof-surface hypotheses cover ten test cases, T11–T20. They do not establish twenty independent cadastral buildings.
- Each case has `Txx_qgis.png` and `Txx_before_after.png` under `selected_v3/`. The project has ten `Lot3 reparat / Txx` bookmarks. Previous variants are preserved as hidden history; accepted Lot1/Lot2 data were not edited.

## Actual changes and remaining uncertainty

| Case | Current observed result | Limits |
|---|---|---|
| T11 | C3 wrong orientation replaced by an optical outline; C1/C2 preserved. | Whole case still needs owner verdict; preserved bodies were not revalidated automatically. |
| T12 | Three targets redelineated; gray L-shaped roof recovered. | C2 has real NoData nearby; completeness is unconfirmed. Adjoining brown surfaces are not automatically inferred to be buildings. |
| T13 | Visible articulated roof followed. | Trees and oblique/curved boundaries remain review items. |
| T14 | Main roof substantially better represented. | Small mask spikes and adjoining flat surfaces/terraces still require interpretation; do not declare complete repair. |
| T15 | One reviewed flat roof, four corners. | Pending visual acceptance. |
| T16 | Previous combined 44-corner outline replaced by three four-corner roof surfaces: tiled C1, patched C2, small porch C3. | Previous C1 is subdivided, not silently preserved. Parent remains T16. Junction completeness and independent cadastral identities are unconfirmed. |
| T17 | Two earlier roof geometries and courtyard preserved exactly. | Earlier completeness warnings remain. |
| T18 | Main roof C1, brown annex C2 and western roof wing C3 separately represented, with 10/10/12 corners. | C3 is a provisional roof-surface subdivision, not a confirmed independent cadastral building. |
| T19 | Previously missing articulated roof recovered; 18-corner orthogonal hypothesis removes thin mask spikes. | Local boundaries still require inspection; mask overlap metrics are not accuracy. |
| T20 | Two principal roof surfaces represented by four corners each; thin pipes/equipment excluded. Lower bright roof edges independently fitted. | Roof identities are provisional; no automatic conversion to ground footprints. |

## Executable product implementation

`PlatformService.create_cadastral_roof_workflow()` exposes the existing service. `CadastralRoofWorkflow.extract()` now accepts explicit reviewed `positive_points`, `negative_points`, `max_prompt_shift_m` and `refinement_policy`:

- `SENSOR_FUSION`: previous default; unchanged.
- `OPTICAL_FIDELITY`: `stratum_ro/roof_mask_fidelity.py` preserves the optical shape, substantial interior holes, valid anchor, and bounded displacement. Tiny mask holes are reported when removed. No supported simple fit means review, not a forced rectangle.
- `OPTICAL_PLANAR_CORE`: only for a target already reviewed as a rectangular roof plane. Removes narrow attached mask fragments through bounded morphological opening, then fits a supported rectangle. Removed area and radius are explicit diagnostics. Never apply this indiscriminately to L-shaped roofs, courtyards or annexes.

`stratum_ro/roof_masked_preflight.py` preserves standard preflight gates. Only per-case `context_policy: MASKED_CONTEXT_REVIEW` can allow a genuine masked context with >=90% valid area and a valid anchor, retaining a completeness warning. Schema/CRS/evidence errors remain blocking. `clip_roof_to_valid_grid()` reapplies the exact validity grid after refinement, so small-hole cleanup cannot refill NoData.

`stratum_ro/roof_gap_edges.py` supports explicit `signal_kind='BRIGHTNESS'` in the existing edge fitter as well as red chromatic contrast. T20 uses independent image-edge fits, not clipping against an unaccepted neighbor/reference.

`tools/run_cadastral_roof_review.py` runs these policies from reviewed manifests, saves raw masks, crops, hypotheses, diagnostics and source hashes. For an independent rerun use a **new output directory**, e.g.:

```powershell
venv/Scripts/python.exe tools/run_cadastral_roof_review.py --manifest workspace/reviews/lot3_repairs_20261017/T16_surface_inputs.json --output-dir workspace/reviews/lot3_repairs_20261017/T16_rerun_NEW --max-vertices 24
```

Reviewed prompting and postprocessing selection remain local review operations. This delivery does not integrate these per-case prompts into an autonomous regional detector.

## Reproduction and provenance

All run artifacts live under `workspace/reviews/lot3_repairs_20261017/`. `attempt1`, `masked_T12`, `T16_surfaces`, `T16_porch`, `T18_surfaces`, `T20_edges` and `simplified2` provide the selected lineage. Failed or unadopted attempts remain evidence; a directory containing `final` is not proof of quality. `selected` and `selected_v2` are historical. Only `CURRENT_SELECTION.json` points to the active version.

`tools/package_lot3_repaired_candidates.py --output-name NEW_NAME` packages reviewed choices without overwriting a loaded GeoPackage. It uses 95% support/coverage for the reviewed T18/T19 orthogonal candidates, distinct from the stricter generic fidelity policy; this is a disclosed local review choice. `tools/render_lot3_selected.py --selected-dir NEW_NAME` produces whole-case comparisons. The QGIS integration/update scripts contain guards against a wrong project, editable layers and repeat application; do not blindly rerun them against a different current state.

Nine 5 cm crops were read from the original SID/VRT. Original SID CRS metadata is empty. `coordinate_checks.json` records agreement with existing project cache pixels at the same coordinates (RGB correlation 0.916–0.988), then EPSG:3844 project interpretation was assigned without changing XY. This is **not independent geodetic validation**. Original external SID files are existing inputs, not new outputs created by this repair.

T12's mask was made explicit after the first experiment. `covers/T12_before_mask.tif` preserves the exact original historical source bytes; `source_mask_versioning.json` records both versions. Preserve these when checking historical source hashes. Dark RGB pixels alone do not establish NoData. Foreign uncommitted changes to the standard preflight have not been included in this repair commit.

## Verification and Git handoff

- `selected_v3/verification.json`: all 20 geometries valid; no positive-area intersections between any pair; all owner verdicts pending. Sixteen non-T16 geometries are exactly unchanged from visually inspected v2.
- All ten v2 native QGIS renders inspected; final v3 T16 inspected after replacement. QGIS contains 49 layers including nine new detail crops; the same review layer ID now points to v3. No stale loaded GeoPackage was overwritten.
- Relevant regression suite: **67 tests passed**. A second isolation check loads the standard preflight and its fixture from committed HEAD in memory, with no filesystem replacement; all 67 also pass. Our implementation does not require another agent's uncommitted preflight edits.
- New source, tests, manifests, failed attempts, TIFF/GPKG files, PNG comparisons, project-state backups and the updated shared QGIS project are versioned locally. No remote push is authorized or performed. Preserve other agents' dirty work rather than using `git add -A`.

Next review must focus on T12 NoData, T14 adjoining surfaces and small spikes, and roof-surface identity/junctions in T16/T18/T20. Inspect full objects and record the owner's verdict separately. Do not train on these hypotheses or claim cadastral accuracy from geometric validity, model confidence or recovered-case counts.
