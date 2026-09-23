# -*- coding: utf-8 -*-
"""
Unit tests for stratum_ro/core/geodesy package.
"""

import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import unittest
from stratum_ro.contracts.geodesy import ICRSManager, ITransformer, AxisOrder
from stratum_ro.core.geodesy import CoreCRSManager, CoreTransformer


class TestCoreGeodesy(unittest.TestCase):

    def setUp(self):
        self.crs_mgr = CoreCRSManager()

    def test_crs_manager_protocol(self):
        self.assertIsInstance(self.crs_mgr, ICRSManager)

    def test_stereo70_metadata(self):
        meta = self.crs_mgr.get_metadata("EPSG:3844")
        self.assertEqual(meta.epsg_code, 3844)
        self.assertEqual(meta.ellipsoid, "Krasovsky 1940")
        self.assertEqual(meta.axis_order, AxisOrder.NORTHING_EASTING)
        self.assertTrue(self.crs_mgr.validate_crs("3844"))
        self.assertTrue(self.crs_mgr.validate_crs("EPSG:3844"))

    def test_transformer_protocol_and_cluj_conversion(self):
        tr = CoreTransformer("EPSG:4326", "EPSG:3844")
        self.assertIsInstance(tr, ITransformer)
        
        # Cluj-Napoca: Longitude ~23.585, Latitude ~46.766
        # In always_xy=True mode: x=lon, y=lat
        lon, lat = 23.585, 46.766
        tx, ty, tz = tr.transform_point(lon, lat)
        
        # Stereo 70 bounds for Cluj: Easting ~391000..395000, Northing ~586000..590000
        self.assertGreater(tx, 380000.0)
        self.assertLess(tx, 410000.0)
        self.assertGreater(ty, 570000.0)
        self.assertLess(ty, 600000.0)
        self.assertEqual(tz, 0.0)

    def test_transform_coordinates_sequence(self):
        tr = CoreTransformer("EPSG:3844", "EPSG:4326")
        coords_s70 = [(391456.0, 587123.0), (391460.0, 587130.0)]
        coords_wgs = tr.transform_coordinates(coords_s70)
        self.assertEqual(len(coords_wgs), 2)
        # Check longitude ~23.58, latitude ~46.76
        for lon, lat in coords_wgs:
            self.assertAlmostEqual(lon, 23.58, places=1)
            self.assertAlmostEqual(lat, 46.76, places=1)


if __name__ == "__main__":
    unittest.main()
