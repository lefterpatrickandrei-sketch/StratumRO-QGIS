# coding=utf-8
"""Tests for QGIS functionality.


.. note:: This program is free software; you can redistribute it and/or modify
     it under the terms of the GNU General Public License as published by
     the Free Software Foundation; either version 2 of the License, or
     (at your option) any later version.

"""

__author__ = "tim@linfiniti.com"
__date__ = "20/01/2011"
__copyright__ = "Copyright 2012, Australia Indonesia Facility for " "Disaster Reduction"

import os
import unittest

try:
    from qgis.core import QgsProviderRegistry, QgsCoordinateReferenceSystem, QgsRasterLayer
    from .utilities import get_qgis_app
    QGIS_APP = get_qgis_app()
    HAS_QGIS = True
except (ImportError, ModuleNotFoundError):
    HAS_QGIS = False
    QGIS_APP = None


@unittest.skipUnless(HAS_QGIS, "QGIS library is required for this test")
class QGISTest(unittest.TestCase):
    """Test the QGIS Environment"""

    def test_qgis_environment(self):
        """QGIS environment has the expected providers"""

        r = QgsProviderRegistry.instance()
        self.assertIn("gdal", r.providerList())
        self.assertIn("ogr", r.providerList())

    def test_projection(self):
        """Test that QGIS can resolve a CRS from an authority code."""
        crs = QgsCoordinateReferenceSystem("EPSG:4326")
        self.assertTrue(crs.isValid())
        self.assertEqual(crs.authid(), "EPSG:4326")

        # test that a loaded raster layer has a valid CRS
        path = os.path.join(os.path.dirname(__file__), "tenbytenraster.asc")
        layer = QgsRasterLayer(path, "TestRaster")
        self.assertTrue(layer.isValid())
        self.assertTrue(layer.crs().isValid())

    def test_stereo70_3844(self):
        """Test that QGIS can resolve modern ANCPI Stereo 70 (EPSG:3844)."""
        crs = QgsCoordinateReferenceSystem("EPSG:3844")
        self.assertTrue(crs.isValid())
        self.assertEqual(crs.authid(), "EPSG:3844")

    def test_stereo70_31700(self):
        """Test that QGIS can resolve legacy Stereo 70 (EPSG:31700)."""
        crs = QgsCoordinateReferenceSystem("EPSG:31700")
        self.assertTrue(crs.isValid())
        self.assertEqual(crs.authid(), "EPSG:31700")

    def test_vertical_marea_neagra(self):
        """Test that QGIS can resolve vertical CRS Marea Neagră 1975 (EPSG:5781)."""
        crs = QgsCoordinateReferenceSystem("EPSG:5781")
        self.assertTrue(crs.isValid())
        self.assertEqual(crs.authid(), "EPSG:5781")


if __name__ == "__main__":
    unittest.main()
