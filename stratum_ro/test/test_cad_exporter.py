# -*- coding: utf-8 -*-
"""
Unit tests for ANCPI Cadastral DXF Exporter.
"""

import os
import unittest
from shapely.geometry import Polygon
import ezdxf
from stratum_ro.cad_exporter import CadastralDxfExporter


class TestCadastralDxfExporter(unittest.TestCase):

    def setUp(self):
        self.output_dxf = r"workspace\output\test_unit_cadastru.dxf"

    def tearDown(self):
        if os.path.exists(self.output_dxf):
            try:
                os.remove(self.output_dxf)
            except Exception:
                pass

    def test_export_buildings_dxf_structure(self):
        # Create a sample rectangular building in Stereo 70
        poly = Polygon([
            (390500.0, 585800.0),
            (390520.0, 585800.0),
            (390520.0, 585815.0),
            (390500.0, 585815.0),
            (390500.0, 585800.0)
        ])
        buildings = [{
            "id": 1,
            "geometry": poly,
            "area_m2": 300.0
        }]

        exporter = CadastralDxfExporter(dxf_version="R2010")
        res_path = exporter.export_buildings_to_dxf(buildings, self.output_dxf, include_labels=True)

        self.assertTrue(os.path.exists(res_path))
        self.assertGreater(os.path.getsize(res_path), 500)

        # Verify DXF layers and entities
        doc = ezdxf.readfile(res_path)
        layers = [layer.dxf.name for layer in doc.layers]
        self.assertIn("CONSTRUCTII", layers)
        self.assertIn("TEXTE", layers)

        msp = doc.modelspace()
        polylines = msp.query('LWPOLYLINE[layer=="CONSTRUCTII"]')
        self.assertEqual(len(polylines), 1)

        texts = msp.query('TEXT[layer=="TEXTE"]')
        self.assertEqual(len(texts), 1)
        self.assertIn("300.0mp", texts[0].dxf.text)


if __name__ == "__main__":
    unittest.main()
