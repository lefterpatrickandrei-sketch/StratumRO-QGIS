# -*- coding: utf-8 -*-
"""
Unit tests for DesktopOperator.
Tests capability auditing, structured logging, and fallback mechanisms.
"""

import os
import unittest
from tools.desktop_operator import DesktopOperator


class TestDesktopOperator(unittest.TestCase):

    def setUp(self):
        self.operator = DesktopOperator()

    def test_capability_audit_structure(self):
        cap = self.operator.check_desktop_capability()
        self.assertIn("available", cap)
        self.assertIn("mode", cap)
        self.assertIn(cap["mode"], ["REAL_DESKTOP", "PYQGIS_ONLY"])

    def test_structured_event_logging(self):
        evt = self.operator.log_event("test_stage", "test_action", "success", param1=42)
        self.assertEqual(evt.stage, "test_stage")
        self.assertEqual(evt.action, "test_action")
        self.assertEqual(evt.status, "success")
        self.assertEqual(evt.details.get("param1"), 42)
        self.assertTrue(len(self.operator.events) > 0)


if __name__ == "__main__":
    unittest.main()
