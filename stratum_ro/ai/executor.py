# -*- coding: utf-8 -*-
"""
Task Executor for StratumRO AI.
Executes DAG task nodes step-by-step or run-to-completion,
dispatching to registered tool adapters while enforcing event emission
and human-in-the-loop approval gates.
"""

import time
from typing import Any, Callable, Dict, Optional

from .events import EventBus, EventType, default_event_bus
from .task_graph import TaskGraph, TaskNode, TaskStatus


class TaskExecutor:
    """
    Executes tasks in a TaskGraph and reports progress via EventBus.
    """

    def __init__(self, graph: TaskGraph, event_bus: Optional[EventBus] = None):
        self.graph = graph
        self.event_bus = event_bus or default_event_bus
        self._tool_handlers: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {}

    def register_tool(self, tool_name: str, handler: Callable[[Dict[str, Any]], Dict[str, Any]]):
        """Registers a callable handler function for a specific tool identifier."""
        self._tool_handlers[tool_name] = handler

    def approve_task(self, task_id: str):
        """Approves a task that was suspended waiting for user approval."""
        node = self.graph.get_task(task_id)
        if not node:
            raise KeyError(f"Task '{task_id}' not found.")
        if node.status == TaskStatus.WAITING_FOR_USER:
            node.status = TaskStatus.PENDING
            node.requires_approval = False
            self.event_bus.emit(
                EventType.TASK_PROGRESS,
                task_id=task_id,
                message=f"User approved execution of task '{node.name}'."
            )

    def execute_step(self) -> bool:
        """
        Executes one batch of ready tasks.
        Returns True if at least one task executed or is waiting for approval;
        returns False if no ready tasks remain or graph is complete.
        """
        ready_tasks = self.graph.get_ready_tasks()
        if not ready_tasks:
            return False

        for task in ready_tasks:
            # Check approval gate
            if task.requires_approval:
                self.graph.mark_status(task.id, TaskStatus.WAITING_FOR_USER)
                self.event_bus.emit(
                    EventType.USER_APPROVAL_REQUIRED,
                    task_id=task.id,
                    message=f"Task '{task.name}' requires user confirmation before proceeding.",
                    tool=task.tool,
                    inputs=task.inputs
                )
                continue

            # Check if tool is available
            handler = self._tool_handlers.get(task.tool)
            if not handler:
                err_msg = f"Tool '{task.tool}' is not registered in executor."
                self.graph.mark_status(task.id, TaskStatus.FAILED, error=err_msg)
                self.event_bus.emit(
                    EventType.TASK_FAILED,
                    task_id=task.id,
                    message=err_msg,
                    error=err_msg
                )
                continue

            # Execute task
            self.graph.mark_status(task.id, TaskStatus.RUNNING)
            self.event_bus.emit(
                EventType.TASK_STARTED,
                task_id=task.id,
                message=f"Started executing task '{task.name}' with tool '{task.tool}'.",
                tool=task.tool
            )

            t0 = time.time()
            try:
                # Merge outputs of parent dependencies into inputs context if needed
                merged_inputs = dict(task.inputs)
                for dep_id in task.dependencies:
                    dep_node = self.graph.get_task(dep_id)
                    if dep_node and dep_node.outputs:
                        merged_inputs[f"dep_{dep_id}_outputs"] = dep_node.outputs

                result = handler(merged_inputs)
                elapsed = time.time() - t0

                conf = result.get("confidence") if isinstance(result, dict) else None
                self.graph.mark_status(
                    task.id,
                    TaskStatus.SUCCESS,
                    outputs=result if isinstance(result, dict) else {"result": result},
                    duration=elapsed,
                    confidence=conf
                )
                self.event_bus.emit(
                    EventType.TASK_COMPLETED,
                    task_id=task.id,
                    message=f"Completed task '{task.name}' in {elapsed:.2f}s.",
                    outputs=result,
                    duration_sec=round(elapsed, 3)
                )

            except Exception as exc:
                elapsed = time.time() - t0
                err_msg = str(exc)
                self.graph.mark_status(
                    task.id,
                    TaskStatus.FAILED,
                    error=err_msg,
                    duration=elapsed
                )
                self.event_bus.emit(
                    EventType.TASK_FAILED,
                    task_id=task.id,
                    message=f"Failed executing task '{task.name}': {err_msg}",
                    error=err_msg,
                    duration_sec=round(elapsed, 3)
                )

        return True

    def execute_all(self, max_steps: int = 50) -> TaskGraph:
        """
        Runs the execution loop until complete or paused for user approval.
        """
        steps = 0
        while not self.graph.is_complete() and steps < max_steps:
            progressed = self.execute_step()
            if not progressed:
                # Either waiting for approval or no tasks ready
                break
            steps += 1
        return self.graph
