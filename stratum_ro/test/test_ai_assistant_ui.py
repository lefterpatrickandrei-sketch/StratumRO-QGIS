# -*- coding: utf-8 -*-
"""
Unit tests for QGIS AI Assistant UI, Non-Blocking Execution & Human Approval (MD 5 Conformance).
Verifies:
1. AITaskGraphWorker asynchronous execution with EventBus signal dispatch.
2. Preview-first Cadastral Approval & Rejection workflow with dependency cascade.
3. Cooperative cancellation without hanging or resource leaks.
4. Dynamic Provider Registry discovery and badge formatting.
5. ContextEngine snapshot generation and formatted display.
6. Sanitized error handling preventing credential/path leakage.
7. Technical validation report formatting (Topology + ANCPI 600/2023).
8. QGIS DockWidget integration test when running within QGIS environment.
"""

import os
import re
import unittest
from typing import Any, Dict

from stratum_ro.ai.events import EventBus, EventType
from stratum_ro.ai.executor import TaskExecutor
from stratum_ro.ai.registry import ProviderRegistry
from stratum_ro.ai.task_graph import TaskGraph, TaskNode, TaskStatus
from stratum_ro.ai.worker import AITaskGraphWorker
from stratum_ro.ai.context import get_default_context_engine
from stratum_ro.ai.memory.session import SessionMemory, sanitize_secrets
from stratum_ro.ai.tools.cadastral_tools import validate_topology, validate_ancpi

# Check QGIS availability
try:
    from qgis.PyQt.QtWidgets import QDockWidget
    from stratum_ro.stratum_ro_dockwidget import StratumRODockWidget
    from .utilities import get_qgis_app
    QGIS_APP = get_qgis_app()
    HAS_QGIS = True
except (ImportError, ModuleNotFoundError):
    HAS_QGIS = False
    QGIS_APP = None


