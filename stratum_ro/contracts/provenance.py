# -*- coding: utf-8 -*-
"""
StratumRO — Provenance & Audit Trail Contracts (Phase 2)
Standardized W3C PROV-O audit trail contracts for end-to-end reproducibility.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable


@dataclass
class ProvenanceRecordContract:
    """
    Structured lineage node representing one discrete processing step.
    """
    activity_id: str
    activity_name: str
    input_hashes: Dict[str, str] = field(default_factory=dict)     # path -> sha256
    parameters: Dict[str, Any] = field(default_factory=dict)       # parameters snapshot
    output_hashes: Dict[str, str] = field(default_factory=dict)    # path -> sha256
    operator_id: str = "system"
    timestamp_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    parent_activity_ids: List[str] = field(default_factory=list)


@runtime_checkable
class IProvenanceRecorder(Protocol):
    """
    Contract for audit trail and provenance record keepers.
    """
    def record_activity(
        self,
        activity_name: str,
        inputs: Dict[str, str],
        parameters: Dict[str, Any],
        outputs: Dict[str, str],
        operator_id: str = "system"
    ) -> ProvenanceRecordContract:
        """Appends a new provenance node to the chain."""
        ...

    def get_lineage(self, activity_id: str) -> List[ProvenanceRecordContract]:
        """Retrieves causal parent lineage for an activity."""
        ...

    def export_manifest(self, output_path: str) -> str:
        """Serializes complete provenance chain as JSON manifest."""
        ...
