# -*- coding: utf-8 -*-
"""
stratum_ro/test/test_pug_harvester_and_qgis.py

Unit tests for universal PUG data harvester, UAT resolution, and QGIS project XML generation.
Verifies compliance with Order MDLPA nr. 904/2023, CATUC 2026, and valid XML entity escaping.
"""

import unittest
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
import geopandas as gpd
from shapely.geometry import Polygon

from stratum_ro.pug_harvester import (
    PugDataHarvester,
    PugQgisProjectBuilder,
    normalize_string,
    REGIONAL_PRESETS,
)

ROOT = Path(__file__).resolve().parent.parent.parent


class TestPugHarvesterAndQgis(unittest.TestCase):

    def setUp(self):
        self.harvester = PugDataHarvester()

    def test_normalize_string(self):
        """Verify diacritics and casing normalization."""
        self.assertEqual(normalize_string("Cluj-Napoca"), "cluj napoca")
        self.assertEqual(normalize_string("FLOREŞTI"), "floresti")
        self.assertEqual(normalize_string("Feleacu"), "feleacu")
        self.assertEqual(normalize_string("București"), "bucuresti")

    def test_resolve_uat_by_siruta(self):
        """Verify resolving single UAT by exact SIRUTA code."""
        gdf = self.harvester.resolve_uats(["54975"])
        self.assertEqual(len(gdf), 1)
        self.assertEqual(gdf.iloc[0]["natCode"], "54975")

    def test_resolve_uat_by_name(self):
        """Verify resolving UAT by Romanian name."""
        gdf = self.harvester.resolve_uats(["Cluj-Napoca"])
        self.assertEqual(len(gdf), 1)
        self.assertEqual(gdf.iloc[0]["natCode"], "54975")

    def test_resolve_regional_preset(self):
        """Verify regional preset resolution (ZMC has 6 UATs)."""
        gdf = self.harvester.resolve_uats(["cluj_zmc"])
        self.assertEqual(len(gdf), 6)
        expected_codes = set(REGIONAL_PRESETS["cluj_zmc"]["codes"])
        self.assertEqual(set(gdf["natCode"]), expected_codes)

    def test_qgis_project_xml_escaping(self):
        """Verify that QGIS project XML escapes ampersands and special characters cleanly."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            gpkg_path = tmp_path / "test.gpkg"
            qgs_path = tmp_path / "test.qgs"

            # Create dummy layer in GPKG
            poly = Polygon([(500000, 500000), (500100, 500000), (500100, 500100), (500000, 500000)])
            df = gpd.GeoDataFrame([{"name": "Zona A & B (Test)", "geometry": poly}], crs="EPSG:3844")
            df.to_file(str(gpkg_path), layer="ZFExistenta", driver="GPKG")

            # Build project
            title = "StratumRO & PUG <Test Project> 2026"
            PugQgisProjectBuilder.build_qgis_project(gpkg_path, qgs_path, project_title=title)

            self.assertTrue(qgs_path.exists())

            # Parse with standard XML parser - must succeed without parse error
            tree = ET.parse(str(qgs_path))
            root = tree.getroot()
            self.assertEqual(root.tag, "qgis")


if __name__ == "__main__":
    unittest.main()
