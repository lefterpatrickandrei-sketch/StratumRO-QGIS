# -*- coding: utf-8 -*-
"""
StratumRO — Formal Architecture Contracts Package (Phase 2)
Provides type-safe, validated interfaces and data models for:
Core, Geodesy, Geometry, Domains, Cadastre RO, Vision, Workflow,
Validation, Provenance, and Adapters.
"""

from stratum_ro.contracts.geo import (
    Coordinate2D,
    Coordinate3D,
    BoundingBox,
    CommonGeoObject,
    IGeoProcessor
)
from stratum_ro.contracts.geodesy import (
    AxisOrder,
    CRSMetadata,
    ICRSManager,
    ITransformer
)
from stratum_ro.contracts.geometry import (
    IGeometryEngine
)
from stratum_ro.contracts.domain import (
    DomainMaturity,
    DomainCapability,
    BaseDomainPack
)
from stratum_ro.contracts.cadastre import (
    TopoLTLayer,
    CadastralPoint,
    PADTableSpec,
    CPInterchangeSpec,
    ICadastralExporter
)
from stratum_ro.contracts.vision import (
    VisionPromptType,
    VisionPrompt,
    VisionMaskResult,
    IVisionEngine
)
from stratum_ro.contracts.workflow import (
    WorkflowStatus,
    ApprovalState,
    ApprovalRequest,
    ApprovalDecision,
    IWorkflowRunner
)
from stratum_ro.contracts.validation import (
    ValidationSeverity,
    ValidationIssue,
    ValidationReport,
    IValidator
)
from stratum_ro.contracts.provenance import (
    ProvenanceRecordContract,
    IProvenanceRecorder
)
from stratum_ro.contracts.adapter import (
    IQgisAdapter,
    ILegacyAdapter
)

__all__ = [
    "Coordinate2D",
    "Coordinate3D",
    "BoundingBox",
    "CommonGeoObject",
    "IGeoProcessor",
    "AxisOrder",
    "CRSMetadata",
    "ICRSManager",
    "ITransformer",
    "IGeometryEngine",
    "DomainMaturity",
    "DomainCapability",
    "BaseDomainPack",
    "TopoLTLayer",
    "CadastralPoint",
    "PADTableSpec",
    "CPInterchangeSpec",
    "ICadastralExporter",
    "VisionPromptType",
    "VisionPrompt",
    "VisionMaskResult",
    "IVisionEngine",
    "WorkflowStatus",
    "ApprovalState",
    "ApprovalRequest",
    "ApprovalDecision",
    "IWorkflowRunner",
    "ValidationSeverity",
    "ValidationIssue",
    "ValidationReport",
    "IValidator",
    "ProvenanceRecordContract",
    "IProvenanceRecorder",
    "IQgisAdapter",
    "ILegacyAdapter",
]
