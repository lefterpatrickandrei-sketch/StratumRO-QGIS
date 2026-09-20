# -*- coding: utf-8 -*-
"""
Risk Policy and Security Engine for StratumRO.
Enforces least-privilege execution, workspace containment, command allowlisting,
approval gates, and secret redaction.
"""

import os
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from .task_graph import RiskTolerance


class ActionRiskLevel(str, Enum):
    READ_ONLY = "read_only"         # Safe queries, layer reading, metadata inspection
    LOW_IMPACT = "low_impact"       # Non-destructive temporary scratch writes, local inference
    MEDIUM_IMPACT = "medium_impact" # Overwriting derivative files, running external models
    HIGH_IMPACT = "high_impact"     # Writing final cadastral files (.CP, DXF), launching subprocesses
    CRITICAL = "critical"           # Destructive operations, ground truth mutation, unconstrained shell


class RiskDecisionType(str, Enum):
    ALLOW = "allow"
    REQUIRE_APPROVAL = "require_approval"
    DENY = "deny"


@dataclass
class RiskDecision:
    decision: RiskDecisionType
    risk_level: ActionRiskLevel
    rationale: str
    requires_human_signoff: bool


class RiskEngine:
    """
    Evaluates requested actions against security boundaries and task risk tolerance.
    """

    # Commands explicitly prohibited or strictly controlled
    FORBIDDEN_COMMAND_PATTERNS = [
        r"\brmdir\s+/s\b",
        r"\bdel\s+/[fqs]\b",
        r"\bformat\b",
        r"\bdiskpart\b",
        r"\breg\s+delete\b",
        r"\bRemove-Item\s+-Recurse\b",
        r":(){ :|:& };:", # fork bomb
    ]

    # Sensitive key patterns to scrub
    SECRET_PATTERNS = [
        re.compile(r"sk-[a-zA-Z0-9_-]{20,}", re.IGNORECASE),
        re.compile(r"nvapi-[a-zA-Z0-9_-]{20,}", re.IGNORECASE),
        re.compile(r"Bearer\s+[a-zA-Z0-9_.-]{20,}", re.IGNORECASE),
        re.compile(r"(api[_-]?key\s*[:=]\s*['\"])[^'\"]+(['\"])", re.IGNORECASE),
    ]

    def __init__(self, workspace_root: Optional[str] = None):
        if workspace_root:
            self.workspace_root = Path(workspace_root).resolve()
        else:
            self.workspace_root = Path.cwd().resolve()

    def scrub_secrets(self, text: str) -> str:
        """Redacts API keys and credentials from logs or agent transcripts."""
        scrubbed = text
        for pat in self.SECRET_PATTERNS:
            scrubbed = pat.sub("[REDACTED_SECRET]", scrubbed)
        return scrubbed

    def check_path_confinement(self, target_path: str) -> bool:
        """Verifies target path does not escape the workspace boundary."""
        try:
            resolved = Path(target_path).resolve()
            # Allow workspace root and AppData temp/scratch if needed
            return self.workspace_root in resolved.parents or resolved == self.workspace_root
        except Exception:
            return False

    def evaluate_action(
        self,
        tool_name: str,
        parameters: Optional[Dict[str, Any]] = None,
        risk_tolerance: RiskTolerance = RiskTolerance.BALANCED,
    ) -> RiskDecision:
        """
        Evaluates a tool or workflow step against risk tolerance and returns a decision.
        """
        params = parameters or {}

        # 1. Check for critical or forbidden operations
        if tool_name in ("execute_shell", "run_command"):
            cmd = str(params.get("command", "") or params.get("CommandLine", ""))
            for pattern in self.FORBIDDEN_COMMAND_PATTERNS:
                if re.search(pattern, cmd, re.IGNORECASE):
                    return RiskDecision(
                        decision=RiskDecisionType.DENY,
                        risk_level=ActionRiskLevel.CRITICAL,
                        rationale=f"Command matches destructive pattern '{pattern}'. Execution denied.",
                        requires_human_signoff=True,
                    )

        # 2. Filesystem write boundary check
        if tool_name in ("write_file", "delete_file", "overwrite_file"):
            path = params.get("path") or params.get("TargetFile")
            if path and not self.check_path_confinement(str(path)):
                # If path escapes workspace
                return RiskDecision(
                    decision=RiskDecisionType.DENY,
                    risk_level=ActionRiskLevel.HIGH_IMPACT,
                    rationale=f"Path '{path}' is outside the authorized workspace '{self.workspace_root}'.",
                    requires_human_signoff=True,
                )

        # 3. Ground Truth modification protection
        target_path_str = str(params.get("path", "") or params.get("TargetFile", ""))
        if "data/ground_truth" in target_path_str.replace("\\", "/"):
            if tool_name not in ("read_file", "view_file", "inspect_layer"):
                return RiskDecision(
                    decision=RiskDecisionType.DENY,
                    risk_level=ActionRiskLevel.CRITICAL,
                    rationale="Ground truth datasets are frozen baselines. Modifications strictly forbidden.",
                    requires_human_signoff=True,
                )

        # 4. Determine risk level by tool type
        if tool_name in ("view_file", "read_file", "inspect_layer", "get_status", "ping"):
            risk_level = ActionRiskLevel.READ_ONLY
        elif tool_name in ("regularize_polygon", "sam2_predict", "extract_ndsm", "profile_data"):
            risk_level = ActionRiskLevel.LOW_IMPACT
        elif tool_name in ("export_cad_deliverables", "write_cp_file", "write_dxf"):
            risk_level = ActionRiskLevel.HIGH_IMPACT
        elif tool_name in ("execute_shell", "run_command"):
            risk_level = ActionRiskLevel.HIGH_IMPACT
        else:
            risk_level = ActionRiskLevel.MEDIUM_IMPACT

        # 5. Apply RiskTolerance policy
        if risk_tolerance == RiskTolerance.LOW:
            # Low risk tolerance requires human sign-off for anything beyond read-only
            if risk_level in (ActionRiskLevel.HIGH_IMPACT, ActionRiskLevel.CRITICAL):
                return RiskDecision(
                    decision=RiskDecisionType.REQUIRE_APPROVAL,
                    risk_level=risk_level,
                    rationale=f"Low risk tolerance requires human validation for {risk_level.value} action '{tool_name}'.",
                    requires_human_signoff=True,
                )
            if risk_level == ActionRiskLevel.MEDIUM_IMPACT:
                return RiskDecision(
                    decision=RiskDecisionType.REQUIRE_APPROVAL,
                    risk_level=risk_level,
                    rationale="Medium impact action requires sign-off under Low Risk Tolerance.",
                    requires_human_signoff=True,
                )

        elif risk_tolerance == RiskTolerance.BALANCED:
            # Balanced permits automated computation, requires signoff for final legal/cadastral deliverables or destructive ops
            if risk_level in (ActionRiskLevel.HIGH_IMPACT, ActionRiskLevel.CRITICAL):
                return RiskDecision(
                    decision=RiskDecisionType.REQUIRE_APPROVAL,
                    risk_level=risk_level,
                    rationale=f"High impact action '{tool_name}' requires surveyor sign-off (Human-in-the-Loop).",
                    requires_human_signoff=True,
                )

        # HIGH risk tolerance (sandbox) allows automated execution of low/medium/high, denying only CRITICAL
        return RiskDecision(
            decision=RiskDecisionType.ALLOW,
            risk_level=risk_level,
            rationale=f"Action '{tool_name}' permitted under {risk_tolerance.value} risk tolerance.",
            requires_human_signoff=False,
        )
