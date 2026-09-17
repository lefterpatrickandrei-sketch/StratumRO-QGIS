# -*- coding: utf-8 -*-
"""
EventBus Listener for Session Memory Persistence (MD 4 Section 28).
Decoupled event-driven integration translating TaskGraph lifecycle events
into persistent SQLite memory records without coupling TaskGraph internals.
"""

from typing import Any, Dict, Optional
from stratum_ro.ai.events import Event, EventBus, EventType, default_event_bus
from stratum_ro.ai.memory.session import SessionMemory


class MemoryEventSubscriber:
    """
    Subscribes to TaskGraph and workflow events on EventBus and persists them to SessionMemory.
    """

    def __init__(self, memory: SessionMemory, event_bus: Optional[EventBus] = None):
        self.memory = memory
        self.event_bus = event_bus or default_event_bus
        self._subscribed = False
        self.attach()

    def attach(self):
        """Attaches callbacks to all relevant lifecycle event types."""
        if self._subscribed:
            return
        self.event_bus.subscribe(EventType.TASK_STARTED, self._on_task_started)
        self.event_bus.subscribe(EventType.TASK_SUCCEEDED, self._on_task_succeeded)
        self.event_bus.subscribe(EventType.TASK_COMPLETED, self._on_task_succeeded)
        self.event_bus.subscribe(EventType.TASK_FAILED, self._on_task_failed)
        self.event_bus.subscribe(EventType.VALIDATION_COMPLETED, self._on_validation_completed)
        self.event_bus.subscribe(EventType.USER_APPROVAL_REQUIRED, self._on_approval_required)
        self.event_bus.subscribe(EventType.GRAPH_STARTED, self._on_graph_started)
        self.event_bus.subscribe(EventType.GRAPH_COMPLETED, self._on_graph_completed)
        self._subscribed = True

    def detach(self):
        """Unsubscribes from all events."""
        if not self._subscribed:
            return
        self.event_bus.unsubscribe(EventType.TASK_STARTED, self._on_task_started)
        self.event_bus.unsubscribe(EventType.TASK_SUCCEEDED, self._on_task_succeeded)
        self.event_bus.unsubscribe(EventType.TASK_COMPLETED, self._on_task_succeeded)
        self.event_bus.unsubscribe(EventType.TASK_FAILED, self._on_task_failed)
        self.event_bus.unsubscribe(EventType.VALIDATION_COMPLETED, self._on_validation_completed)
        self.event_bus.unsubscribe(EventType.USER_APPROVAL_REQUIRED, self._on_approval_required)
        self.event_bus.unsubscribe(EventType.GRAPH_STARTED, self._on_graph_started)
        self.event_bus.unsubscribe(EventType.GRAPH_COMPLETED, self._on_graph_completed)
        self._subscribed = False

    def _on_task_started(self, event: Event):
        task_id = event.task_id or event.data.get("task_id", "unknown_task")
        tool = event.data.get("tool", "unknown_tool")
        graph_id = event.data.get("graph_id")
        self.memory.record_task(
            task_id=task_id,
            tool=tool,
            status="RUNNING",
            graph_id=graph_id,
            source="event_bus"
        )

    def _on_task_succeeded(self, event: Event):
        task_id = event.task_id or event.data.get("task_id", "unknown_task")
        tool = event.data.get("tool", "unknown_tool")
        duration = event.data.get("duration", 0.0)
        outputs = event.data.get("outputs") or event.data.get("result")
        artifact = event.data.get("artifact_reference") or event.data.get("output_path")
        self.memory.record_task(
            task_id=task_id,
            tool=tool,
            status="SUCCESS",
            duration_sec=duration,
            outputs=outputs if isinstance(outputs, dict) else {"result": str(outputs)},
            artifact_reference=artifact,
            evidence_level="TESTED" if "test" in str(tool) else "OBSERVED",
            source="event_bus"
        )
        if artifact:
            self.memory.record_artifact(str(artifact), task_id=task_id)

    def _on_task_failed(self, event: Event):
        task_id = event.task_id or event.data.get("task_id", "unknown_task")
        tool = event.data.get("tool", "unknown_tool")
        error_msg = event.message or event.data.get("error", "Task failed")
        self.memory.record_task(
            task_id=task_id,
            tool=tool,
            status="FAILED",
            error=str(error_msg),
            source="event_bus"
        )

    def _on_validation_completed(self, event: Event):
        task_id = event.task_id or event.data.get("task_id")
        metrics = event.data.get("metrics") or event.data
        self.memory.record_memory_entry(
            category="validation",
            key=f"validation_{task_id or 'run'}",
            value=metrics,
            source="deterministic_validation",
            evidence_level="VALIDATED",
            task_id=task_id
        )

    def _on_approval_required(self, event: Event):
        task_id = event.task_id or event.data.get("task_id", "unknown_task")
        scope = event.data.get("scope", "general")
        self.memory.record_approval(
            task_id=task_id,
            approved=False,
            comment=event.message or "Pending surveyor review",
            scope=scope,
            decision="pending"
        )

    def _on_graph_started(self, event: Event):
        graph_id = event.data.get("graph_id", "default_graph")
        self.memory.record_memory_entry(
            category="graph",
            key=f"graph_started_{graph_id}",
            value={"graph_id": graph_id, "tasks_count": event.data.get("tasks_count", 0)},
            source="task_graph",
            evidence_level="OBSERVED"
        )

    def _on_graph_completed(self, event: Event):
        graph_id = event.data.get("graph_id", "default_graph")
        self.memory.record_memory_entry(
            category="graph",
            key=f"graph_completed_{graph_id}",
            value={"graph_id": graph_id, "success": event.data.get("success", True)},
            source="task_graph",
            evidence_level="MEASURED"
        )


def attach_memory_to_event_bus(memory: SessionMemory, event_bus: Optional[EventBus] = None) -> MemoryEventSubscriber:
    """Convenience helper to attach a SessionMemory listener to an EventBus."""
    return MemoryEventSubscriber(memory=memory, event_bus=event_bus)
