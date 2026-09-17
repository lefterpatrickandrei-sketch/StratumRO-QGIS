# -*- coding: utf-8 -*-
"""
Unit tests for StratumRO AI Task Graph, Event Bus, and Executor (MD 2).
Verifies DAG dependency ordering, state machine transition enforcement,
cycle detection, failure propagation, selective retries, cooperative cancellation,
parallel execution, and AIRouter delegation.
"""

import time
import unittest

from stratum_ro.ai.events import EventBus, EventType
from stratum_ro.ai.executor import TaskExecutor
from stratum_ro.ai.registry import ProviderRegistry
from stratum_ro.ai.router import AIRouter, TaskType
from stratum_ro.ai.task_graph import TaskGraph, TaskNode, TaskStatus


class TestAITaskGraphAndExecutor(unittest.TestCase):

    def setUp(self):
        self.bus = EventBus()

    def test_event_bus_pub_sub(self):
        received_events = []

        def callback(event):
            received_events.append(event)

        self.bus.subscribe(EventType.TASK_STARTED, callback)
        self.bus.emit(EventType.TASK_STARTED, task_id="t1", message="Started")
        self.bus.emit(EventType.TASK_COMPLETED, task_id="t1", message="Done")

        self.assertEqual(len(received_events), 1)
        self.assertEqual(received_events[0].task_id, "t1")
        self.assertEqual(received_events[0].message, "Started")

        # Unsubscribe
        self.bus.unsubscribe(EventType.TASK_STARTED, callback)
        self.bus.emit(EventType.TASK_STARTED, task_id="t2", message="Started 2")
        self.assertEqual(len(received_events), 1)

    def test_task_graph_dependencies(self):
        graph = TaskGraph(goal="Extract and regularize buildings")
        t1 = TaskNode(id="t1", name="Detect Candidates", tool="lidar.detect")
        t2 = TaskNode(id="t2", name="Segment SAM2", tool="sam2.segment", dependencies=["t1"])

        graph.add_task(t1)
        graph.add_task(t2)

        # Initially only t1 is ready
        ready = graph.get_ready_tasks()
        self.assertEqual(len(ready), 1)
        self.assertEqual(ready[0].id, "t1")

        # Transition t1: PENDING -> RUNNING -> SUCCESS
        graph.mark_status("t1", TaskStatus.RUNNING)
        graph.mark_status("t1", TaskStatus.SUCCESS, outputs={"candidates": [1, 2, 3]})

        # Now t2 is ready
        ready2 = graph.get_ready_tasks()
        self.assertEqual(len(ready2), 1)
        self.assertEqual(ready2[0].id, "t2")

    def test_task_graph_state_machine_transition_enforcement(self):
        """Rejects illegal state transitions, e.g. PENDING -> SUCCESS without RUNNING."""
        graph = TaskGraph(goal="Test State Machine")
        t1 = TaskNode(id="t1", name="Step 1", tool="mock.tool")
        graph.add_task(t1)

        # 1. PENDING -> SUCCESS must raise ValueError
        with self.assertRaises(ValueError) as ctx:
            graph.mark_status("t1", TaskStatus.SUCCESS)
        self.assertIn("cannot transition from pending to success", str(ctx.exception))

        # 2. PENDING -> RUNNING -> SUCCESS is valid
        graph.mark_status("t1", TaskStatus.RUNNING)
        graph.mark_status("t1", TaskStatus.SUCCESS)
        self.assertEqual(graph.get_task("t1").status, TaskStatus.SUCCESS)

        # 3. Terminal state cannot transition back to RUNNING or PENDING
        with self.assertRaises(ValueError) as ctx:
            graph.mark_status("t1", TaskStatus.RUNNING)
        self.assertIn("cannot transition from success to running", str(ctx.exception))

    def test_dag_cycle_detection(self):
        """Adding cyclic dependencies must be prevented and raise ValueError."""
        graph = TaskGraph(goal="Test Cycle Detection")
        t1 = TaskNode(id="t1", name="Task 1", tool="mock.tool")
        t2 = TaskNode(id="t2", name="Task 2", tool="mock.tool")
        t3 = TaskNode(id="t3", name="Task 3", tool="mock.tool")

        graph.add_task(t1)
        graph.add_task(t2)
        graph.add_task(t3)

        # Self-dependency
        with self.assertRaises(ValueError):
            graph.add_dependency("t1", "t1")

        # Linear dependency: t2 depends on t1, t3 depends on t2
        graph.add_dependency("t2", "t1")
        graph.add_dependency("t3", "t2")

        # Cyclic dependency: t1 depends on t3
        with self.assertRaises(ValueError):
            graph.add_dependency("t1", "t3")

    def test_failure_propagation(self):
        """When a task fails, all transitive downstream tasks are marked SKIPPED."""
        graph = TaskGraph(goal="Test Failure Propagation")
        t1 = TaskNode(id="t1", name="Task 1", tool="fail.tool")
        t2 = TaskNode(id="t2", name="Task 2", tool="mock.tool", dependencies=["t1"])
        t3 = TaskNode(id="t3", name="Task 3", tool="mock.tool", dependencies=["t2"])

        graph.add_task(t1)
        graph.add_task(t2)
        graph.add_task(t3)

        executor = TaskExecutor(graph, event_bus=self.bus)

        def raise_err(_):
            raise RuntimeError("Database connection lost")

        executor.register_tool("fail.tool", raise_err)
        executor.register_tool("mock.tool", lambda _: {"ok": True})

        executor.execute_all()

        self.assertTrue(graph.is_complete())
        self.assertTrue(graph.has_failed())
        self.assertEqual(graph.get_task("t1").status, TaskStatus.FAILED)
        self.assertEqual(graph.get_task("t2").status, TaskStatus.SKIPPED)
        self.assertEqual(graph.get_task("t3").status, TaskStatus.SKIPPED)
        self.assertIn("failed upstream dependency", graph.get_task("t2").error)

    def test_cooperative_cancellation(self):
        """Cancelling the executor marks remaining unexecuted tasks as CANCELLED."""
        graph = TaskGraph(goal="Test Cancellation")
        t1 = TaskNode(id="t1", name="Task 1", tool="step1")
        t2 = TaskNode(id="t2", name="Task 2", tool="step2", dependencies=["t1"])

        graph.add_task(t1)
        graph.add_task(t2)

        executor = TaskExecutor(graph, event_bus=self.bus)
        executor.register_tool("step1", lambda _: {"val": 1})
        executor.register_tool("step2", lambda _: {"val": 2})

        # Cancel before step 1
        executor.cancel()
        self.assertTrue(executor.is_cancelled())

        executor.execute_all()

        self.assertEqual(graph.get_task("t1").status, TaskStatus.CANCELLED)
        self.assertEqual(graph.get_task("t2").status, TaskStatus.CANCELLED)
        self.assertTrue(graph.is_cancelled())

    def test_selective_retry_transient_error(self):
        """Transient errors are automatically retried up to max_retries."""
        graph = TaskGraph(goal="Test Retries")
        t_retry = TaskNode(id="t_retry", name="Network Task", tool="net.fetch", max_retries=2)
        graph.add_task(t_retry)

        executor = TaskExecutor(graph, event_bus=self.bus)

        call_count = [0]

        def transient_handler(_):
            call_count[0] += 1
            if call_count[0] < 3:
                raise ConnectionError("Connection timed out (transient network glitch)")
            return {"downloaded": True}

        executor.register_tool("net.fetch", transient_handler)
        executor.execute_all()

        self.assertEqual(call_count[0], 3)
        self.assertEqual(graph.get_task("t_retry").status, TaskStatus.SUCCESS)
        self.assertEqual(graph.get_task("t_retry").retry_count, 2)
        self.assertEqual(graph.get_task("t_retry").outputs["downloaded"], True)

    def test_selective_retry_rejects_deterministic_error(self):
        """Deterministic errors (e.g. ValueError, KeyError) are NOT retried."""
        graph = TaskGraph(goal="Test Deterministic Failure")
        t_det = TaskNode(id="t_det", name="Math Task", tool="calc.bad", max_retries=5)
        graph.add_task(t_det)

        executor = TaskExecutor(graph, event_bus=self.bus)

        call_count = [0]

        def deterministic_handler(_):
            call_count[0] += 1
            raise ValueError("Invalid polygon: self-intersection at vertex 3")

        executor.register_tool("calc.bad", deterministic_handler)
        executor.execute_all()

        # Must NOT retry: called exactly once!
        self.assertEqual(call_count[0], 1)
        self.assertEqual(graph.get_task("t_det").status, TaskStatus.FAILED)
        self.assertEqual(graph.get_task("t_det").retry_count, 0)

    def test_parallel_independent_tasks_execution(self):
        """Independent tasks execute concurrently when parallel=True."""
        graph = TaskGraph(goal="Test Parallel Execution")
        t1 = TaskNode(id="t1", name="Task 1", tool="sleep.tool", inputs={"dur": 0.05})
        t2 = TaskNode(id="t2", name="Task 2", tool="sleep.tool", inputs={"dur": 0.05})
        t3 = TaskNode(id="t3", name="Task 3", tool="sleep.tool", inputs={"dur": 0.05})

        graph.add_task(t1)
        graph.add_task(t2)
        graph.add_task(t3)

        executor = TaskExecutor(graph, event_bus=self.bus, max_workers=3)

        def sleeper(inputs):
            time.sleep(inputs["dur"])
            return {"slept": inputs["dur"]}

        executor.register_tool("sleep.tool", sleeper)

        t_start = time.time()
        executor.execute_all(parallel=True)
        total_time = time.time() - t_start

        self.assertTrue(graph.is_complete())
        self.assertFalse(graph.has_failed())
        # 3 tasks of 0.05s executed in parallel should complete in < 0.12s, well below serial 0.15s
        self.assertLess(total_time, 0.14)

    def test_router_integration_offline(self):
        """AIRouter automatically selects target and fallback provider for unhandled tasks (100% offline)."""
        graph = TaskGraph(goal="Test Router Fallback")
        t_ai = TaskNode(
            id="t_ai",
            name="Cadastral Planning",
            task_type="planning",
            inputs={"prompt": "Suggest regularization workflow"}
        )
        graph.add_task(t_ai)

        # Use an isolated registry with local provider only to ensure zero network requests and fast execution
        registry = ProviderRegistry()
        for name in list(registry._providers.keys()):
            if name not in ("local", "local_mock"):
                del registry._providers[name]

        router = AIRouter(registry=registry)
        executor = TaskExecutor(graph, event_bus=self.bus, router=router)

        executor.execute_all()

        task = graph.get_task("t_ai")
        self.assertEqual(task.status, TaskStatus.SUCCESS)
        self.assertTrue(task.execution_target.startswith("provider:"))
        self.assertIn("content", task.outputs)

    def test_human_in_the_loop_rejection(self):
        """A user rejecting a task waiting for approval cancels it and skips dependents."""
        graph = TaskGraph(goal="Test Rejection Gate")
        t_check = TaskNode(id="t_check", name="Surveyor Signoff", tool="mock.tool", requires_approval=True)
        t_export = TaskNode(id="t_export", name="CAD Export", tool="mock.tool", dependencies=["t_check"])

        graph.add_task(t_check)
        graph.add_task(t_export)

        executor = TaskExecutor(graph, event_bus=self.bus)
        executor.register_tool("mock.tool", lambda _: {"ok": True})

        # Run step: t_check pauses
        executor.execute_all()
        self.assertEqual(graph.get_task("t_check").status, TaskStatus.WAITING_FOR_USER)

        # Reject task
        executor.reject_task("t_check", reason="Surveyor detected boundary overlap")
        executor.execute_all()

        self.assertEqual(graph.get_task("t_check").status, TaskStatus.CANCELLED)
        self.assertEqual(graph.get_task("t_export").status, TaskStatus.SKIPPED)

    def test_graph_lifecycle_events(self):
        """Verifies GRAPH_STARTED and GRAPH_COMPLETED are emitted."""
        events_emitted = []

        def tracker(event):
            events_emitted.append(event.event_type)

        self.bus.subscribe(EventType.GRAPH_STARTED, tracker)
        self.bus.subscribe(EventType.GRAPH_COMPLETED, tracker)

        graph = TaskGraph(goal="Lifecycle Test")
        graph.add_task(TaskNode(id="t1", name="Quick Task", tool="quick.tool"))

        executor = TaskExecutor(graph, event_bus=self.bus)
        executor.register_tool("quick.tool", lambda _: {"done": True})

        executor.execute_all()

        self.assertIn(EventType.GRAPH_STARTED, events_emitted)
        self.assertIn(EventType.GRAPH_COMPLETED, events_emitted)

    def test_task_graph_serialization(self):
        graph = TaskGraph(goal="Test DAG")
        graph.add_task(TaskNode(id="t1", name="Step 1", tool="mock.tool"))
        graph.add_task(TaskNode(id="t2", name="Step 2", tool="mock.tool", dependencies=["t1"]))

        d = graph.to_dict()
        restored = TaskGraph.from_dict(d)

        self.assertEqual(restored.goal, "Test DAG")
        self.assertEqual(len(restored.list_tasks()), 2)
        self.assertEqual(restored.get_task("t2").dependencies, ["t1"])

    def test_executor_run_dag(self):
        graph = TaskGraph(goal="Run DAG pipeline")
        graph.add_task(TaskNode(id="step1", name="Step 1", tool="calc.add", inputs={"a": 10, "b": 20}))
        graph.add_task(TaskNode(id="step2", name="Step 2", tool="calc.double", dependencies=["step1"]))

        executor = TaskExecutor(graph, event_bus=self.bus)

        # Register tool handlers
        executor.register_tool("calc.add", lambda inputs: {"sum": inputs["a"] + inputs["b"]})
        executor.register_tool(
            "calc.double",
            lambda inputs: {"doubled": inputs["dep_step1_outputs"]["sum"] * 2}
        )

        executor.execute_all()

        self.assertTrue(graph.is_complete())
        self.assertFalse(graph.has_failed())
        self.assertEqual(graph.get_task("step1").outputs["sum"], 30)
        self.assertEqual(graph.get_task("step2").outputs["doubled"], 60)

    def test_executor_approval_gate(self):
        """A task with requires_approval=True pauses until explicitly approved."""
        graph = TaskGraph(goal="Test Approval Gate")
        t_safe = TaskNode(id="t_safe", name="Inspect", tool="test.safe")
        t_write = TaskNode(
            id="t_write",
            name="Write to disk",
            tool="test.write",
            dependencies=["t_safe"],
            requires_approval=True
        )

        graph.add_task(t_safe)
        graph.add_task(t_write)

        executor = TaskExecutor(graph, event_bus=self.bus)
        executor.register_tool("test.safe", lambda _: {"inspected": True})
        executor.register_tool("test.write", lambda _: {"written": True})

        # Run step 1: t_safe executes, t_write becomes ready but pauses
        executor.execute_all()

        self.assertEqual(graph.get_task("t_safe").status, TaskStatus.SUCCESS)
        self.assertEqual(graph.get_task("t_write").status, TaskStatus.WAITING_FOR_USER)
        self.assertFalse(graph.is_complete())

        # Approve and resume
        executor.approve_task("t_write")
        executor.execute_all()

        self.assertEqual(graph.get_task("t_write").status, TaskStatus.SUCCESS)
        self.assertTrue(graph.is_complete())

    def test_executor_handles_tool_failure(self):
        graph = TaskGraph(goal="Test Failure")
        graph.add_task(TaskNode(id="t_fail", name="Failing Task", tool="error.tool"))

        executor = TaskExecutor(graph, event_bus=self.bus)

        def raise_err(_):
            raise RuntimeError("Out of memory on GPU")

        executor.register_tool("error.tool", raise_err)
        executor.execute_all()

        self.assertTrue(graph.is_complete())
        self.assertTrue(graph.has_failed())
        self.assertEqual(graph.get_task("t_fail").status, TaskStatus.FAILED)
        self.assertIn("Out of memory", graph.get_task("t_fail").error)


if __name__ == "__main__":
    unittest.main()

