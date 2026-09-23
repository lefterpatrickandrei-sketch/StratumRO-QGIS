# -*- coding: utf-8 -*-
"""
StratumRO — Core QA/QC: Quality Assurance & Geometric Validation (Phase 3)
Implementation of the IValidator contract.
Pure-Python, deterministic geometric and attribute quality gates. Zero QGIS dependencies.
"""

from typing import Any, Dict, List, Optional
from shapely.geometry import Polygon, shape
from shapely.validation import explain_validity

from stratum_ro.contracts.validation import (
    IValidator,
    ValidationReport,
    ValidationIssue,
    ValidationSeverity
)


class CoreGeometryValidator(IValidator):
    """
    Standard QA/QC validator for 2D polygon geometries.
    Validates topological invariants, minimum areas, and geometric defects.
    """

    @property
    def validator_id(self) -> str:
        return "core_geometry_validator_v1"

    def validate(self, target: Any, **options: Any) -> ValidationReport:
        """
        Validates a Polygon or GeoJSON feature against universal geometric gates.
        """
        min_area_m2 = options.get("min_area_m2", 5.0)
        max_area_m2 = options.get("max_area_m2", 50000.0)

        poly = None
        feature_id = ""
        if isinstance(target, Polygon):
            poly = target
        elif isinstance(target, dict) and "geometry" in target:
            poly = shape(target["geometry"])
            feature_id = str(target.get("id", target.get("properties", {}).get("id", "")))

        issues: List[ValidationIssue] = []

        if poly is None or poly.is_empty:
            issues.append(ValidationIssue(
                code="GEOM_EMPTY",
                message="Geometry is None or empty",
                severity=ValidationSeverity.CRITICAL,
                feature_id=feature_id
            ))
            return ValidationReport(
                is_valid=False,
                ruleset_name="CORE_GEOMETRY_GATES",
                total_features_checked=1,
                issues=issues
            )

        # 1. GEOS Topological Validity
        if not poly.is_valid:
            reason = explain_validity(poly)
            issues.append(ValidationIssue(
                code="GEOS_INVALID",
                message=f"Topological defect: {reason}",
                severity=ValidationSeverity.CRITICAL,
                feature_id=feature_id,
                details={"reason": reason}
            ))

        # 2. Area bounds
        area = poly.area
        if area < min_area_m2:
            issues.append(ValidationIssue(
                code="GEOM_AREA_TOO_SMALL",
                message=f"Polygon area {area:.2f} m² is below threshold {min_area_m2} m²",
                severity=ValidationSeverity.WARNING,
                feature_id=feature_id,
                details={"area_m2": area, "min_threshold": min_area_m2}
            ))
        elif area > max_area_m2:
            issues.append(ValidationIssue(
                code="GEOM_AREA_TOO_LARGE",
                message=f"Polygon area {area:.2f} m² exceeds threshold {max_area_m2} m²",
                severity=ValidationSeverity.WARNING,
                feature_id=feature_id,
                details={"area_m2": area, "max_threshold": max_area_m2}
            ))

        # 3. Degenerate vertex count
        coords = list(poly.exterior.coords)[:-1] if hasattr(poly, "exterior") else []
        if len(coords) < 3:
            issues.append(ValidationIssue(
                code="GEOM_DEGENERATE_RING",
                message=f"Polygon has fewer than 3 unique vertices ({len(coords)})",
                severity=ValidationSeverity.CRITICAL,
                feature_id=feature_id
            ))

        is_valid = not any(i.severity in [ValidationSeverity.ERROR, ValidationSeverity.CRITICAL] for i in issues)

        return ValidationReport(
            is_valid=is_valid,
            ruleset_name="CORE_GEOMETRY_GATES",
            total_features_checked=1,
            issues=issues,
            metrics={"area_m2": area, "vertex_count": len(coords)}
        )
