# -*- coding: utf-8 -*-
"""
Asynchronous QThread Worker for StratumRO AI Task Graph Execution.
Executes the DAG workflow off the main UI thread and bridges EventBus
events into PyQt5 signals to ensure the QGIS GUI remains responsive.
"""

from typing import Any, Dict, Optional

try:
    from PyQt5 import QtCore
    from PyQt5.QtCore import pyqtSignal, QThread
    HAS_PYQT = True
except (ImportError, ModuleNotFoundError):
    HAS_PYQT = False
    import threading
    import time
    # Mock base class and signals for headless / non-GUI environments
    class QThread:
        def __init__(self, parent=None):
            self.parent = parent
            self._thread = None

        def start(self):
            self._thread = threading.Thread(target=self.run, daemon=True)
            self._thread.start()

        def wait(self, timeout_ms=5000):
            if self._thread and self._thread.is_alive():
                timeout_s = (timeout_ms / 1000.0) if timeout_ms is not None else None
                self._thread.join(timeout=timeout_s)

        def isRunning(self):
            return self._thread.is_alive() if self._thread else False

        def msleep(self, ms):
            time.sleep(max(0.005, min(0.05, ms / 1000.0)))

    class QtCore:
        class QObject: pass

    class MockBoundSignal:
        def __init__(self):
            self._callbacks = []

        def connect(self, slot):
            if slot not in self._callbacks:
                self._callbacks.append(slot)

        def disconnect(self, slot=None):
            if slot in self._callbacks:
                self._callbacks.remove(slot)
            elif slot is None:
                self._callbacks.clear()

        def emit(self, *args, **kwargs):
            for cb in list(self._callbacks):
                try:
                    cb(*args, **kwargs)
                except Exception:
                    pass

    class MockSignalDescriptor:
        def __init__(self, *args, **kwargs):
            self._name = None

        def __set_name__(self, owner, name):
            self._name = f"_mock_signal_{name}"

        def __get__(self, instance, owner):
            if instance is None:
                return self
            attr = self._name or f"_mock_sig_{id(self)}"
            if not hasattr(instance, attr):
                setattr(instance, attr, MockBoundSignal())
            return getattr(instance, attr)

    def pyqtSignal(*args, **kwargs):
        return MockSignalDescriptor(*args, **kwargs)

from .events import Event, EventBus, EventType, default_event_bus
from .executor import TaskExecutor
from .task_graph import TaskGraph, TaskNode, TaskStatus


class AITaskGraphWorker(QThread):
    """
    Asynchronous worker executing DAG tasks with PyQt signals for QGIS GUI updates.
    """
    taskStarted = pyqtSignal(str, str)            # task_id, task_name
    taskProgress = pyqtSignal(str, str, int)       # task_id, message, percent
    taskCompleted = pyqtSignal(str, str, float)    # task_id, task_name, duration_sec
    taskFailed = pyqtSignal(str, str)             # task_id, error_message
    approvalRequired = pyqtSignal(str, str, str)  # task_id, task_name, tool
    graphFinished = pyqtSignal(bool, str)         # success, message

    def __init__(
        self,
        graph: TaskGraph,
        executor: TaskExecutor,
        event_bus: Optional[EventBus] = None,
        parent=None
    ):
        super(AITaskGraphWorker, self).__init__(parent)
        self.graph = graph
        self.executor = executor
        self.event_bus = event_bus or default_event_bus
        self._is_cancelled = False

        # Connect EventBus events to Qt signals
        self.event_bus.subscribe(EventType.TASK_STARTED, self._on_bus_task_started)
        self.event_bus.subscribe(EventType.TASK_COMPLETED, self._on_bus_task_completed)
        self.event_bus.subscribe(EventType.TASK_FAILED, self._on_bus_task_failed)
        self.event_bus.subscribe(EventType.USER_APPROVAL_REQUIRED, self._on_bus_approval_required)

    def _on_bus_task_started(self, event: Event):
        task_name = event.data.get("tool", "Task")
        node = self.graph.get_task(event.task_id or "")
        if node:
            task_name = node.name
        self.taskStarted.emit(event.task_id or "", task_name)

    def _on_bus_task_completed(self, event: Event):
        dur = float(event.data.get("duration_sec", 0.0))
        task_name = event.message
        node = self.graph.get_task(event.task_id or "")
        if node:
            task_name = node.name
        self.taskCompleted.emit(event.task_id or "", task_name, dur)

    def _on_bus_task_failed(self, event: Event):
        err = event.data.get("error", "Eroare necunoscută")
        self.taskFailed.emit(event.task_id or "", str(err))

    def _on_bus_approval_required(self, event: Event):
        node = self.graph.get_task(event.task_id or "")
        name = node.name if node else "Task"
        tool = event.data.get("tool", "")
        self.approvalRequired.emit(event.task_id or "", name, tool)

    def cancel(self):
        self._is_cancelled = True

    def approve_task(self, task_id: str):
        """Resumes execution of a paused task after human approval."""
        self.executor.approve_task(task_id)

    def reject_task(self, task_id: str, reason: str = "User rejected execution"):
        """Rejects a task waiting for user approval and skips dependent tasks."""
        self.executor.reject_task(task_id, reason=reason)

    def run(self):
        """Main execution thread loop."""
        try:
            total_tasks = len(self.graph.list_tasks())
            step_count = 0

            while not self.graph.is_complete() and not self._is_cancelled:
                progressed = self.executor.execute_step()
                step_count += 1

                completed_count = len(self.graph.get_completed_ids())
                pct = int((completed_count / total_tasks) * 100) if total_tasks > 0 else 0
                self.taskProgress.emit("status", f"Progres: {completed_count}/{total_tasks} pași finalizați.", pct)

                if not progressed:
                    # Check if waiting for user approval
                    waiting = [
                        n for n in self.graph.list_tasks()
                        if n.status == TaskStatus.WAITING_FOR_USER
                    ]
                    if waiting:
                        # Wait in thread loop until approval is received or cancelled
                        self.msleep(50)
                        continue
                    else:
                        break

            if self._is_cancelled:
                self.graphFinished.emit(False, "Execuție întreruptă de utilizator.")
            elif self.graph.has_failed():
                failed_tasks = [t.name for t in self.graph.list_tasks() if t.status == TaskStatus.FAILED]
                self.graphFinished.emit(False, f"Fluxul a eșuat la pașii: {', '.join(failed_tasks)}.")
            else:
                self.graphFinished.emit(True, "Toate etapele fluxului geospațial au fost finalizate cu succes.")

        except Exception as exc:
            self.graphFinished.emit(False, f"Eroare neprevăzută în worker: {str(exc)}")
