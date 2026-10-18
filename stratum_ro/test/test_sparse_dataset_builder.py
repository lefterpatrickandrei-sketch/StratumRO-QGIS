# -*- coding: utf-8 -*-
import unittest
from pathlib import Path
import numpy as np
import geopandas as gpd
from shapely.geometry import box, Polygon
import rasterio
from rasterio.transform import from_origin

from stratum_ro.sparse_dataset_builder import (
    SparseDatasetBuilder, IGNORE_INDEX, ROOF_LABEL, NEGATIVE_LABEL
)

ROOT = Path(__file__).resolve().parent.parent.parent


class TestSparseDatasetBuilder(unittest.TestCase):
    def setUp(self):
        self.builder = SparseDatasetBuilder(crs="EPSG:3844")

    def test_rasterize_sparse_patch_values(self):
        """Verifies that unannotated pixels are 255, explicit negatives are 0, and roofs are 1."""
        patch_bounds = (0.0, 0.0, 100.0, 100.0)
        transform = from_origin(0.0, 100.0, 1.0, 1.0)
        out_shape = (100, 100)

        pos_geom = box(20.0, 20.0, 40.0, 40.0)
        neg_geom = box(60.0, 60.0, 80.0, 80.0)

        mask = self.builder.rasterize_sparse_patch(
            patch_bounds=patch_bounds,
            transform=transform,
            out_shape=out_shape,
            positive_geoms=[pos_geom],
            negative_geoms=[neg_geom],
            ignore_index=IGNORE_INDEX
        )

        self.assertEqual(mask.shape, out_shape)
        # Check unannotated pixel (0, 0 in geo -> row 99, col 0)
        self.assertEqual(mask[90, 10], IGNORE_INDEX)
        # Check roof pixel (center of pos_geom: x=30, y=30 -> row 70, col 30)
        self.assertEqual(mask[70, 30], ROOF_LABEL)
        # Check negative pixel (center of neg_geom: x=70, y=70 -> row 30, col 70)
        self.assertEqual(mask[30, 70], NEGATIVE_LABEL)

    def test_spatial_split_guarantees_zero_leakage_and_buffer(self):
        """create_spatial_split enforces strict spatial separation >= buffer_m with zero overlap."""
        # 4 buildings in North, 2 in South
        pos_geoms = [
            box(10.0, 100.0, 20.0, 110.0),
            box(30.0, 120.0, 45.0, 135.0),
            box(10.0, 20.0, 20.0, 30.0),
            box(30.0, 15.0, 40.0, 25.0),
        ]
        pos_gdf = gpd.GeoDataFrame([{"id": f"P{i}", "geometry": g} for i, g in enumerate(pos_geoms)], crs="EPSG:3844")
        neg_gdf = gpd.GeoDataFrame([{"id": "N0", "geometry": box(15.0, 140.0, 25.0, 150.0)}], crs="EPSG:3844")

        # Split at Y = 60 with buffer = 20m
        split = self.builder.create_spatial_split(pos_gdf, neg_gdf, split_axis="y", split_coord=60.0, buffer_m=20.0)
        self.assertTrue(split["zero_leakage_verified"])
        self.assertGreaterEqual(split["measured_min_distance_m"], 20.0)
        self.assertEqual(len(split["train_pos"]), 2)
        self.assertEqual(len(split["val_pos"]), 2)
        self.assertEqual(len(split["train_neg"]), 1)
        self.assertEqual(split["excluded_pos_count"], 0)

    def test_load_cluj_annotations_integrity(self):
        """Verifies loading real audited annotations from repository geopackages."""
        r18 = ROOT / "workspace/reviews/review18_20261013/review18.gpkg"
        r6 = ROOT / "workspace/reviews/retry_six_release_20261013/retry_six.gpkg"
        l3 = ROOT / "workspace/reviews/lot3_20261013/lot3_results.gpkg"

        if not r18.exists() or not r6.exists() or not l3.exists():
            self.skipTest("Audited geopackages not present in workspace")

        pos_gdf, neg_gdf = self.builder.load_cluj_annotations(r18, r6, l3)
        self.assertGreater(len(pos_gdf), 15)
        self.assertGreater(len(neg_gdf), 2)
        self.assertIn("NEG_T12_C1_PAVED_COURTYARD", neg_gdf["id"].tolist())
        self.assertTrue(all(pos_gdf.geometry.is_valid))
        self.assertTrue(all(neg_gdf.geometry.is_valid))


if __name__ == "__main__":
    unittest.main()
