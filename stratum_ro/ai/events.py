# -*- coding: utf-8 -*-
"""
Event Bus & Notification Engine for StratumRO AI.
Provides decoupled event publication and subscription for UI updates,
progress tracking, audit logging, and human-in-the-loop approval gates.
"""

import threading
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class EventType(str, Enum):
    # Task lifecycle events
    TASK_CREATED = "task_created"
    TASK_STARTED = "task_started"
    TASK_PROGRESS = "task_progress"
    TASK_SUCCEEDED = "task_succeeded"
    TASK_COMPLETED = "task_completed"  # Standard / backwards compatible alias
    TASK_FAILED = "task_failed"
    TASK_CANCELLED = "task_cancelled"
    TASK_WAITING_FOR_USER = "task_waiting_for_user"
    USER_APPROVAL_REQUIRED = "user_approval_required"

    # Graph lifecycle events
    GRAPH_STARTED = "graph_started"
    GRAPH_COMPLETED = "graph_completed"
    GRAPH_FAILED = "graph_failed"

    # Provider & validation events
    MODEL_SELECTED = "model_selected"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    RESULT_CREATED = "result_created"
    VALIDATION_COMPLETED = "validation_completed"


@dataclass
class Event:
    event_type: EventType
    task_id: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)
    message: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class EventBus:
    """
    Thread-safe publish/subscribe event dispatcher.
    """

    def __init__(self):
        self._lock = threading.RLock()
        self._subscribers: Dict[EventType, List[Callable[[Event], None]]] = {
            t: [] for t in EventType
        }
        self._history: List[Event] = []

    def subscribe(self, event_type: EventType, callback: Callable[[Event], None]):
        """Subscribes a listener to an event type."""
        with self._lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            if callback not in self._subscribers[event_type]:
                self._subscribers[event_type].append(callback)

    def unsubscribe(self, event_type: EventType, callback: Callable[[Event], None]):
        """Unsubscribes a listener from an event type."""
        with self._lock:
            if event_type in self._subscribers and callback in self._subscribers[event_type]:
                self._subscribers[event_type].remove(callback)

    def emit(self, event_type: EventType, task_id: Optional[str] = None, message: str = "", **kwargs) -> Event:
        """Publishes an event to all subscribed listeners and records history."""
        event = Event(
            event_type=event_type,
            task_id=task_id,
            message=message,
            data=kwargs
        )
        with self._lock:
            self._history.append(event)
            # Copy subscriber list to allow callbacks to mutate subscribers safely
            callbacks = list(self._subscribers.get(event_type, []))
            # Also notify TASK_COMPLETED listeners if event is TASK_SUCCEEDED and vice-versa
            if event_type == EventType.TASK_SUCCEEDED and EventType.TASK_COMPLETED in self._subscribers:
                for cb in self._subscribers[EventType.TASK_COMPLETED]:
                    if cb not in callbacks:
                        callbacks.append(cb)
            elif event_type == EventType.TASK_COMPLETED and EventType.TASK_SUCCEEDED in self._subscribers:
                for cb in self._subscribers[EventType.TASK_SUCCEEDED]:
                    if cb not in callbacks:
                        callbacks.append(cb)

        for callback in callbacks:
            try:
                callback(event)
            except Exception as err:
                print(f"[EventBus] Error in listener callback for {event_type.value}: {err}")

        return event

    def get_history(self, event_type: Optional[EventType] = None) -> List[Event]:
        """Returns recorded event history, optionally filtered by event type."""
        with self._lock:
            if event_type is None:
                return list(self._history)
            return [e for e in self._history if e.event_type == event_type]

    def clear(self):
        """Clears subscribers and event history."""
        with self._lock:
            for t in EventType:
                self._subscribers[t].clear()
            self._history.clear()


# Default singleton event bus instance
default_event_bus = EventBus()
