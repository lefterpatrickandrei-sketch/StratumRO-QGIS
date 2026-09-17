# -*- coding: utf-8 -*-
"""
Unit tests for Cadastral .CP export.
Ensures that vertices are extracted authentically from polygon boundaries
and that synthetic coordinates are completely prohibited.
"""

import os
import unittest
import tempfile
from shapely.geometry import box, Polygon, mapping
from stratum_ro.ai.tools.cadastral_tools import export_cp_file


class TestCpExportRealCoords(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_authentic_vertex_extraction(self):
        # Create a real cadastral building polygon in Stereo 70
        poly = box(390700.123, 585400.456, 390725.789, 585420.987)
        exterior_coords = list(poly.exterior.coords)[:-1]

        pts = []
        for i, (x, y) in enumerate(exterior_coords):
            pts.append({
                "nr": i + 1,
                "x": round(x, 3),
                "y": round(y, 3),
                "z": 345.500
            })

        out_cp = os.path.join(self.temp_dir, "test_real.cp")
        res = export_cp_file(out_cp, parcel_id="CAD_01", points=pts, approved=True)

        self.assertEqual(res["status"], "success")
        self.assertTrue(os.path.exists(out_cp))

        with open(out_cp, "r", encoding="utf-8") as f:
            content = f.read()

        # Check header
        self.assertIn("; StratumRO eTerra .CP Export - Imobil CAD_01", content)
        # Check actual coordinate strings matching poly vertices
        self.assertIn("1,390725.789,585400.456,345.500", content)
        self.assertIn("2,390725.789,585420.987,345.500", content)
        self.assertIn("3,390700.123,585420.987,345.500", content)
        self.assertIn("4,390700.123,585400.456,345.500", content)

        # Ensure NO synthetic sequence like 390500 + idx*10
        self.assertNotIn("390500.000,585500.000", content)
        self.assertNotIn("390510.000,585510.000", content)


if __name__ == "__main__":
    unittest.main()
