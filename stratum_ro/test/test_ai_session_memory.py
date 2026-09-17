# -*- coding: utf-8 -*-
"""
Unit tests for StratumRO AI Session Memory (MD 4 Sections 17-25, 30-32, 36).
Verifies SQLite storage, structured query APIs, scoped approvals,
crash recovery (INTERRUPTED state), credential sanitization, retention,
and concurrent write safety.
"""

import os
import shutil
import tempfile
import threading
import unittest

from stratum_ro.ai.memory.session import SessionMemory, sanitize_secrets


class TestAISessionMemory(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_memory.db")
        self.memory = SessionMemory(session_id="session_test_01", db_path=self.db_path)

    def tearDown(self):
        self.memory.close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_session_init_and_query(self):
        sess = self.memory.get_session("session_test_01")
        self.assertIsNotNone(sess)
        self.assertEqual(sess["session_id"], "session_test_01")
        self.assertEqual(sess["status"], "RUNNING")

    def test_task_recording_and_history(self):
        self.memory.record_task(
            task_id="task_001",
            tool="raster.extract_chip",
            status="SUCCESS",
            duration_sec=0.25,
            outputs={"chip_path": "workspace/output/chip.tif"},
            graph_id="graph_abc",
            confidence=0.95,
            artifact_reference="workspace/output/chip.tif"
        )

        history = self.memory.get_task_history("task_001")
        self.assertEqual(len(history), 1)
        record = history[0]
        self.assertEqual(record["tool"], "raster.extract_chip")
        self.assertEqual(record["status"], "SUCCESS")
        self.assertEqual(record["confidence"], 0.95)
        self.assertEqual(record["artifact_reference"], "workspace/output/chip.tif")

    def test_scoped_approval_recording(self):
        # 1. Record scoped approval for TopoLT export
        self.memory.record_approval(
            task_id="export_cad_01",
            approved=True,
            comment="Surveyor validated building boundaries",
            scope="export_topolt_dxf"
        )

        appr = self.memory.get_approval("export_cad_01")
        self.assertIsNotNone(appr)
        self.assertEqual(appr["decision"], "approved")
        self.assertEqual(appr["scope"], "export_topolt_dxf")
        self.assertIn("Surveyor", appr["reason"])

    def test_artifact_registration(self):
        # Create dummy file to test size tracking
        dummy_file = os.path.join(self.temp_dir, "test_model.gpkg")
        with open(dummy_file, "w") as f:
            f.write("DUMMY_GEOPACKAGE_DATA" * 100)

        self.memory.record_artifact(dummy_file, task_id="task_export")
        arts = self.memory.get_artifact_history()
        self.assertEqual(len(arts), 1)
        self.assertEqual(arts[0]["file_path"], dummy_file)
        self.assertGreater(arts[0]["file_size_kb"], 0.0)

    def test_crash_recovery_interrupted_state(self):
        # Simulate prior crash: another session in RUNNING state
        mem_old = SessionMemory(session_id="session_crashed_99", db_path=self.db_path)
        mem_old.record_task(
            task_id="task_stranded",
            tool="vector.regularize",
            status="RUNNING"
        )

        # New startup session triggers recovery
        mem_new = SessionMemory(session_id="session_fresh_100", db_path=self.db_path, auto_recover=True)

        # Verify old running task was transitioned to INTERRUPTED
        history = mem_new.get_task_history("task_stranded")
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["status"], "INTERRUPTED")

        old_sess = mem_new.get_session("session_crashed_99")
        self.assertEqual(old_sess["status"], "INTERRUPTED")
        mem_old.close()
        mem_new.close()

    def test_secret_sanitization_privacy(self):
        secret_key = "mock-secret-token-abcdef1234567890"
        leaked_output = {
            "api_key": secret_key,
            "error_msg": f"Authentication failed with {secret_key}",
            "safe_val": 42
        }

        self.memory.record_task(
            task_id="task_secret_test",
            tool="union_alpha.reason",
            status="FAILED",
            error=f"Unauthorized: Bearer {secret_key}",
            outputs=leaked_output
        )

        history = self.memory.get_task_history("task_secret_test")
        self.assertEqual(len(history), 1)
        err = history[0]["error"]
        self.assertNotIn(secret_key, err)
        self.assertIn("[REDACTED_SECRET]", err)

    def test_structured_search_and_validation_history(self):
        self.memory.record_memory_entry(
            category="validation",
            key="iou_benchmark",
            value={"mean_iou": 0.892, "cadastral_status": "PASS"},
            source="deterministic_validation",
            evidence_level="VALIDATED"
        )

        # Query validation history
        val_hist = self.memory.get_validation_history()
        self.assertEqual(len(val_hist), 1)
        self.assertEqual(val_hist[0]["key"], "iou_benchmark")

        # Search memory
        search_res = self.memory.search_memory("iou")
        self.assertGreater(len(search_res), 0)

    def test_retention_cleanup(self):
        # Insert records and test bounded retention
        for i in range(10):
            self.memory.record_task(f"t_old_{i}", tool="mock", status="SUCCESS")

        res = self.memory.cleanup_old_records(retention_days=0, keep_sessions=1)
        self.assertIn("deleted_tasks", res)

    def test_concurrent_multithreaded_writes(self):
        # Concurrency safety (Section 31): multiple threads writing simultaneously
        threads = []
        errors = []

        def worker(thread_idx: int):
            try:
                for j in range(20):
                    self.memory.record_task(
                        task_id=f"th_{thread_idx}_task_{j}",
                        tool="concurrent_tool",
                        status="SUCCESS",
                        duration_sec=0.01
                    )
            except Exception as e:
                errors.append(e)

        for i in range(5):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0, f"Thread errors: {errors}")
        runs = self.memory.get_recent_runs(limit=200)
        self.assertGreaterEqual(len(runs), 100)


if __name__ == "__main__":
    unittest.main()
