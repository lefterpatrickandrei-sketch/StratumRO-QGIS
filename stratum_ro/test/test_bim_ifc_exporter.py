# -*- coding: utf-8 -*-
"""
Unit tests for StratumRO IFC4 Georeferenced BIM Exporter.
"""

import os
import unittest
from shapely.geometry import Polygon
from stratum_ro.domain.bim.ifc_exporter import IfcCadastralExporter


class TestIfcCadastralExporter(unittest.TestCase):

    def setUp(self):
        self.output_ifc = os.path.join("workspace", "output", "test_cadastre_bim.ifc")

    def tearDown(self):
        if os.path.exists(self.output_ifc):
            try:
                os.remove(self.output_ifc)
            except Exception:
                pass

    def test_export_ifc4_structure_and_georeferencing(self):
        # Two rectangular buildings in Stereo 70
        poly1 = Polygon([
            (567000.0, 302000.0),
            (567020.0, 302000.0),
            (567020.0, 302015.0),
            (567000.0, 302015.0),
            (567000.0, 302000.0)
        ])
        poly2 = Polygon([
            (567050.0, 302030.0),
            (567065.0, 302030.0),
            (567065.0, 302040.0),
            (567050.0, 302040.0),
            (567050.0, 302030.0)
        ])
        buildings = [
            {"id": "IEP_001", "geometry": poly1, "height_m": 7.5, "ground_z": 85.0},
            {"id": "IEP_002", "geometry": poly2, "height_m": 4.2, "ground_z": 85.2}
        ]

        exporter = IfcCadastralExporter()
        res_path = exporter.export_buildings_to_ifc4(buildings, self.output_ifc)

        self.assertTrue(os.path.exists(res_path))
        self.assertGreater(os.path.getsize(res_path), 500)

        with open(res_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check ISO STEP & IFC4 structure
        self.assertIn("ISO-10303-21;", content)
        self.assertIn("FILE_SCHEMA(('IFC4'));", content)

        # Check buildingSMART georeferencing
        self.assertIn("IFCPROJECTEDCRS('EPSG:3844'", content)
        self.assertIn("IFCMAPCONVERSION", content)

        # Check extruded elements and proxies
        self.assertIn("IFCEXTRUDEDAREASOLID", content)
        self.assertIn("IFCBUILDINGELEMENTPROXY", content)
        self.assertIn("IEP_001", content)
        self.assertIn("IEP_002", content)


if __name__ == "__main__":
    unittest.main()
