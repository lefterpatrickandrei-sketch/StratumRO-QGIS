# -*- coding: utf-8 -*-
"""
Task Graph Data Structure for StratumRO AI.
Implements a Directed Acyclic Graph (DAG) of processing steps,
supporting dependency resolution, execution tracking, and human-in-the-loop approvals.
"""

import threading
from dataclasses import dataclass, field
from datetime import datetime
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
    CANCELLED = "cancelled"


# Deterministic state machine transition rules
VALID_TRANSITIONS: Dict[TaskStatus, Set[TaskStatus]] = {
    TaskStatus.PENDING: {
        TaskStatus.RUNNING,
        TaskStatus.WAITING_FOR_USER,
        TaskStatus.CANCELLED,
        TaskStatus.SKIPPED,
    },
    TaskStatus.WAITING_FOR_USER: {
        TaskStatus.PENDING,
        TaskStatus.RUNNING,
        TaskStatus.CANCELLED,
        TaskStatus.SKIPPED,
    },
    TaskStatus.RUNNING: {
        TaskStatus.SUCCESS,
        TaskStatus.FAILED,
        TaskStatus.CANCELLED,
        TaskStatus.RETRY,
        TaskStatus.WAITING_FOR_USER,
    },
    TaskStatus.RETRY: {
        TaskStatus.RUNNING,
        TaskStatus.FAILED,
        TaskStatus.CANCELLED,
    },
    # Terminal states: immutable
    TaskStatus.SUCCESS: set(),
    TaskStatus.FAILED: set(),
    TaskStatus.CANCELLED: set(),
    TaskStatus.SKIPPED: set(),
}


