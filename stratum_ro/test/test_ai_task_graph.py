# -*- coding: utf-8 -*-
"""
Unit tests for StratumRO AI Task Graph, Event Bus, and Executor.
Verifies DAG dependency ordering, asynchronous event dispatching,
failure isolation, and human-in-the-loop approval gates.
"""

import unittest

from stratum_ro.ai.events import EventBus, EventType
from stratum_ro.ai.executor import TaskExecutor
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

        # Mark t1 as SUCCESS
        graph.mark_status("t1", TaskStatus.SUCCESS, outputs={"candidates": [1, 2, 3]})

        # Now t2 is ready
        ready2 = graph.get_ready_tasks()
        self.assertEqual(len(ready2), 1)
        self.assertEqual(ready2[0].id, "t2")

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
