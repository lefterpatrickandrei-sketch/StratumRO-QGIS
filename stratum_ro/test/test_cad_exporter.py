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

    def test_export_polygon_with_interior_hole(self):
        """Verifică calculul corect al ariei nete (375 mp) pentru clădiri cu curte interioară / gaură (P1.4 DoD)."""
        # Exterior 20m x 20m = 400 mp, Gaură interioară 5m x 5m = 25 mp -> Arie netă = 375 mp
        exterior_coords = [(390500.0, 585800.0), (390520.0, 585800.0), (390520.0, 585820.0), (390500.0, 585820.0), (390500.0, 585800.0)]
        hole_coords = [(390505.0, 585805.0), (390510.0, 585805.0), (390510.0, 585810.0), (390505.0, 585810.0), (390505.0, 585805.0)]
        poly_with_hole = Polygon(shell=exterior_coords, holes=[hole_coords])

        self.assertAlmostEqual(poly_with_hole.area, 375.0, places=2)

        # 1. Verificare DXF (etichete și tabel PAD)
        exporter = CadastralDxfExporter(dxf_version="R2010")
        cat_dict = {
            "CLADIRI_PRINCIPALE": [{"id": 1, "geometry": poly_with_hole}]
        }
        res_dxf = exporter.export_multicategory_to_dxf(
            cat_dict,
            self.output_dxf,
            include_labels=True,
            topolt_mode=True,
            draw_pad_table=True
        )
        self.assertTrue(os.path.exists(res_dxf))
        doc = ezdxf.readfile(res_dxf)
        msp = doc.modelspace()

        # Textul C1 trebuie să specifice exact aria netă de 375.0mp (nu 400mp)
        all_texts = [t.dxf.text for t in msp.query('TEXT')]
        self.assertTrue(any("375" in t for t in all_texts), f"Aria netă 375 mp trebuie să apară în textele DXF: {all_texts}")
        self.assertFalse(any("400.0mp" in t for t in all_texts), "Aria brută 400mp nu trebuie să apară ca arie a clădirii")

        # În DXF trebuie să existe 2 polilinii pe 1CC: conturul exterior + conturul curții interioare
        polylines_1cc = msp.query('LWPOLYLINE[layer=="1CC"]')
        self.assertEqual(len(polylines_1cc), 2, "Trebuie desenate atât conturul exterior cât și curtea interioară")

        # 2. Verificare fișier .cp
        output_cp = r"workspace\output\test_hole_interchange.cp"
        res_cp = exporter.export_to_cp_file(cat_dict, output_cp)
        self.assertTrue(os.path.exists(res_cp))
        with open(res_cp, "r", encoding="utf-8") as f:
            cp_content = f.read()

        self.assertIn("[CONSTRUCTIE_1CC_C1]", cp_content)
        self.assertIn("GOL_INTERIOR", cp_content)
        self.assertIn("1CC_GOL", cp_content)

        if os.path.exists(output_cp):
            try:
                os.remove(output_cp)
            except Exception:
                pass


if __name__ == "__main__":
    unittest.main()

