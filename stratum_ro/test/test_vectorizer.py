# -*- coding: utf-8 -*-
"""
Unit tests for Cadastral Vectorizer and 90-degree Orthogonalization.
"""

import os
import unittest
import numpy as np
import rasterio
from shapely.geometry import Polygon
from stratum_ro.vectorizer import CadastralVectorizer


class TestCadastralVectorizer(unittest.TestCase):

    def setUp(self):
        self.vectorizer = CadastralVectorizer(crs="EPSG:3844")

    def test_orthogonalize_slanted_rectangle(self):
        # Slightly slanted rectangle
        slanted_coords = [
            (10.0, 10.0),
            (20.2, 10.1),
            (20.1, 25.0),
            (9.9, 24.9),
            (10.0, 10.0)
        ]
        poly = Polygon(slanted_coords)
        ortho_poly = self.vectorizer.orthogonalize_polygon(poly, tolerance=0.5)

        self.assertTrue(ortho_poly.is_valid)
        self.assertGreater(ortho_poly.area, 50.0)

    def test_vectorize_synthetic_ndsm(self):
        # 50x50 synthetic nDSM with a 10x10 building in center
        ndsm = np.zeros((50, 50), dtype=np.float32)
        ndsm[15:25, 15:25] = 6.5  # 6.5m high building
        transform = rasterio.transform.from_origin(390000.0, 585000.0, 1.0, 1.0)

        buildings = self.vectorizer.vectorize_ndsm_buildings(
            ndsm_array=ndsm,
            transform=transform,
            min_height=2.5,
            min_area_m2=20.0,
            orthogonalize=True
        )

        self.assertEqual(len(buildings), 1)
        self.assertAlmostEqual(buildings[0]["area_m2"], 100.0, delta=10.0)
        self.assertEqual(buildings[0]["crs"], "EPSG:3844")

    def test_resolve_multipart_touching_blocks(self):
        """Verifică unificarea blocurilor alipite (evită spargerea în corpuri incomplete)."""
        from shapely.geometry import box, MultiPolygon
        from stratum_ro.geometry_utils import resolve_multipart_geometry
        b1 = box(0, 0, 10, 20)   # 200 mp
        b2 = box(10, 0, 20, 10)  # 100 mp
        mp = MultiPolygon([b1, b2])
        res = resolve_multipart_geometry(mp)
        self.assertEqual(res.geom_type, "Polygon")
        self.assertAlmostEqual(res.area, 300.0, places=1)

    def test_resolve_multipart_bridged_wings(self):
        """Verifică construirea punții structurale între aripi de clădire separate de rost/coridor."""
        from shapely.geometry import box, MultiPolygon
        from stratum_ro.geometry_utils import resolve_multipart_geometry
        b1 = box(0, 0, 10, 20)   # 200 mp
        b2 = box(11, 0, 21, 20)  # 200 mp, spațiu de 1.0m
        mp = MultiPolygon([b1, b2])
        res = resolve_multipart_geometry(mp, bridge_max_distance_m=1.5)
        self.assertEqual(res.geom_type, "Polygon")
        self.assertGreaterEqual(res.area, 400.0)

    def test_resolve_multipart_micro_noise_filtered(self):
        """Verifică eliminarea zgomotului parazit (< 8 mp) fără afectarea corpului principal."""
        from shapely.geometry import box, MultiPolygon
        from stratum_ro.geometry_utils import resolve_multipart_geometry
        b_main = box(0, 0, 20, 20)     # 400 mp
        b_noise = box(25, 25, 26, 27)  # 2 mp
        mp = MultiPolygon([b_main, b_noise])
        res = resolve_multipart_geometry(mp)
        self.assertEqual(res.geom_type, "Polygon")
        self.assertAlmostEqual(res.area, 400.0, places=1)


if __name__ == "__main__":
    unittest.main()