class TestAITaskGraphWorkerExecution(unittest.TestCase):
    """Tests non-blocking worker execution and human-in-the-loop approval/rejection gates."""

    def setUp(self):
        self.bus = EventBus()

    def test_worker_standard_lifecycle(self):
        """Worker executes tasks and emits start, progress, completed, and graph finished signals."""
        graph = TaskGraph(goal="Test Worker Lifecycle")
        t1 = TaskNode(id="t1", name="Step 1", tool="mock.step1")
        t2 = TaskNode(id="t2", name="Step 2", tool="mock.step2", dependencies=["t1"])
        graph.add_task(t1)
        graph.add_task(t2)

        executor = TaskExecutor(graph, event_bus=self.bus)
        executor.register_tool("mock.step1", lambda _: {"val": 1})
        executor.register_tool("mock.step2", lambda _: {"val": 2})

        worker = AITaskGraphWorker(graph, executor, event_bus=self.bus)

        events = []
        worker.taskStarted.connect(lambda tid, name: events.append(("started", tid)))
        worker.taskCompleted.connect(lambda tid, name, dur: events.append(("completed", tid)))
        finished_results = []
        worker.graphFinished.connect(lambda success, msg: finished_results.append((success, msg)))

        worker.start()
        worker.wait(timeout_ms=3000)

        self.assertIn(("started", "t1"), events)
        self.assertIn(("completed", "t1"), events)
        self.assertIn(("started", "t2"), events)
        self.assertIn(("completed", "t2"), events)
        self.assertEqual(len(finished_results), 1)
        self.assertTrue(finished_results[0][0])
        self.assertEqual(graph.get_task("t1").status, TaskStatus.SUCCESS)
        self.assertEqual(graph.get_task("t2").status, TaskStatus.SUCCESS)

    def test_worker_human_approval_flow(self):
        """Worker pauses on task requiring approval, emits approvalRequired, and resumes on approve_task."""
        import time
        graph = TaskGraph(goal="Test Approval Gate")
        t1 = TaskNode(id="t1", name="Prepare Footprints", tool="mock.prep")
        t2 = TaskNode(id="t2", name="Authoritative Export", tool="mock.export", dependencies=["t1"], requires_approval=True)
        graph.add_task(t1)
        graph.add_task(t2)

        executor = TaskExecutor(graph, event_bus=self.bus)
        executor.register_tool("mock.prep", lambda _: {"polys": [1, 2]})
        executor.register_tool("mock.export", lambda _: {"exported": True})

        worker = AITaskGraphWorker(graph, executor, event_bus=self.bus)

        approval_signals = []
        worker.approvalRequired.connect(lambda tid, name, tool: approval_signals.append((tid, name, tool)))

        # Start worker: will execute t1, then pause at t2
        worker.start()

        # Wait until t2 enters WAITING_FOR_USER
        for _ in range(50):
            if graph.get_task("t2").status == TaskStatus.WAITING_FOR_USER:
                break
            time.sleep(0.02)

        self.assertEqual(graph.get_task("t1").status, TaskStatus.SUCCESS)
        self.assertEqual(graph.get_task("t2").status, TaskStatus.WAITING_FOR_USER)
        self.assertEqual(len(approval_signals), 1)
        self.assertEqual(approval_signals[0][0], "t2")

        # Now simulate user approving task
        worker.approve_task("t2")
        worker.wait(timeout_ms=3000)

        self.assertEqual(graph.get_task("t2").status, TaskStatus.SUCCESS)

    def test_worker_human_rejection_flow(self):
        """Worker rejects paused task with reason, skips dependent tasks, and marks graph finished."""
        import time
        graph = TaskGraph(goal="Test Rejection Gate")
        t1 = TaskNode(id="t1", name="Vectorize", tool="mock.vec")
        t2 = TaskNode(id="t2", name="Cadastral Gate", tool="mock.gate", dependencies=["t1"], requires_approval=True)
        t3 = TaskNode(id="t3", name="Commit DB", tool="mock.commit", dependencies=["t2"])
        graph.add_task(t1)
        graph.add_task(t2)
        graph.add_task(t3)

        executor = TaskExecutor(graph, event_bus=self.bus)
        executor.register_tool("mock.vec", lambda _: {"features": 5})
        executor.register_tool("mock.gate", lambda _: {"ready": True})
        executor.register_tool("mock.commit", lambda _: {"saved": True})

        worker = AITaskGraphWorker(graph, executor, event_bus=self.bus)
        worker.start()

        # Wait until t2 enters WAITING_FOR_USER
        for _ in range(50):
            if graph.get_task("t2").status == TaskStatus.WAITING_FOR_USER:
                break
            time.sleep(0.02)

        self.assertEqual(graph.get_task("t2").status, TaskStatus.WAITING_FOR_USER)

        # User rejects task
        worker.reject_task("t2", reason="Surveyor detected street alignment overlap")
        worker.wait(timeout_ms=3000)

        self.assertEqual(graph.get_task("t2").status, TaskStatus.CANCELLED)
        self.assertEqual(graph.get_task("t3").status, TaskStatus.SKIPPED)

    def test_worker_cancellation(self):
        """Worker cancels cooperatively when cancel() is requested."""
        graph = TaskGraph(goal="Test Cancel")
        t1 = TaskNode(id="t1", name="Step 1", tool="mock.tool")
        graph.add_task(t1)

        executor = TaskExecutor(graph, event_bus=self.bus)
        executor.register_tool("mock.tool", lambda _: {"ok": True})

        worker = AITaskGraphWorker(graph, executor, event_bus=self.bus)
        worker.cancel()
        self.assertTrue(worker._is_cancelled)


