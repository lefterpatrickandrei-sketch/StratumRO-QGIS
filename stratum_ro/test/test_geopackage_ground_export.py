import os
import tempfile
import unittest
from shapely.geometry import Polygon
import geopandas as gpd

from stratum_ro.vectorizer import CadastralVectorizer


class TestGeopackageGroundExport(unittest.TestCase):
    def setUp(self):
        self.vectorizer = CadastralVectorizer(crs="EPSG:3844")
        self.poly1 = Polygon([(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)])
        self.poly1_sol = Polygon([(0.4, 0.4), (9.6, 0.4), (9.6, 9.6), (0.4, 9.6), (0.4, 0.4)])

        self.poly2 = Polygon([(20, 20), (30, 20), (30, 30), (20, 30), (20, 20)])
        self.poly2_sol = Polygon([(20.4, 20.4), (29.6, 20.4), (29.6, 29.6), (20.4, 29.6), (20.4, 20.4)])

    def test_explicit_ground_wins_and_metadata_retained(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            gpkg = os.path.join(tmpdir, "test.gpkg")
            feat1 = {"id": 1, "geometry": self.poly1, "geometry_sol": self.poly1_sol}
            explicit_sol = [{
                "id": 1,
                "geometry": self.poly1_sol,
                "review_status": "MANUAL_VERIFIED",
                "surveyor": "TOPO_ING"
            }]
            cats = {
                "CLADIRI_CLEAN": [feat1],
                "CLADIRI_SOL_ANCPI": explicit_sol
            }
            self.vectorizer.save_multicategory_geopackage(cats, gpkg)
            gdf_sol = gpd.read_file(gpkg, layer="CLADIRI_SOL_ANCPI")
            self.assertEqual(len(gdf_sol), 1)
            self.assertEqual(gdf_sol.iloc[0]["review_status"], "MANUAL_VERIFIED")
            self.assertEqual(gdf_sol.iloc[0]["surveyor"], "TOPO_ING")

    def test_clean_hibrid_aliases_do_not_duplicate_auto_ground(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            gpkg = os.path.join(tmpdir, "test.gpkg")
            feat1 = {"id": 1, "geometry": self.poly1, "geometry_sol": self.poly1_sol}
            feat2 = {"id": 2, "geometry": self.poly2, "geometry_sol": self.poly2_sol}

            # CLEAN and HIBRID point to same two IDs with geometry_sol
            cats = {
                "CLADIRI_CLEAN": [dict(feat1), dict(feat2)],
                "CLADIRI_HIBRID": [dict(feat1), dict(feat2)]
            }
            self.vectorizer.save_multicategory_geopackage(cats, gpkg)
            gdf_sol = gpd.read_file(gpkg, layer="CLADIRI_SOL_ANCPI")
            self.assertEqual(len(gdf_sol), 2)
            self.assertCountEqual(gdf_sol["id"].tolist(), [1, 2])

    def test_repeated_export_remains_idempotent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            gpkg = os.path.join(tmpdir, "test.gpkg")
            feat1 = {"id": 1, "geometry": self.poly1, "geometry_sol": self.poly1_sol}
            cats = {"CLADIRI_CLEAN": [feat1]}

            self.vectorizer.save_multicategory_geopackage(cats, gpkg)
            self.vectorizer.save_multicategory_geopackage(cats, gpkg)

            gdf_clean = gpd.read_file(gpkg, layer="CLADIRI_CLEAN")
            gdf_sol = gpd.read_file(gpkg, layer="CLADIRI_SOL_ANCPI")
            self.assertEqual(len(gdf_clean), 1)
            self.assertEqual(len(gdf_sol), 1)

    def test_explicit_empty_suppresses_auto_ground(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            gpkg = os.path.join(tmpdir, "test.gpkg")
            feat1 = {"id": 1, "geometry": self.poly1, "geometry_sol": self.poly1_sol}
            cats = {
                "CLADIRI_CLEAN": [feat1],
                "CLADIRI_SOL_ANCPI": []
            }
            self.vectorizer.save_multicategory_geopackage(cats, gpkg)
            layers = gpd.list_layers(gpkg)["name"].tolist()
            self.assertNotIn("CLADIRI_SOL_ANCPI", layers)

    def test_conflicting_auto_ground_ids_fail(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            gpkg = os.path.join(tmpdir, "test.gpkg")
            feat1_a = {"id": 1, "geometry": self.poly1, "geometry_sol": self.poly1_sol}
            feat1_b = {"id": 1, "geometry": self.poly1, "geometry_sol": self.poly2_sol}
            cats = {
                "LAYER_A": [feat1_a],
                "LAYER_B": [feat1_b]
            }
            with self.assertRaises(ValueError):
                self.vectorizer.save_multicategory_geopackage(cats, gpkg)
            self.assertFalse(os.path.exists(gpkg))

    def test_explicit_empty_clears_existing_ground_and_preserves_other_layers(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            gpkg = os.path.join(tmpdir, "test.gpkg")
            feat = {"id": 1, "geometry": self.poly1, "geometry_sol": self.poly1_sol}
            self.vectorizer.save_multicategory_geopackage({"KEEP": [{"id": 9, "geometry": self.poly2}], "CLEAN": [feat]}, gpkg)
            self.vectorizer.save_multicategory_geopackage({"CLEAN": [feat], "CLADIRI_SOL_ANCPI": []}, gpkg)
            self.assertEqual(len(gpd.read_file(gpkg, layer="CLADIRI_SOL_ANCPI")), 0)
            self.assertEqual(gpd.read_file(gpkg, layer="KEEP").iloc[0]["id"], 9)

    def test_caller_features_remain_unmodified(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            gpkg = os.path.join(tmpdir, "test.gpkg")
            feat1 = {"id": 1, "geometry": self.poly1, "geometry_sol": self.poly1_sol, "meta": "keep"}
            cats = {"CLADIRI_CLEAN": [feat1]}
            self.vectorizer.save_multicategory_geopackage(cats, gpkg)
            # Ensure feat1 still has geometry_sol and original attributes
            self.assertIn("geometry_sol", feat1)
            self.assertEqual(feat1["meta"], "keep")


if __name__ == "__main__":
    unittest.main()
