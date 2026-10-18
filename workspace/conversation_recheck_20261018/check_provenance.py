"""Read-only checks of comparison provenance; never executes processing scripts."""
import hashlib
import json
from pathlib import Path

import geopandas as gpd

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
full = ROOT / "workspace/reviews/auto_unvectorized_20261018/auto_unvectorized_orthogonal.gpkg"
regional = ROOT / "workspace/reviews/regional_roofs_20261017/masked_review_v2/regional_review.gpkg"
comparison = ROOT / "workspace/reviews/comparatie_a_vs_b_20261018/comparatie_a_vs_b.gpkg"
lot4 = ROOT / "workspace/reviews/lot4_20261017/selected_v4_orthogonal/lot4_orthogonal.gpkg"
raw = gpd.read_file(full, layer="RAW_CANDIDATES_BEFORE")
rest = raw.loc[raw.body_id == "REST_260:C1"].iloc[0]
pool = gpd.read_file(regional, layer="ROOF_CANDIDATES")
rejected = gpd.read_file(comparison, layer="OPTIUNEA_B_FALS_POZITIV_ELIMINAT")
sol = gpd.read_file(lot4, layer="FOOTPRINT_HYPOTHESES_SOL")
sol_t22 = sol.loc[sol.body_id == "T22:C1"].iloc[0]
plugin = Path.home() / "AppData/Roaming/QGIS/QGIS3/profiles/default/python/plugins/stratum_ro"
paths = ["tools/run_comparison_a_vs_b.py", "tools/run_stratumro_full_auto.py",
         "stratum_ro/core/geometry/regularizer.py", "stratum_ro/ai/tools/vector_tools.py"]
result = {
    "source_files_sha256": {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in paths},
    "qgis_plugin_path": str(plugin),
    "qgis_plugin_resolved_target": str(plugin.resolve()),
    "incorrect_src_link_exists": (ROOT / "src/stratum_ro/core/geometry/regularizer.py").exists(),
    "rest260_input_check": {
        "candidate_id": str(rest.candidate_id), "raw_area_m2": rest.geometry.area,
        "regional_pool_count": len(pool),
        "maximum_intersection_with_regional_pool_m2": max(g.intersection(rest.geometry).area for g in pool.geometry),
        "regional_exact_geometry_matches": sum(g.equals(rest.geometry) for g in pool.geometry),
        "comparison_rejected_count": len(rejected),
        "comparison_rejected_max_area_m2": float(rejected.geometry.area.max()),
    },
    "t22_sol_actual_geometry_area_m2": sol_t22.geometry.area,
    "code_inspection_findings": {
        "comparison_input": "regional ROOF_CANDIDATES only; no COMPLEX_REVIEW input",
        "option_a_selection": "top ten fixed score h90*2 + pct_elev + compactness*50",
        "false_positive_rate_pct": "literal 0.0 at tools/run_comparison_a_vs_b.py:413, not measured",
        "geographic_quarters": "no quarter-area split implemented",
        "new_sam2_inference": "not implemented in comparison script",
        "calibration": "fixed thresholds, no training/calibration against owner-accepted labels",
        "full_auto_total_timer": "computed at line 620 before QGIS synchronization",
        "ui_tool_import": "stratum_ro/ai/tools/vector_tools.py imports stratum_ro.vectorizer.CadastralVectorizer",
        "integration_limit": "same core used by scripts does not prove every app entrypoint invokes this workflow",
    },
}
(OUT / "provenance.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(json.dumps(result, indent=2, ensure_ascii=False))
