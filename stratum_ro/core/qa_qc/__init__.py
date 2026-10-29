# -*- coding: utf-8 -*-
"""
StratumRO — Core QA/QC Package
"""

from stratum_ro.core.qa_qc.validator import CoreGeometryValidator
from stratum_ro.core.qa_qc.simultaneous_2d_validator import (
    SimultaneousValidationReport,
    GateResult,
    CANONICAL_VERDICT_MAP,
    VERDICT_PRIORITY,
    normalize_verdict,
    evaluate_building_simultaneously,
    deduplicate_v6_planar_nms,
    repair_v2_whole_roof_extension,
    repair_v3_complete_tree_bitten_corners,
)

__all__ = [
    "CoreGeometryValidator",
    "SimultaneousValidationReport",
    "GateResult",
    "CANONICAL_VERDICT_MAP",
    "VERDICT_PRIORITY",
    "normalize_verdict",
    "evaluate_building_simultaneously",
    "deduplicate_v6_planar_nms",
    "repair_v2_whole_roof_extension",
    "repair_v3_complete_tree_bitten_corners",
]
