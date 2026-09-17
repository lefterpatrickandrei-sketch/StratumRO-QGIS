import concurrent.futures
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from .events import EventBus, EventType, default_event_bus
from .router import AIRouter, RoutingDecision, TaskType
from .task_graph import TaskGraph, TaskNode, TaskStatus

# Non-transient exceptions that represent deterministic logic errors
NON_TRANSIENT_EXCEPTIONS = (
    ValueError,
    KeyError,
    TypeError,
    SyntaxError,
    ZeroDivisionError,
    AssertionError,
    AttributeError,
    ImportError,
    IndexError,
)

# Known transient error keywords in message strings
TRANSIENT_KEYWORDS = (
    "timeout",
    "timed out",
    "connection",
    "rate limit",
    "429",
    "502",
    "503",
    "504",
    "temporary",
    "transient",
    "busy",
    "reset by peer",
    "lock",
)


class TaskExecutor:
    """
    Executes tasks in a TaskGraph and reports fine-grained progress via EventBus.
    Supports DAG dependencies, selective retries, failure propagation,
    cooperative cancellation, parallel execution, and AIRouter delegation.
    """

    def __init__(
        self,
        graph: TaskGraph,
        event_bus: Optional[EventBus] = None,
        router: Optional[AIRouter] = None,
        max_workers: int = 4
    ):
        self.graph = graph
        self.event_bus = event_bus or default_event_bus
        self.router = router
        self.max_workers = max(1, max_workers)
        self._tool_handlers: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {}
        self._cancelled = False
        self._lock = threading.RLock()

    def register_tool(self, tool_name: str, handler: Callable[[Dict[str, Any]], Dict[str, Any]]):
        """Registers a callable handler function for a specific tool identifier."""
        with self._lock:
            self._tool_handlers[tool_name] = handler

    def cancel(self):
        """Cooperatively cancels running/pending tasks in the graph."""
        with self._lock:
            self._cancelled = True
            for task in self.graph.list_tasks():
                if task.status in {TaskStatus.PENDING, TaskStatus.WAITING_FOR_USER, TaskStatus.RETRY}:
                    self.graph.mark_status(
                        task.id,
                        TaskStatus.CANCELLED,
                        error="Execution cancelled by user or parent process."
                    )
                    self.event_bus.emit(
                        EventType.TASK_CANCELLED,
                        task_id=task.id,
                        message=f"Task '{task.name}' was cancelled."
                    )

    def is_cancelled(self) -> bool:
        """Returns True if the executor was cancelled."""
        return self._cancelled

    def approve_task(self, task_id: str):
        """Approves a task that was suspended waiting for user approval."""
        with self._lock:
            node = self.graph.get_task(task_id)
            if not node:
                raise KeyError(f"Task '{task_id}' not found.")
            if node.status == TaskStatus.WAITING_FOR_USER:
                self.graph.mark_status(task_id, TaskStatus.PENDING)
                node.requires_approval = False
                self.event_bus.emit(
                    EventType.TASK_PROGRESS,
                    task_id=task_id,
                    message=f"User approved execution of task '{node.name}'."
                )

    def reject_task(self, task_id: str, reason: str = "User rejected execution"):
        """Rejects a task waiting for user approval, cancelling it and skipping dependents."""
        with self._lock:
            node = self.graph.get_task(task_id)
            if not node:
                raise KeyError(f"Task '{task_id}' not found.")
            if node.status == TaskStatus.WAITING_FOR_USER:
                self.graph.mark_status(task_id, TaskStatus.CANCELLED, error=reason)
                self.event_bus.emit(
                    EventType.TASK_CANCELLED,
                    task_id=task_id,
                    message=f"Task '{node.name}' rejected: {reason}"
                )
                self._propagate_failure(task_id, reason=f"Upstream task '{node.name}' rejected by user")

    def _is_transient_error(self, exc: Exception) -> bool:
        """Determines if an exception is likely transient and safe to retry."""
        if isinstance(exc, (TimeoutError, ConnectionError, IOError, OSError)):
            return True

        if isinstance(exc, NON_TRANSIENT_EXCEPTIONS):
            return False

        err_str = str(exc).lower()
        return any(kw in err_str for kw in TRANSIENT_KEYWORDS)

    def _propagate_failure(self, failed_task_id: str, reason: Optional[str] = None):
        """Marks all downstream tasks that depend on the failed task as SKIPPED."""
        downstream = self.graph.get_downstream_tasks(failed_task_id)
        msg = reason or f"Skipped due to failed upstream dependency: '{failed_task_id}'"
        for dep in downstream:
            if dep.status in {TaskStatus.PENDING, TaskStatus.WAITING_FOR_USER, TaskStatus.RETRY}:
                self.graph.mark_status(dep.id, TaskStatus.SKIPPED, error=msg)
                self.event_bus.emit(
                    EventType.TASK_PROGRESS,
                    task_id=dep.id,
                    message=msg,
                    status=TaskStatus.SKIPPED.value
                )

    def _execute_single_task(self, task: TaskNode) -> bool:
        """Executes a single ready task node with retries and event publication."""
        if self._cancelled:
            if task.status in {TaskStatus.PENDING, TaskStatus.RETRY}:
                self.graph.mark_status(task.id, TaskStatus.CANCELLED, error="Cancelled before execution.")
                self.event_bus.emit(EventType.TASK_CANCELLED, task_id=task.id, message="Cancelled.")
            return False

        # 1. Approval Gate
        if task.requires_approval:
            self.graph.mark_status(task.id, TaskStatus.WAITING_FOR_USER)
            self.event_bus.emit(
                EventType.USER_APPROVAL_REQUIRED,
                task_id=task.id,
                message=f"Task '{task.name}' requires user confirmation before proceeding.",
                tool=task.tool,
                inputs=task.inputs
            )
            self.event_bus.emit(
                EventType.TASK_WAITING_FOR_USER,
                task_id=task.id,
                message=f"Task '{task.name}' is waiting for user approval."
            )
            return True

        # 2. Resolve Tool Handler or AIRouter
        handler: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None
        decision: Optional[RoutingDecision] = None

        with self._lock:
            if task.tool and task.tool in self._tool_handlers:
                handler = self._tool_handlers[task.tool]
                if not task.execution_target:
                    task.execution_target = "custom_tool"
            elif task.task_type and self.router:
                try:
                    t_type = TaskType(task.task_type) if isinstance(task.task_type, str) else task.task_type
                    decision = self.router.route_task(t_type)
                    task.execution_target = decision.execution_target
                    if decision.provider:
                        task.provider = decision.provider.name

                    self.event_bus.emit(
                        EventType.MODEL_SELECTED,
                        task_id=task.id,
                        message=f"Routed task '{task.name}' to target '{decision.execution_target}'.",
                        execution_target=decision.execution_target,
                        provider=task.provider,
                        rationale=decision.rationale
                    )

                    if decision.is_llm_task:
                        def llm_handler(ctx: Dict[str, Any]) -> Dict[str, Any]:
                            prompt = ctx.get("prompt", f"Execute {task.name}")
                            sys_p = ctx.get("system_prompt")
                            resp = self.router.execute_with_fallback(
                                t_type,
                                prompt=prompt,
                                system_prompt=sys_p,
                                context=ctx
                            )
                            if resp.is_ok():
                                return {
                                    "content": resp.content,
                                    "provider": resp.provider_name,
                                    "model": resp.model_name,
                                    "status": resp.status
                                }
                            raise RuntimeError(f"AI Provider execution failed: {resp.error}")

                        handler = llm_handler
                    else:
                        # Deterministic or local segmentation
                        handler = self._tool_handlers.get(task.tool) or self._tool_handlers.get(str(task.task_type))

                except Exception as route_err:
                    err_msg = f"Task routing error: {route_err}"
                    self.graph.mark_status(task.id, TaskStatus.FAILED, error=err_msg)
                    self.event_bus.emit(
                        EventType.TASK_FAILED,
                        task_id=task.id,
                        message=err_msg,
                        error=err_msg,
                        error_type="RoutingError",
                        recoverable=False
                    )
                    self._propagate_failure(task.id)
                    return False

        if not handler:
            err_msg = f"Tool '{task.tool or task.task_type}' is not registered in executor."
            self.graph.mark_status(task.id, TaskStatus.FAILED, error=err_msg)
            self.event_bus.emit(
                EventType.TASK_FAILED,
                task_id=task.id,
                message=err_msg,
                error=err_msg,
                error_type="UnregisteredToolError",
                recoverable=False
            )
            self._propagate_failure(task.id)
            return False

        # 3. Transition to RUNNING
        self.graph.mark_status(task.id, TaskStatus.RUNNING)
        self.event_bus.emit(
            EventType.TASK_STARTED,
            task_id=task.id,
            message=f"Started executing task '{task.name}' ({task.tool or task.task_type}).",
            tool=task.tool,
            task_type=task.task_type,
            execution_target=task.execution_target
        )

        # Merge outputs of parent dependencies into inputs
        merged_inputs = dict(task.inputs)
        for dep_id in task.dependencies:
            dep_node = self.graph.get_task(dep_id)
            if dep_node and dep_node.outputs:
                merged_inputs[f"dep_{dep_id}_outputs"] = dep_node.outputs

        # 4. Execution Loop with Retries
        while True:
            if self._cancelled:
                self.graph.mark_status(task.id, TaskStatus.CANCELLED, error="Cancelled during run.")
                self.event_bus.emit(EventType.TASK_CANCELLED, task_id=task.id, message="Task cancelled.")
                return False

            t0 = time.time()
            try:
                result = handler(merged_inputs)
                elapsed = time.time() - t0

                outputs = result if isinstance(result, dict) else {"result": result}
                conf = outputs.get("confidence") if isinstance(outputs, dict) else None

                self.graph.mark_status(
                    task.id,
                    TaskStatus.SUCCESS,
                    outputs=outputs,
                    duration=elapsed,
                    confidence=conf
                )
                self.event_bus.emit(
                    EventType.TASK_SUCCEEDED,
                    task_id=task.id,
                    message=f"Completed task '{task.name}' in {elapsed:.2f}s.",
                    outputs=outputs,
                    duration_sec=round(elapsed, 4)
                )
                return True

            except Exception as exc:
                elapsed = time.time() - t0
                err_msg = str(exc)
                is_transient = self._is_transient_error(exc)

                if is_transient and task.retry_count < task.max_retries:
                    task.retry_count += 1
                    self.graph.mark_status(task.id, TaskStatus.RETRY, error=err_msg, duration=elapsed)
                    self.event_bus.emit(
                        EventType.TASK_PROGRESS,
                        task_id=task.id,
                        message=(
                            f"Transient error in task '{task.name}': {err_msg}. "
                            f"Retrying ({task.retry_count}/{task.max_retries})..."
                        ),
                        retry_count=task.retry_count,
                        error=err_msg
                    )
                    # Prepare for next attempt
                    self.graph.mark_status(task.id, TaskStatus.RUNNING)
                    continue

                # Permanent failure or retries exhausted
                if task.status != TaskStatus.RUNNING:
                    self.graph.mark_status(task.id, TaskStatus.RUNNING)
                self.graph.mark_status(task.id, TaskStatus.FAILED, error=err_msg, duration=elapsed)
                self.event_bus.emit(
                    EventType.TASK_FAILED,
                    task_id=task.id,
                    message=f"Failed executing task '{task.name}': {err_msg}",
                    error=err_msg,
                    error_type=exc.__class__.__name__,
                    recoverable=False,
                    duration_sec=round(elapsed, 4)
                )
                self._propagate_failure(task.id)
                return False

    def execute_step(self, parallel: bool = False) -> bool:
        """
        Executes one batch of ready tasks.
        If parallel is True, runs independent ready tasks concurrently via ThreadPoolExecutor.
        Returns True if at least one task executed or is waiting for approval; False otherwise.
        """
        if self._cancelled:
            return False

        ready_tasks = self.graph.get_ready_tasks()
        if not ready_tasks:
            return False

        if parallel and len(ready_tasks) > 1:
            with concurrent.futures.ThreadPoolExecutor(max_workers=min(self.max_workers, len(ready_tasks))) as pool:
                futures = [pool.submit(self._execute_single_task, t) for t in ready_tasks]
                for f in concurrent.futures.as_completed(futures):
                    try:
                        f.result()
                    except Exception as err:
                        print(f"[TaskExecutor] Worker thread exception: {err}")
        else:
            for task in ready_tasks:
                if self._cancelled:
                    break
                self._execute_single_task(task)

        return True

    def execute_all(self, max_steps: int = 100, parallel: bool = False) -> TaskGraph:
        """
        Runs the execution loop until complete or paused for user approval.
        Emits GRAPH_STARTED, and upon completion GRAPH_COMPLETED or GRAPH_FAILED.
        """
        self.event_bus.emit(
            EventType.GRAPH_STARTED,
            message=f"Started execution of TaskGraph (goal: '{self.graph.goal}')."
        )

        steps = 0
        while not self.graph.is_complete() and not self._cancelled and steps < max_steps:
            progressed = self.execute_step(parallel=parallel)
            if not progressed:
                # Either waiting for user approval or blocked
                break
            steps += 1

        if self.graph.is_complete():
            if self.graph.has_failed() or self.graph.is_cancelled():
                self.event_bus.emit(
                    EventType.GRAPH_FAILED,
                    message=f"TaskGraph finished with errors or cancellation after {steps} step(s)."
                )
            else:
                self.event_bus.emit(
                    EventType.GRAPH_COMPLETED,
                    message=f"TaskGraph completed successfully in {steps} step(s)."
                )

        return self.graph

