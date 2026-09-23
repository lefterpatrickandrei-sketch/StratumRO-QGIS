# -*- coding: utf-8 -*-
"""
StratumRO — Workflow, Task & Human Approval Contracts (Phase 2)
Declarative workflow orchestration, execution lifecycle, and human approval gates.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable


class WorkflowStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class ApprovalState(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    BYPASSED = "BYPASSED"


@dataclass
class ApprovalRequest:
    """
    Formal request presented to the human operator when a high/critical risk task is encountered.
    """
    request_id: str
    task_id: str
    task_name: str
    risk_level: str               # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    reason: str
    proposed_payload: Dict[str, Any] = field(default_factory=dict)
    state: ApprovalState = ApprovalState.PENDING
    created_at_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class ApprovalDecision:
    """
    Human operator decision recorded in the audit trail.
    """
    request_id: str
    decision: ApprovalState       # APPROVED or REJECTED
    approver_id: str              # User identity or licensed surveyor ID
    comments: str = ""
    decided_at_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@runtime_checkable
class IWorkflowRunner(Protocol):
    """
    Contract for workflow DAG runners.
    """
    def start_workflow(self, workflow_id: str, inputs: Dict[str, Any]) -> str:
        """Initiates an execution of a registered workflow DAG."""
        ...

    def get_status(self, execution_id: str) -> WorkflowStatus:
        """Queries current status of a workflow run."""
        ...

    def submit_approval(self, decision: ApprovalDecision) -> bool:
        """Submits human approval decision to unblock an awaiting workflow."""
        ...
