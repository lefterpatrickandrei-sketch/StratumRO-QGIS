# -*- coding: utf-8 -*-
"""
Task Graph Data Structure for StratumRO AI.
Implements a Directed Acyclic Graph (DAG) of processing steps,
supporting dependency resolution, execution tracking, and human-in-the-loop approvals.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    RETRY = "retry"
    WAITING_FOR_USER = "waiting_for_user"


@dataclass
class TaskNode:
    id: str
    name: str
    tool: str
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    requires_approval: bool = False
    duration_sec: float = 0.0
    error: Optional[str] = None
    confidence: Optional[float] = None

    def is_ready(self, completed_task_ids: Set[str]) -> bool:
        """Returns True if all parent dependencies are satisfied."""
        return self.status == TaskStatus.PENDING and all(
            dep_id in completed_task_ids for dep_id in self.dependencies
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "tool": self.tool,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "dependencies": self.dependencies,
            "status": self.status.value,
            "requires_approval": self.requires_approval,
            "duration_sec": self.duration_sec,
            "error": self.error,
            "confidence": self.confidence,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskNode":
        return cls(
            id=data["id"],
            name=data["name"],
            tool=data["tool"],
            inputs=data.get("inputs", {}),
            outputs=data.get("outputs", {}),
            dependencies=data.get("dependencies", []),
            status=TaskStatus(data.get("status", TaskStatus.PENDING.value)),
            requires_approval=data.get("requires_approval", False),
            duration_sec=data.get("duration_sec", 0.0),
            error=data.get("error"),
            confidence=data.get("confidence"),
        )


class TaskGraph:
    """
    Stateful execution graph representing an AI-orchestrated geodetic workflow.
    """

    def __init__(self, goal: str = "", metadata: Optional[Dict[str, Any]] = None):
        self.goal = goal
        self.metadata = metadata or {}
        self._nodes: Dict[str, TaskNode] = {}

    def add_task(self, task: TaskNode):
        """Adds a task node to the graph."""
        if task.id in self._nodes:
            raise ValueError(f"Task with ID '{task.id}' already exists in graph.")
        self._nodes[task.id] = task

    def add_dependency(self, task_id: str, depends_on_id: str):
        """Adds a directional dependency: task_id depends on depends_on_id."""
        if task_id not in self._nodes or depends_on_id not in self._nodes:
            raise KeyError(f"Both '{task_id}' and '{depends_on_id}' must exist in graph.")
        if depends_on_id not in self._nodes[task_id].dependencies:
            self._nodes[task_id].dependencies.append(depends_on_id)

    def get_task(self, task_id: str) -> Optional[TaskNode]:
        return self._nodes.get(task_id)

    def list_tasks(self) -> List[TaskNode]:
        return list(self._nodes.values())

    def get_completed_ids(self) -> Set[str]:
        return {
            node.id for node in self._nodes.values()
            if node.status == TaskStatus.SUCCESS
        }

    def get_ready_tasks(self) -> List[TaskNode]:
        """Returns all tasks whose dependencies have succeeded and are ready for execution."""
        completed = self.get_completed_ids()
        return [node for node in self._nodes.values() if node.is_ready(completed)]

    def mark_status(
        self,
        task_id: str,
        status: TaskStatus,
        outputs: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        duration: float = 0.0,
        confidence: Optional[float] = None
    ):
        """Updates the status and results of a task node."""
        node = self._nodes.get(task_id)
        if not node:
            raise KeyError(f"Task '{task_id}' not found.")
        node.status = status
        if outputs is not None:
            node.outputs = outputs
        if error is not None:
            node.error = error
        if duration > 0.0:
            node.duration_sec = round(duration, 3)
        if confidence is not None:
            node.confidence = round(confidence, 3)

    def is_complete(self) -> bool:
        """Returns True if all nodes reached a terminal state (SUCCESS, FAILED, or SKIPPED)."""
        terminal = {TaskStatus.SUCCESS, TaskStatus.FAILED, TaskStatus.SKIPPED}
        return all(node.status in terminal for node in self._nodes.values())

    def has_failed(self) -> bool:
        """Returns True if any task node has failed."""
        return any(node.status == TaskStatus.FAILED for node in self._nodes.values())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "goal": self.goal,
            "metadata": self.metadata,
            "tasks": [n.to_dict() for n in self._nodes.values()]
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskGraph":
        graph = cls(goal=data.get("goal", ""), metadata=data.get("metadata", {}))
        for t_data in data.get("tasks", []):
            graph.add_task(TaskNode.from_dict(t_data))
        return graph