@dataclass
class TaskNode:
    id: str
    name: str
    tool: str = ""
    task_type: Optional[str] = None
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    requires_approval: bool = False
    duration_sec: float = 0.0
    error: Optional[str] = None
    confidence: Optional[float] = None
    execution_target: Optional[str] = None
    provider: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_ready(self, completed_task_ids: Set[str]) -> bool:
        """Returns True if task is pending or retry and all parent dependencies are satisfied."""
        return (self.status in {TaskStatus.PENDING, TaskStatus.RETRY}) and all(
            dep_id in completed_task_ids for dep_id in self.dependencies
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "tool": self.tool,
            "task_type": self.task_type,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "dependencies": list(self.dependencies),
            "status": self.status.value,
            "requires_approval": self.requires_approval,
            "duration_sec": self.duration_sec,
            "error": self.error,
            "confidence": self.confidence,
            "execution_target": self.execution_target,
            "provider": self.provider,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskNode":
        return cls(
            id=data["id"],
            name=data["name"],
            tool=data.get("tool", ""),
            task_type=data.get("task_type"),
            inputs=data.get("inputs", {}),
            outputs=data.get("outputs", {}),
            dependencies=data.get("dependencies", []),
            status=TaskStatus(data.get("status", TaskStatus.PENDING.value)),
            requires_approval=data.get("requires_approval", False),
            duration_sec=data.get("duration_sec", 0.0),
            error=data.get("error"),
            confidence=data.get("confidence"),
            execution_target=data.get("execution_target"),
            provider=data.get("provider"),
            retry_count=data.get("retry_count", 0),
            max_retries=data.get("max_retries", 0),
            created_at=data.get("created_at", datetime.now().isoformat()),
            started_at=data.get("started_at"),
            finished_at=data.get("finished_at"),
            metadata=data.get("metadata", {}),
        )


class TaskGraph:
    """
    Stateful Directed Acyclic Graph (DAG) representing an AI-orchestrated geodetic workflow.
    Guarantees acyclic dependency structure and deterministic state machine transitions.
    """

    def __init__(self, goal: str = "", metadata: Optional[Dict[str, Any]] = None):
        self._lock = threading.RLock()
        self.goal = goal
        self.metadata = metadata or {}
        self._nodes: Dict[str, TaskNode] = {}

    def add_task(self, task: TaskNode):
        """Adds a task node to the graph."""
        with self._lock:
            if task.id in self._nodes:
                raise ValueError(f"Task with ID '{task.id}' already exists in graph.")
            self._nodes[task.id] = task
            # Validate that existing dependencies don't create cycles
            if self._has_cycle():
                del self._nodes[task.id]
                raise ValueError(f"Adding task '{task.id}' would introduce a cycle into the graph.")

    def add_dependency(self, task_id: str, depends_on_id: str):
        """Adds a directional dependency: task_id depends on depends_on_id."""
        with self._lock:
            if task_id not in self._nodes or depends_on_id not in self._nodes:
                raise KeyError(f"Both '{task_id}' and '{depends_on_id}' must exist in graph.")
            if task_id == depends_on_id:
                raise ValueError(f"Task '{task_id}' cannot depend on itself.")

            if depends_on_id not in self._nodes[task_id].dependencies:
                self._nodes[task_id].dependencies.append(depends_on_id)
                if self._has_cycle():
                    self._nodes[task_id].dependencies.remove(depends_on_id)
                    raise ValueError(
                        f"Dependency from '{task_id}' to '{depends_on_id}' creates a cycle in the task graph."
                    )

    def _has_cycle(self) -> bool:
        """Cycle detection using depth-first search graph coloring."""
        visited: Dict[str, int] = {}  # 0=unvisited, 1=visiting, 2=visited

        def dfs(node_id: str) -> bool:
            visited[node_id] = 1  # visiting
            node = self._nodes.get(node_id)
            if node:
                for dep_id in node.dependencies:
                    if dep_id not in self._nodes:
                        continue
                    if visited.get(dep_id, 0) == 1:
                        return True  # cycle detected
                    if visited.get(dep_id, 0) == 0:
                        if dfs(dep_id):
                            return True
            visited[node_id] = 2  # visited
            return False

        for n_id in self._nodes:
            if visited.get(n_id, 0) == 0:
                if dfs(n_id):
                    return True
        return False

    def get_task(self, task_id: str) -> Optional[TaskNode]:
        with self._lock:
            return self._nodes.get(task_id)

    def list_tasks(self) -> List[TaskNode]:
        with self._lock:
            return list(self._nodes.values())

    def get_completed_ids(self) -> Set[str]:
        with self._lock:
            return {
                node.id for node in self._nodes.values()
                if node.status == TaskStatus.SUCCESS
            }

    def get_ready_tasks(self) -> List[TaskNode]:
        """Returns all tasks whose dependencies have succeeded and are ready for execution."""
        with self._lock:
            completed = {
                node.id for node in self._nodes.values()
                if node.status == TaskStatus.SUCCESS
            }
            return [node for node in self._nodes.values() if node.is_ready(completed)]

    def get_downstream_tasks(self, task_id: str) -> List[TaskNode]:
        """Returns all tasks that directly or indirectly depend on task_id."""
        with self._lock:
            downstream: List[TaskNode] = []
            visited: Set[str] = set()
            queue = [task_id]

            while queue:
                current_id = queue.pop(0)
                for node in self._nodes.values():
                    if current_id in node.dependencies and node.id not in visited:
                        visited.add(node.id)
                        downstream.append(node)
                        queue.append(node.id)

            return downstream

    def mark_status(
        self,
        task_id: str,
        status: TaskStatus,
        outputs: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        duration: float = 0.0,
        confidence: Optional[float] = None
    ):
        """
        Updates the status and execution artifacts of a task node.
        Enforces deterministic state machine transition rules.
        """
        with self._lock:
            node = self._nodes.get(task_id)
            if not node:
                raise KeyError(f"Task '{task_id}' not found.")

            # Check deterministic state transition
            current_status = node.status
            if status != current_status:
                allowed = VALID_TRANSITIONS.get(current_status, set())
                if status not in allowed:
                    raise ValueError(
                        f"Illegal state transition for task '{task_id}': "
                        f"cannot transition from {current_status.value} to {status.value}."
                    )

            node.status = status
            now_iso = datetime.now().isoformat()

            if status == TaskStatus.RUNNING and not node.started_at:
                node.started_at = now_iso

            if status in {TaskStatus.SUCCESS, TaskStatus.FAILED, TaskStatus.CANCELLED, TaskStatus.SKIPPED}:
                node.finished_at = now_iso

            if outputs is not None:
                node.outputs = outputs
            if error is not None:
                node.error = error
            if duration > 0.0:
                node.duration_sec = round(duration, 4)
            if confidence is not None:
                node.confidence = round(confidence, 4)

    def is_complete(self) -> bool:
        """Returns True if all nodes reached a terminal state (SUCCESS, FAILED, SKIPPED, or CANCELLED)."""
        with self._lock:
            terminal = {TaskStatus.SUCCESS, TaskStatus.FAILED, TaskStatus.SKIPPED, TaskStatus.CANCELLED}
            return len(self._nodes) > 0 and all(node.status in terminal for node in self._nodes.values())

    def has_failed(self) -> bool:
        """Returns True if any task node has failed."""
        with self._lock:
            return any(node.status == TaskStatus.FAILED for node in self._nodes.values())

    def is_cancelled(self) -> bool:
        """Returns True if any task node was cancelled."""
        with self._lock:
            return any(node.status == TaskStatus.CANCELLED for node in self._nodes.values())

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
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