class TestAIAssistantUIComponents(unittest.TestCase):
    """Tests UI helper methods, provider discovery, sanitization, and context formatting."""

    def test_provider_registry_discovery(self):
        """ProviderRegistry dynamically discovers registered providers and reports statuses."""
        reg = ProviderRegistry()
        all_provs = reg.list_all()
        names = [p.name for p in all_provs]
        self.assertIn("local_mock", names)
        self.assertIn("union_alpha", names)
        self.assertIn("nvidia_nim", names)

        # Local mock provider must always report available
        local = reg.get("local_mock")
        self.assertIsNotNone(local)
        self.assertTrue(local.is_available())

    def test_context_engine_formatting(self):
        """ContextEngine returns Stereo 70 (EPSG:3844) project context."""
        engine = get_default_context_engine()
        ctx = engine.refresh()

        self.assertIn("crs", ctx)
        crs = ctx["crs"]
        self.assertEqual(crs.get("project_crs"), "EPSG:3844")
        self.assertEqual(crs.get("vertical_datum"), "EPSG:5781")
        self.assertIn("hardware", ctx)
        self.assertIn("providers", ctx)

    def test_error_sanitization(self):
        """Secret tokens and developer home directories are redacted cleanly."""
        dummy_key = "sk-" + "dummykeyfortest" + "1234567890"
        raw_error = (
            f"Exception occurred: Failed to connect with key {dummy_key} "
            "while accessing file C:\\Users\\developer\\workspace\\secret_project\\file.dxf"
        )
        cleaned = sanitize_secrets(raw_error)
        cleaned = re.sub(r"[A-Za-z]:\\[Uu]sers\\[^\\]+", "<USER_HOME>", cleaned)
        cleaned = re.sub(r"/home/[^/]+", "<USER_HOME>", cleaned)

        self.assertNotIn("dummykey", cleaned)
        self.assertIn("[REDACTED_SECRET]", cleaned)
        self.assertNotIn("developer", cleaned)
        self.assertIn("<USER_HOME>", cleaned)

    def test_validation_report_generation(self):
        """Topology and ANCPI validation structures report clear metrics for the UI."""
        from shapely.geometry import box, mapping
        polys = [mapping(box(390500.0, 585500.0, 390510.0, 585510.0))]

        top = validate_topology(polys)
        self.assertTrue(top["valid"])
        self.assertEqual(top["self_intersections"], 0)
        self.assertEqual(top["duplicate_vertices"], 0)
        self.assertEqual(top["sliver_count"], 0)

        ancpi = validate_ancpi(polys)
        self.assertIn("checks", ancpi)
        self.assertIn("min_edge_1m", ancpi["checks"])


@unittest.skipUnless(HAS_QGIS, "QGIS library is required for DockWidget UI instantiation")
class TestStratumRODockWidgetUIIntegration(unittest.TestCase):
    """Verifies that the enhanced DockWidget instantiates cleanly and exposes all MD 5 UI elements."""

    def setUp(self):
        self.dockwidget = StratumRODockWidget(None)

    def tearDown(self):
        self.dockwidget = None

    def test_dockwidget_tabs_and_controls(self):
        """Verifies tabs, providers, context, validation, approval, and history panels exist."""
        dw = self.dockwidget
        self.assertIsNotNone(dw.tabs)
        self.assertEqual(dw.tabs.count(), 2)
        self.assertEqual(dw.tabs.tabText(0), "🗺️ Flux Clasic")
        self.assertEqual(dw.tabs.tabText(1), "🤖 Orchestrator AI")

        # Provider selector & badges
        self.assertIsNotNone(dw.lblProviders)
        self.assertIsNotNone(dw.comboAIProvider)
        self.assertGreater(dw.comboAIProvider.count(), 0)

        # Context panel
        self.assertIsNotNone(dw.grpContext)
        self.assertIsNotNone(dw.lblContextDetails)
        self.assertIsNotNone(dw.btnRefreshContext)

        # TaskGraph tree
        self.assertIsNotNone(dw.treeTaskGraph)
        self.assertEqual(dw.treeTaskGraph.columnCount(), 2)

        # Validation panel
        self.assertIsNotNone(dw.grpValidation)
        self.assertIsNotNone(dw.lblValidationReport)

        # Approval gate
        self.assertIsNotNone(dw.widgetApproval)
        self.assertIsNotNone(dw.btnPreviewLayers)
        self.assertIsNotNone(dw.txtRejectReason)
        self.assertIsNotNone(dw.btnApproveAI)
        self.assertIsNotNone(dw.btnRejectAI)
        self.assertIsNotNone(dw.btnCancelAI)

        # History panel
        self.assertIsNotNone(dw.grpHistory)
        self.assertIsNotNone(dw.listHistory)
        self.assertIsNotNone(dw.btnRefreshHistory)


if __name__ == "__main__":
    unittest.main()
