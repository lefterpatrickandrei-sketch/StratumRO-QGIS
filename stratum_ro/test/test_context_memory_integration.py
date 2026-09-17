# -*- coding: utf-8 -*-
"""
Integration tests for StratumRO AI Context, Session Memory, EventBus, and MCP (MD 4).
Verifies:
1. TaskGraph execution automatically feeds SessionMemory via EventBus.
2. Context + Memory combined agent package with task-aware filtering.
3. FastMCP read-only tool invocation for context and memory queries.
"""

import asyncio
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

from stratum_ro.ai.context import get_agent_context_package
from stratum_ro.ai.events import EventBus
from stratum_ro.ai.executor import TaskExecutor
from stratum_ro.ai.memory import MemoryEventSubscriber, SessionMemory
from stratum_ro.ai.task_graph import TaskGraph, TaskNode


class TestContextMemoryIntegration(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "integration_memory.db")
        self.session_id = "test_integration_run_01"
        self.memory = SessionMemory(session_id=self.session_id, db_path=self.db_path)
        self.event_bus = EventBus()
        self.subscriber = MemoryEventSubscriber(memory=self.memory, event_bus=self.event_bus)

    def tearDown(self):
        self.subscriber.detach()
        self.memory.close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_task_graph_to_memory_pipeline(self):
        """
        Executes a 2-node TaskGraph and verifies that EventBus lifecycle events
        are captured and persisted into SQLite memory without manual logging.
        """
        graph = TaskGraph(goal="Inspect and segment")
        task1 = TaskNode(
            id="t1_inspect",
            name="Inspect LiDAR",
            tool="lidar.inspect",
            inputs={"laz_path": "data/teren.laz"}
        )
        task2 = TaskNode(
            id="t2_segment",
            name="Segment buildings",
            tool="segmentation.run_sam2",
            inputs={"candidate_count": 5},
            dependencies=["t1_inspect"]
        )
        graph.add_task(task1)
        graph.add_task(task2)

        executor = TaskExecutor(graph=graph, event_bus=self.event_bus, max_workers=2)
        executor.register_tool("lidar.inspect", lambda args: {"point_count": 1250000})
        executor.register_tool("segmentation.run_sam2", lambda args: {"building_count": 5, "status": "success"})

        executor.execute_all()
        self.assertTrue(graph.is_complete())
        self.assertFalse(graph.has_failed())

        # Verify tasks were persisted to SQLite
        t1_hist = self.memory.get_task_history("t1_inspect")
        self.assertGreaterEqual(len(t1_hist), 1)
        # Final status should be SUCCESS
        self.assertEqual(t1_hist[-1]["status"], "SUCCESS")

        t2_hist = self.memory.get_task_history("t2_segment")
        self.assertGreaterEqual(len(t2_hist), 1)
        self.assertEqual(t2_hist[-1]["status"], "SUCCESS")

        # Verify recent runs contains both
        recent = self.memory.get_recent_runs(limit=10)
        tool_names = [r["tool"] for r in recent]
        self.assertIn("lidar.inspect", tool_names)
        self.assertIn("segmentation.run_sam2", tool_names)

    def test_agent_context_package_filtering(self):
        """
        Tests task-aware relevance filtering in get_agent_context_package:
        - segmentation tasks prioritize raster/lidar and past segmentations
        - export tasks prioritize CRS, approvals, and previous export artifacts
        """
        # Populate some memory items
        self.memory.record_task(
            task_id="prev_seg",
            tool="segmentation.run_sam2",
            status="SUCCESS",
            outputs={"buildings": 12}
        )
        self.memory.record_approval(
            task_id="prev_export",
            approved=True,
            comment="Approved DXF submission",
            scope="export_topolt_dxf"
        )
        self.memory.record_artifact("workspace/output/official.dxf")

        # 1. Package for segmentation task
        pkg_seg = get_agent_context_package(task_type="segmentation", session_id=self.session_id)
        self.assertEqual(pkg_seg["task_type"], "segmentation")
        self.assertIn("environment", pkg_seg)
        self.assertIn("inputs", pkg_seg["environment"])
        self.assertIn("past_segmentations", pkg_seg["relevant_memory"])

        # 2. Package for export task
        pkg_exp = get_agent_context_package(task_type="export", session_id=self.session_id)
        self.assertEqual(pkg_exp["task_type"], "export")
        self.assertIn("approvals", pkg_exp["relevant_memory"])
        self.assertIn("exported_artifacts", pkg_exp["relevant_memory"])

    def test_mcp_context_and_memory_tools(self):
        """
        Tests invocation of the 7 new FastMCP read-only context & memory tools.
        """
        repo_root = Path(__file__).resolve().parent.parent.parent
        sys.path.insert(0, str(repo_root / "mcp"))
        import stratumro_server

        # 1. context.get
        res_ctx = stratumro_server.tool_context_get()
        self.assertIn("project", res_ctx)
        self.assertIn("crs", res_ctx)

        # 2. context.get_aoi
        res_aoi = stratumro_server.tool_context_get_aoi()
        self.assertIn("bbox", res_aoi)
        self.assertIn("source", res_aoi)

        # 3. context.get_layers
        res_layers = stratumro_server.tool_context_get_layers()
        self.assertIsInstance(res_layers, list)

        # 4. context.get_inputs
        res_inputs = stratumro_server.tool_context_get_inputs()
        self.assertIn("rasters", res_inputs)
        self.assertIn("lidar", res_inputs)

        # 5. memory.get_recent_runs
        res_runs = stratumro_server.tool_memory_get_recent_runs(limit=5)
        self.assertIsInstance(res_runs, list)

        # 6. memory.get_task_history
        res_th = stratumro_server.tool_memory_get_task_history("t1_inspect")
        self.assertIsInstance(res_th, list)

        # 7. memory.search
        res_search = stratumro_server.tool_memory_search("segment")
        self.assertIsInstance(res_search, list)


if __name__ == "__main__":
    unittest.main()
