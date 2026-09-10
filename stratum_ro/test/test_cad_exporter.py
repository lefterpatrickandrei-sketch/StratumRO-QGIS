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

    def test_export_topolt_dxf_structure(self):
        # Create a sample rectangular building in Stereo 70
        poly = Polygon([
            (390500.0, 585800.0),
            (390520.0, 585800.0),
            (390520.0, 585815.0),
            (390500.0, 585815.0),
            (390500.0, 585800.0)
        ])
        poly_anx = Polygon([
            (390530.0, 585800.0),
            (390540.0, 585800.0),
            (390540.0, 585808.0),
            (390530.0, 585808.0),
            (390530.0, 585800.0)
        ])
        cat_dict = {
            "CLADIRI_PRINCIPALE": [{"id": 1, "geometry": poly, "area_m2": 300.0}],
            "ANEXE_GOSPODARESTI": [{"id": 2, "geometry": poly_anx, "area_m2": 80.0}]
        }

        exporter = CadastralDxfExporter(dxf_version="R2010")
        res_path = exporter.export_multicategory_to_dxf(
            cat_dict,
            self.output_dxf,
            include_labels=True,
            topolt_mode=True,
            draw_pad_table=True
        )

        self.assertTrue(os.path.exists(res_path))
        doc = ezdxf.readfile(res_path)
        layers = [layer.dxf.name for layer in doc.layers]
        self.assertIn("1CC", layers)
        self.assertIn("2CC", layers)
        self.assertIn("VARFURI", layers)
        self.assertIn("NUMERE_PCT", layers)
        self.assertIn("TABEL_PAD", layers)

        msp = doc.modelspace()
        pts = msp.query('POINT[layer=="VARFURI"]')
        self.assertEqual(len(pts), 8)  # 4 for main building + 4 for outbuilding

        num_texts = msp.query('TEXT[layer=="NUMERE_PCT"]')
        self.assertEqual(len(num_texts), 8)

        table_lines = msp.query('LINE[layer=="TABEL_PAD"]')
        self.assertGreater(len(table_lines), 5)

    def test_export_to_cp_file(self):
        output_cp = r"workspace\output\test_interchange.cp"
        poly = Polygon([
            (390500.0, 585800.0),
            (390520.0, 585800.0),
            (390520.0, 585815.0),
            (390500.0, 585815.0),
            (390500.0, 585800.0)
        ])
        cat_dict = {
            "CLADIRI_PRINCIPALE": [{"id": 1, "geometry": poly, "area_m2": 300.0}]
        }

        exporter = CadastralDxfExporter()
        res_cp = exporter.export_to_cp_file(cat_dict, output_cp)

        self.assertTrue(os.path.exists(res_cp))
        with open(res_cp, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("[CONSTRUCTIE_1CC_C1]", content)
        self.assertIn("390500.000,585800.000,0.000,1CC", content)

        if os.path.exists(output_cp):
            try:
                os.remove(output_cp)
            except Exception:
                pass


if __name__ == "__main__":
    unittest.main()
