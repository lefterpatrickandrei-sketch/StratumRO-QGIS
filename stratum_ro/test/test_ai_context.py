# -*- coding: utf-8 -*-
"""
Unit tests for StratumRO AI Project Context and Session Memory.
Verifies config loading, threshold extraction, session tracking,
and reproducible audit log persistence.
"""

import json
import os
import shutil
import tempfile
import unittest

from stratum_ro.ai.context import ProjectContext
from stratum_ro.ai.memory.session import SessionMemory


class TestAIContextAndSession(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_project_context_load_config(self):
        ctx = ProjectContext.load_from_config("config.yaml")
        self.assertEqual(ctx.crs, "EPSG:3844")
        self.assertEqual(ctx.vertical_datum, "EPSG:5781")
        self.assertIn("min_building_height_m", ctx.thresholds)
        self.assertAlmostEqual(ctx.thresholds["eave_offset_meters"], 0.40)
        self.assertAlmostEqual(ctx.thresholds["mrr_rectangularity_trigger"], 0.70)

        d = ctx.to_dict()
        self.assertEqual(d["crs"], "EPSG:3844")
        self.assertIsInstance(d["thresholds"], dict)

    def test_session_memory_audit_trail(self):
        session = SessionMemory(session_id="test_run_01")
        session.record_task(
            task_id="t1",
            tool="lidar.inspect",
            status="success",
            duration_sec=0.45,
            outputs={"point_count": 4620000}
        )
        session.record_approval(
            task_id="t2",
            approved=True,
            comment="Approved building regularization"
        )
        session.record_artifact("workspace/output/test_cad.dxf")

        log_path = session.save_audit_log(output_dir=self.temp_dir)
        self.assertTrue(os.path.isfile(log_path))

        with open(log_path, "r", encoding="utf-8") as f:
            audit_data = json.load(f)

        self.assertEqual(audit_data["session_id"], "test_run_01")
        self.assertEqual(audit_data["tasks_count"], 1)
        self.assertEqual(audit_data["approvals_count"], 1)
        self.assertEqual(audit_data["artifacts_count"], 1)
        self.assertEqual(audit_data["tasks"][0]["tool"], "lidar.inspect")
        self.assertTrue(audit_data["approvals"][0]["approved"])


if __name__ == "__main__":
    unittest.main()
