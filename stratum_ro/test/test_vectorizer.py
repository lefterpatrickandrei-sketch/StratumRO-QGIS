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


if __name__ == "__main__":
    unittest.main()
