# -*- coding: utf-8 -*-
"""
Unit tests for 3D Volumetric Extrusion, RANSAC Roof Fitting, and CityJSON.
"""

import os
import json
import unittest
import numpy as np
from shapely.geometry import Polygon
from stratum_ro.volumetric_3d import Volumetric3DBuilder


class TestVolumetric3D(unittest.TestCase):

    def setUp(self):
        self.builder = Volumetric3DBuilder(default_ground_z=350.0)
        self.test_poly = Polygon([
            (390500.0, 585800.0),
            (390520.0, 585800.0),
            (390520.0, 585815.0),
            (390500.0, 585815.0),
            (390500.0, 585800.0)
        ])
        self.output_cityjson = r"workspace\output\test_model_3d.city.json"

    def tearDown(self):
        if os.path.exists(self.output_cityjson):
            try:
                os.remove(self.output_cityjson)
            except Exception:
                pass

    def test_extrude_lod1_solid(self):
        solid = self.builder.extrude_lod1_solid(self.test_poly, height_m=6.5, ground_z=350.0)
        self.assertIsNotNone(solid)
        self.assertTrue(solid.has_z)
        self.assertEqual(solid.geom_type, "MultiPolygon")

        # 1 floor + 1 roof + 4 walls = 6 faces
        self.assertEqual(len(solid.geoms), 6)

        # Verify coordinates of floor vs roof
        floor_face = solid.geoms[0]
        roof_face = solid.geoms[1]
        self.assertAlmostEqual(list(floor_face.exterior.coords)[0][2], 350.0)
        self.assertAlmostEqual(list(roof_face.exterior.coords)[0][2], 356.5)

    def test_estimate_lod2_roof_planes(self):
        # Generate horizontal points
        x = np.linspace(390500, 390520, 10)
        y = np.linspace(585800, 585815, 10)
        xx, yy = np.meshgrid(x, y)
        zz = np.full_like(xx, 356.5)
        pts = np.column_stack([xx.ravel(), yy.ravel(), zz.ravel()])

        res = self.builder.estimate_lod2_roof_planes(pts)
        self.assertEqual(res["tip_acoperis"], "TERASA")
        self.assertLess(res["panta_grade"], 5.0)

    def test_export_cityjson(self):
        bldg_data = [{
            "cod_cladire": "BLDG_0001",
            "geometry": self.test_poly,
            "h_cornisa_m": 6.5,
            "z_sol_m": 350.0,
            "regim_inaltime": "P+1E"
        }]

        res_path = self.builder.export_cityjson(bldg_data, self.output_cityjson, epsg_code=3844)
        self.assertTrue(os.path.exists(res_path))

        with open(res_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertEqual(data["type"], "CityJSON")
        self.assertEqual(data["version"], "1.1")
        self.assertIn("BLDG_0001", data["CityObjects"])
        self.assertEqual(data["CityObjects"]["BLDG_0001"]["attributes"]["measuredHeight"], 6.5)
        self.assertGreater(len(data["vertices"]), 0)

    def test_canonical_import_and_forwarder_equivalence(self):
        """Verifies that the canonical domain builder and legacy forwarder produce identical outputs."""
        from stratum_ro.domain.city_3d.builder import Volumetric3DBuilder as CanonicalBuilder
        from stratum_ro.domain.city_3d import Volumetric3DBuilder as PackageBuilder
        from stratum_ro.volumetric_3d import Volumetric3DBuilder as ForwarderBuilder
        from stratum_ro.volumetric_3d import _extract_polygons as forwarder_extract
        from stratum_ro.domain.city_3d.builder import _extract_polygons as canonical_extract

        # Verify class object identity
        self.assertIs(ForwarderBuilder, CanonicalBuilder)
        self.assertIs(PackageBuilder, CanonicalBuilder)
        self.assertIs(forwarder_extract, canonical_extract)

        # Verify behavioral equivalence on LoD1 solid
        can_b = CanonicalBuilder(default_ground_z=350.0)
        fwd_b = ForwarderBuilder(default_ground_z=350.0)

        solid_can = can_b.extrude_lod1_solid(self.test_poly, height_m=6.5, ground_z=350.0)
        solid_fwd = fwd_b.extrude_lod1_solid(self.test_poly, height_m=6.5, ground_z=350.0)

        self.assertTrue(solid_can.equals_exact(solid_fwd, 1e-9))

    def test_degenerate_and_edge_case_handling(self):
        """Verifies safe handling of empty polygons, sub-threshold areas, and minimal points."""
        # Empty polygon
        empty_poly = Polygon()
        self.assertIsNone(self.builder.extrude_lod1_solid(empty_poly, height_m=5.0))
        self.assertIsNone(self.builder.create_lod1_roof_surface(empty_poly, height_m=5.0))

        # Sub-threshold area (< 2.0 m^2)
        tiny_poly = Polygon([(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0), (0.0, 0.0)])
        self.assertIsNone(self.builder.extrude_lod1_solid(tiny_poly, height_m=5.0))

        # Degenerate roof points (< 6 points returns fallback TERASA_LOD1)
        few_pts = np.array([[390500.0, 585800.0, 350.0], [390510.0, 585800.0, 350.0]])
        res = self.builder.estimate_lod2_roof_planes(few_pts)
        self.assertEqual(res["tip_acoperis"], "TERASA_LOD1")
        self.assertEqual(res["panta_grade"], 0.0)

    def test_create_lod1_roof_surface(self):
        """Verifies creation of 2.5D horizontal roof polygon."""
        roof = self.builder.create_lod1_roof_surface(self.test_poly, height_m=7.0, ground_z=340.0)
        self.assertIsNotNone(roof)
        self.assertTrue(roof.has_z)
        self.assertAlmostEqual(list(roof.exterior.coords)[0][2], 347.0)


if __name__ == "__main__":
    unittest.main()

