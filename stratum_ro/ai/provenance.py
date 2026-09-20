# -*- coding: utf-8 -*-
"""
Evidence and Provenance Lineage Engine for StratumRO.
Attaches structured, immutable lineage records to every generated deliverable,
tracking data source, transformation parameters, validation checks, and operator.
"""

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class EvidenceClass(str, Enum):
    OBSERVED = "OBSERVED"                      # Direct sensor data (Orthophoto, raw LiDAR)
    DERIVED = "DERIVED"                        # Computed deterministically (nDSM, slope, DTM)
    MODEL_PREDICTION = "MODEL_PREDICTION"      # Deep learning inference (SAM 2 mask)
    HEURISTIC = "HEURISTIC"                    # Rule-based filtering (ExG vegetation mask)
    HUMAN_DECISION = "HUMAN_DECISION"          # Geodetic surveyor verification or manual edit
    EXTERNAL_REFERENCE = "EXTERNAL_REFERENCE"  # ANCPI reference layer, official cadastre
    SYNTHETIC = "SYNTHETIC"                    # Procedurally generated CAD geometries
    SIMULATED = "SIMULATED"                    # Controlled perturbation for failure analysis


@dataclass
class ProvenanceRecord:
    record_id: str
    timestamp: str
    evidence_class: EvidenceClass
    step_name: str
    operator: str
    inputs: List[str]
    outputs: List[str]
    parameters: Dict[str, Any] = field(default_factory=dict)
    validation_status: str = "UNCHECKED"
    human_signed_off: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["evidence_class"] = self.evidence_class.value
        return d


class ProvenanceChain:
    """
    Maintains a chronological DAG of provenance records for a given task or dataset.
    """

    def __init__(self, task_id: Optional[str] = None):
        self.task_id = task_id or f"task_{uuid.uuid4().hex[:8]}"
        self.records: List[ProvenanceRecord] = []

    def record_step(
        self,
        evidence_class: EvidenceClass,
        step_name: str,
        operator: str,
        inputs: List[str],
        outputs: List[str],
        parameters: Optional[Dict[str, Any]] = None,
        validation_status: str = "PASSED",
        human_signed_off: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ProvenanceRecord:
        """Appends an immutable provenance step to the lineage chain."""
        rec = ProvenanceRecord(
            record_id=f"rec_{len(self.records) + 1:04d}_{uuid.uuid4().hex[:6]}",
            timestamp=datetime.now(timezone.utc).isoformat(),
            evidence_class=evidence_class,
            step_name=step_name,
            operator=operator,
            inputs=inputs,
            outputs=outputs,
            parameters=parameters or {},
            validation_status=validation_status,
            human_signed_off=human_signed_off,
            metadata=metadata or {},
        )
        self.records.append(rec)
        return rec

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "record_count": len(self.records),
            "created_at": self.records[0].timestamp if self.records else None,
            "latest_update": self.records[-1].timestamp if self.records else None,
            "has_human_signoff": any(r.human_signed_off for r in self.records),
            "lineage": [r.to_dict() for r in self.records],
        }

    def save_to_file(self, filepath: str):
        """Persists the provenance chain as JSON."""
        p = Path(filepath)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load_from_file(cls, filepath: str) -> "ProvenanceChain":
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        chain = cls(task_id=data.get("task_id"))
        for item in data.get("lineage", []):
            rec = ProvenanceRecord(
                record_id=item["record_id"],
                timestamp=item["timestamp"],
                evidence_class=EvidenceClass(item["evidence_class"]),
                step_name=item["step_name"],
                operator=item["operator"],
                inputs=item["inputs"],
                outputs=item["outputs"],
                parameters=item.get("parameters", {}),
                validation_status=item.get("validation_status", "UNCHECKED"),
                human_signed_off=item.get("human_signed_off", False),
                metadata=item.get("metadata", {}),
            )
            chain.records.append(rec)
        return chain
