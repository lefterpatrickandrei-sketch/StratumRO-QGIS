# ANCPI Ordinul nr. 600/2023 traceability for footprint validation

## Scope and evidence status

This note separates text directly supported by a pinpoint provision from
implementation heuristics. It is not a legal opinion, a complete compliance
assessment, or a declaration that generated footprints meet cadastral
requirements. `validate_ancpi` is a geometry sanity-check wrapper; it does not
replace review and sign-off by an authorized surveyor.

The available official Portal Legislativ entry identifies Ordinul nr. 600 of
8 February 2023 and its approved regulation. The regulation's Article 37(1)
describes technical reception checks, including correspondence with source
documents, location/boundaries, overlaps, geometry review, and accuracy where
applicable. Those general checks do not substantiate the numeric thresholds
below. No exact article/annex provision was verified here for the project
thresholds or the specific validation rules; accordingly they are not assigned
to `NORMATIV_ANCPI`.

## NORMATIV_ANCPI

Only entries backed by an exact article or annex belong in this category.

| Rule / source | Traceability and limit |
|---|---|
| Technical reception review | Regulation approved by Ordinul nr. 600/2023, **Art. 37(1)**, provides for technical checks in cadastral documentation reception, including geometry/location and boundary-related review. This is general context, not support for the code's numeric cutoffs. |
| 8 m² / 45 m² thresholds; 1 m edge; 5° orthogonality; coordinate envelope; mandatory EPSG:3844 for this API | **UNVERIFIED as Ordinul 600/2023 rules.** No exact article/annex citation has been established for these claims. Do not present the code's docstring or response `evidence` labels as legal authority. |

## EURISTICA_PROIECT

These are current code behaviors / internal thresholds, not attributed here to
Ordinul nr. 600/2023:

| Check | Current implementation behavior (`stratum_ro/ai/tools/cadastral_tools.py`) |
|---|---|
| Area | `area >= 45.0` increments `min_area_main_45m2`; otherwise `area >= 8.0` increments `min_area_annex_8m2`; smaller area fails. These are code thresholds, not verified legal minima. |
| Edge | Docstring says minimum edge `>= 1.0 m`, but executable code flags an exterior segment only when length is **strictly `< 0.5 m`**. Thus 0.50 m passes; 0.75 m and 1.0 m pass. The result key `min_edge_1m` is inconsistent with the implemented cutoff. |
| Coordinate envelope | Code checks only the geometry centroid against inclusive X `[150000, 850000]`, Y `[200000, 800000]`. It does not check every vertex, and does not validate CRS. Bounds are an approximate project sanity envelope, not an established legal boundary. |
| CRS | Raw geometry calls carry no CRS metadata. `layer_path` reads a GeoDataFrame but current implementation does not inspect its CRS; the response's `EPSG:3844` string is declarative, not a performed CRS validation. Missing and non-EPSG:3844 CRS are therefore not distinguishable through the raw-geometry API. |
| Empty geometry | Counted as failed and skipped for the area, edge, and bounds counters. |
| MultiPolygon | Area and centroid are evaluated; edge loop is skipped because the geometry lacks a single `exterior`, and the edge check is counted as passed. |
| Self-intersection | `validate_ancpi` does not test validity/topology; a bow-tie polygon can pass these checks if its calculated area and centroid satisfy them. `validate_topology` is a separate API. |

## Verification reference

Focused regression coverage is in `stratum_ro/test/test_ancpi_validation.py`.
Tests characterize the current implementation only and intentionally do not
assert that these heuristics are legally sufficient.

Official source consulted: Portal Legislativ, Ordinul (A) nr. 600/08.02.2023,
and the regulation text, Art. 37(1). The exact numeric thresholds listed above
remain unverified as normative provisions.