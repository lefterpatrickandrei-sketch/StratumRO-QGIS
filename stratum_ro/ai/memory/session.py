# -*- coding: utf-8 -*-
"""
Session Memory & Reproducibility Audit Engine for StratumRO AI.
Persists execution logs, intermediate artifact paths, and user approval history
to structured JSON records conforming to AGENTS.md evidence rules.
"""

import json
import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional


class SessionMemory:
    """
    Stateful memory recording workflow execution and user approvals.
    """

    def __init__(self, session_id: Optional[str] = None):
        self.session_id = session_id or f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.start_time = time.time()
        self.task_history: List[Dict[str, Any]] = []
        self.approvals: List[Dict[str, Any]] = []
        self.artifacts: List[str] = []

    def record_task(
        self,
        task_id: str,
        tool: str,
        status: str,
        duration_sec: float = 0.0,
        outputs: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        confidence: Optional[float] = None
    ):
        """Appends a task record to session history."""
        record = {
            "task_id": task_id,
            "tool": tool,
            "status": status,
            "duration_sec": round(duration_sec, 3),
            "timestamp": datetime.now().isoformat(),
            "confidence": confidence,
            "outputs_summary": {k: type(v).__name__ for k, v in (outputs or {}).items()},
            "error": error
        }
        self.task_history.append(record)

    def record_approval(self, task_id: str, approved: bool = True, comment: str = ""):
        """Records a human-in-the-loop decision."""
        self.approvals.append({
            "task_id": task_id,
            "approved": approved,
            "comment": comment,
            "timestamp": datetime.now().isoformat()
        })

    def record_artifact(self, file_path: str):
        """Tracks an output file generated during the session."""
        if file_path not in self.artifacts:
            self.artifacts.append(file_path)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "duration_total_sec": round(time.time() - self.start_time, 2),
            "tasks_count": len(self.task_history),
            "approvals_count": len(self.approvals),
            "artifacts_count": len(self.artifacts),
            "tasks": self.task_history,
            "approvals": self.approvals,
            "artifacts": self.artifacts
        }

    def save_audit_log(self, output_dir: str = "workspace/output") -> str:
        """Saves session audit trail to disk."""
        os.makedirs(output_dir, exist_ok=True)
        log_path = os.path.join(output_dir, f"session_audit_{self.session_id}.json")
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)
        return log_path
