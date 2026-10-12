# -*- coding: utf-8 -*-
"""
Unit tests for StratumRO Geospatial Platform API and Closed-Loop Orchestrator.
"""

import unittest
from pathlib import Path
from fastapi.testclient import TestClient

from stratum_ro.api.app import app
from stratum_ro.api.service import PlatformService, TRANSFORMER_3844_TO_4326
from stratum_ro.ai.closed_loop import ClosedLoopOrchestrator, TestResults, QGISLiveStatus


class TestPlatformAPI(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_health_endpoint(self):
        resp = self.client.get("/api/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "OPERATIONAL")
        self.assertIn("Stereo 70", data["geodetic"]["crs"])
        self.assertIn("qgis_engine", data)
        self.assertIn("providers", data)

    def test_workflow_modes_endpoint(self):
        resp = self.client.get("/api/workflow/modes")
        self.assertEqual(resp.status_code, 200)
        modes = resp.json()
        self.assertIsInstance(modes, list)
        self.assertGreaterEqual(len(modes), 4)
        mode_ids = [m["id"] for m in modes]
        self.assertIn("assisted_cadastre", mode_ids)
        self.assertIn("urban_3d_lod1", mode_ids)

    def test_workflow_run_endpoint(self):
        payload = {"mode": "assisted_cadastre", "regularize_90": True}
        resp = self.client.post("/api/workflow/run", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "COMPLETED")
        self.assertEqual(data["mode"], "assisted_cadastre")
        self.assertIn("metrics", data)
        self.assertIn("deliverables", data)

    def test_export_cp_endpoint(self):
        resp = self.client.get("/api/export/cp")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("text/plain", resp.headers["content-type"])
        self.assertIn("attachment; filename=imobil_1001_stratumro.cp", resp.headers["content-disposition"])
        self.assertIn("392120", resp.text)

    def test_export_pad_endpoint(self):
        resp = self.client.get("/api/export/pad")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("PLAN DE AMPLASAMENT SI DELIMITARE", resp.text)
        self.assertIn("Stereografic 1970", resp.text)

        # MultiPolygon robustness check
        from unittest.mock import patch
        import geopandas as gpd
        from shapely.geometry import MultiPolygon, Polygon
        mp = MultiPolygon([
            Polygon([(390500, 585800), (390510, 585800), (390510, 585810), (390500, 585810)]),
            Polygon([(390520, 585820), (390530, 585820), (390530, 585830), (390520, 585830)])
        ])
        fake_gdf = gpd.GeoDataFrame([{"geometry": mp}], crs="EPSG:3844")
        with patch("geopandas.read_file", return_value=fake_gdf):
            resp_mp = self.client.get("/api/export/pad")
            self.assertEqual(resp_mp.status_code, 200)
            self.assertIn("Corp 1", resp_mp.text)
            self.assertIn("Corp 2", resp_mp.text)

    def test_export_dxf_endpoint(self):
        resp = self.client.get("/api/export/dxf")
        self.assertEqual(resp.status_code, 200)

    def test_stereo70_to_wgs84_transform(self):
        # Cluj-Napoca sample Stereo 70 coordinates (Easting, Northing)
        # Note: PROJ EPSG:3844 convention: Easting (X) ~ 392000, Northing (Y) ~ 585000
        easting = 392250.0
        northing = 585200.0
        lon, lat = TRANSFORMER_3844_TO_4326.transform(easting, northing)

        # Cluj is in Romania, approximately Lat 46.7-46.8 N, Lon 23.5-23.7 E
        self.assertAlmostEqual(lat, 46.76, delta=0.2)
        self.assertAlmostEqual(lon, 23.59, delta=0.2)

    def test_closed_loop_report_classes(self):
        t = TestResults(total_discovered=206, passed=197, skipped=9, failed=0, success=True)
        self.assertTrue(t.success)
        self.assertEqual(t.passed, 197)

        q = QGISLiveStatus(connected=True, layers_count=5)
        self.assertTrue(q.connected)
        self.assertEqual(q.layers_count, 5)


if __name__ == "__main__":
    unittest.main()
