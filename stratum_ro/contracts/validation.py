# -*- coding: utf-8 -*-
"""
StratumRO — Validation & Quality Assurance Contracts (Phase 2)
Standardized quality gates for geometry, topology, and regulatory compliance.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Protocol, runtime_checkable


class ValidationSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class ValidationIssue:
    """
    Individual defect or anomaly detected during automated QA/QC.
    """
    code: str                     # e.g., "GEOM_SELF_INTERSECT", "ANCPI_TOLERANCE_EXCEEDED"
    message: str
    severity: ValidationSeverity
    feature_id: str = ""
    suggested_fix: str = ""
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationReport:
    """
    Aggregated quality report across all validated features.
    """
    is_valid: bool
    ruleset_name: str
    total_features_checked: int = 0
    issues: List[ValidationIssue] = field(default_factory=list)
    metrics: Dict[str, float] = field(default_factory=dict)

    @property
    def has_critical_errors(self) -> bool:
        return any(i.severity in [ValidationSeverity.ERROR, ValidationSeverity.CRITICAL] for i in self.issues)


@runtime_checkable
class IValidator(Protocol):
    """
    Contract for QA/QC validation engines.
    """
    @property
    def validator_id(self) -> str:
        ...

    def validate(self, target: Any, **options: Any) -> ValidationReport:
        """Executes validation rules against a target object or dataset."""
        ...
