# -*- coding: utf-8 -*-
"""Non-destructive regression tests for CRS labels and LiDAR spatial extents.

All vector and point-cloud inputs are generated under temporary directories;
no project datasets are read or modified.
"""

import json
import tempfile
import unittest
from pathlib import Path

from stratum_ro.ai.data_profiler import DataProfiler
from stratum_ro.lidar_processor import LidarProcessor
from stratum_ro.lidar_quality_gate import LidarQualityGate


def _feature_collection(coordinates, crs_name=None):
    document = {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "properties": {},
            "geometry": {"type": "Polygon", "coordinates": [coordinates]},
        }],
    }
    if crs_name is not None:
        document["crs"] = {
            "type": "name",
            "properties": {"name": crs_name},
        }
    return document


class TestCRSMetadataHandling(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.profiler = DataProfiler()

    def _profile(self, filename, coordinates, crs_name):
        path = Path(self.temp_dir.name) / filename
        path.write_text(
            json.dumps(_feature_collection(coordinates, crs_name)), encoding="utf-8"
        )
        return self.profiler.profile_vector_file(str(path))

    def test_epsg_3844_tagged_metric_coordinates_pass_spatial_domain(self):
        report = self._profile(
            "stereo70.geojson",
            [[390000, 585000], [390010, 585000], [390010, 585010],
             [390000, 585010], [390000, 585000]],
            "urn:ogc:def:crs:EPSG::3844",
        )
        self.assertIn("L2", report.checks)
        self.assertTrue(report.checks["L2"]["stereo70_conforming"])
        self.assertEqual(report.bbox, (390000.0, 585000.0, 390010.0, 585010.0))

    def test_wgs84_coordinates_mislabeled_as_3844_are_flagged_by_domain(self):
        report = self._profile(
            "wrongly_tagged.geojson",
            [[24.9, 46.7], [24.91, 46.7], [24.91, 46.71],
             [24.9, 46.71], [24.9, 46.7]],
            "urn:ogc:def:crs:EPSG::3844",
        )
        self.assertNotIn("L2", report.checks)
        self.assertTrue(any("geographic" in issue for issue in report.issues))

    def test_missing_crs_metadata_is_inferred_from_metric_domain(self):
        report = self._profile(
            "missing_crs.geojson",
            [[390000, 585000], [390010, 585000], [390010, 585010],
             [390000, 585010], [390000, 585000]],
            None,
        )
        # The current profiler labels coordinates from their domain even without
        # embedded metadata; this records that behavior without claiming it
        # independently verified the source CRS.
        self.assertEqual(report.crs_detected, "EPSG:3844")
        self.assertIn("L2", report.checks)

    def test_wgs84_like_coordinates_are_flagged_even_when_tagged_wgs84(self):
        report = self._profile(
            "wgs84.geojson",
            [[24.9, 46.7], [24.91, 46.7], [24.91, 46.71],
             [24.9, 46.71], [24.9, 46.7]],
            "urn:ogc:def:crs:EPSG::4326",
        )
        self.assertNotIn("L2", report.checks)
        self.assertTrue(any("geographic" in issue for issue in report.issues))


class TestLidarDeclaredAndActualExtents(unittest.TestCase):
    """Exercise header-vs-point bounds and boundary relations on temporary LAS."""

    @classmethod
    def setUpClass(cls):
        try:
            import laspy
            from shapely.geometry import box
            from shapely.geometry import Polygon
        except ImportError as exc:
            raise unittest.SkipTest(f"LAS extent fixture dependencies unavailable: {exc}")
        cls.laspy = laspy
        cls.box = staticmethod(box)
        cls.Polygon = Polygon

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)

    def _write_cloud(self, name, xy):
        header = self.laspy.LasHeader(point_format=3, version="1.2")
        header.scales = [0.01, 0.01, 0.01]
        from pyproj import CRS
        header.add_crs(CRS.from_epsg(3844))
        cloud = self.laspy.LasData(header)
        cloud.x = [p[0] for p in xy]
        cloud.y = [p[1] for p in xy]
        cloud.z = [100.0] * len(xy)
        cloud.classification = [6] * len(xy)
        path = Path(self.temp_dir.name) / name
        cloud.write(path)
        return path

    def _assert_extent_relation(self, name, points, expected_relation, aoi=None):
        aoi = aoi or self.box(0, 0, 10, 10)
        path = self._write_cloud(name, points)
        processor = LidarProcessor(str(path))
        before = path.read_bytes()
        result = processor.validate_extent_against_aoi(aoi)
        self.assertEqual(result["relation"], expected_relation)
        self.assertEqual(result["crs"], "EPSG:3844")
        self.assertEqual(path.read_bytes(), before, "validation must be read-only")
        return processor

    def test_declared_and_actual_extents_contained_in_aoi(self):
        self._assert_extent_relation("contained.las", [(2, 2), (8, 8)], "contained")

    def test_declared_and_actual_extents_partially_overlap_aoi(self):
        self._assert_extent_relation("partial.las", [(8, 4), (12, 6)], "partial_overlap")

    def test_declared_and_actual_extents_disjoint_from_aoi(self):
        self._assert_extent_relation("disjoint.las", [(12, 2), (15, 5)], "disjoint")

    def test_declared_and_actual_extents_touch_aoi_edge(self):
        self._assert_extent_relation("edge.las", [(10, 2), (12, 8)], "edge_touching")

    def test_invalid_aoi_geometries_are_rejected(self):
        processor = self._assert_extent_relation(
            "valid-for-invalid-aoi.las", [(2, 2), (8, 8)], "contained"
        )
        bowtie = self.Polygon([(0, 0), (10, 10), (0, 10), (10, 0), (0, 0)])
        for aoi in (bowtie, self.Polygon(), self.box(0, 0, 1, 1).centroid):
            with self.subTest(aoi=aoi.geom_type):
                with self.assertRaises(ValueError):
                    processor.validate_extent_against_aoi(aoi)

    def test_missing_and_mismatched_las_crs_metadata_are_rejected(self):
        path = self._write_cloud("crs-check.las", [(2, 2), (8, 8)])
        processor = LidarProcessor(str(path))
        with self.laspy.open(path) as reader:
            cloud = reader.read()
        cloud.header.vlrs.clear()
        cloud.write(path)
        with self.assertRaisesRegex(ValueError, "missing"):
            processor.validate_extent_against_aoi(self.box(0, 0, 10, 10))

        with self.laspy.open(path) as reader:
            cloud = reader.read()
        from pyproj import CRS
        cloud.header.add_crs(CRS.from_epsg(4326))
        cloud.write(path)
        with self.assertRaisesRegex(ValueError, "must be EPSG:3844"):
            processor.validate_extent_against_aoi(self.box(0, 0, 10, 10))

    def test_coordinate_magnitude_does_not_substitute_for_crs_metadata(self):
        header = self.laspy.LasHeader(point_format=3, version="1.2")
        cloud = self.laspy.LasData(header)
        cloud.x, cloud.y, cloud.z = [390000, 390010], [585000, 585010], [100, 100]
        cloud.classification = [6, 6]
        path = Path(self.temp_dir.name) / "untagged-metric.las"
        cloud.write(path)
        with self.assertRaisesRegex(ValueError, "missing"):
            LidarProcessor(str(path)).validate_extent_against_aoi(
                self.box(389000, 584000, 391000, 586000)
            )

    def test_aoi_crs_must_be_epsg_3844(self):
        path = self._write_cloud("aoi-crs.las", [(2, 2), (8, 8)])
        processor = LidarProcessor(str(path))
        with self.assertRaisesRegex(ValueError, "AOI CRS must be EPSG:3844"):
            processor.validate_extent_against_aoi(self.box(0, 0, 10, 10), "EPSG:4326")
        with self.assertRaisesRegex(ValueError, "missing or invalid"):
            processor.validate_extent_against_aoi(self.box(0, 0, 10, 10), None)


if __name__ == "__main__":
    unittest.main()
