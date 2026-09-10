# -*- coding: utf-8 -*-
"""
Unit tests for StratumRO Quantitative Evaluation Engine.
Verifies IoU, Hausdorff, Boundary RMSE, Shape metrics, and Compliance Tiers.
"""

import unittest
from shapely.geometry import Polygon, box
from engine.evaluation import (
    compute_iou,
    compute_hausdorff,
    compute_boundary_rmse,
    compute_shape_metrics,
    evaluate_dataset,
)
import geopandas as gpd


class TestEvaluationEngine(unittest.TestCase):

    def setUp(self):
        # Referință: Dreptunghi de 10m x 20m (200 mp)
        self.ref_poly = Polygon([
            (390800.0, 585200.0),
            (390810.0, 585200.0),
            (390810.0, 585220.0),
            (390800.0, 585220.0),
            (390800.0, 585200.0)
        ])

    def test_identity_metrics(self):
        """Test pentru geometrii identice (eroare zero)."""
        iou = compute_iou(self.ref_poly, self.ref_poly)
        hausdorff = compute_hausdorff(self.ref_poly, self.ref_poly, densify=0.1)
        rmse = compute_boundary_rmse(self.ref_poly, self.ref_poly, sample_step_m=0.2)
        shape_stats = compute_shape_metrics(self.ref_poly, self.ref_poly)

        self.assertAlmostEqual(iou, 1.0, places=4)
        self.assertAlmostEqual(hausdorff, 0.0, places=3)
        self.assertAlmostEqual(rmse, 0.0, places=3)
        self.assertAlmostEqual(shape_stats["centroid_disp_m"], 0.0, places=3)
        self.assertAlmostEqual(shape_stats["area_error_m2"], 0.0, places=2)

    def test_controlled_translation_ancpi_conform(self):
        """Test pentru o translație mică de 5 cm (trebuie să fie CONFORM_ANCPI)."""
        from shapely.affinity import translate
        pred_poly = translate(self.ref_poly, xoff=0.05, yoff=0.0)

        iou = compute_iou(pred_poly, self.ref_poly)
        hausdorff = compute_hausdorff(pred_poly, self.ref_poly, densify=0.1)
        rmse = compute_boundary_rmse(pred_poly, self.ref_poly, sample_step_m=0.2)

        self.assertGreater(iou, 0.98)
        self.assertAlmostEqual(hausdorff, 0.05, delta=0.01)
        self.assertLessEqual(rmse, 0.06)

    def test_controlled_translation_pug_acceptable(self):
        """Test pentru o translație de 20 cm (depășește ANCPI 10cm, dar este ACCEPTABIL_PUG <= 30cm)."""
        from shapely.affinity import translate
        pred_poly = translate(self.ref_poly, xoff=0.20, yoff=0.0)

        rmse = compute_boundary_rmse(pred_poly, self.ref_poly, sample_step_m=0.2)
        self.assertGreater(rmse, 0.10)
        self.assertLessEqual(rmse, 0.25)

    def test_l_shape_fixture_evaluation(self):
        """Test de evaluare pe fixture-ul real case_01_L_shape."""
        gdf_gt = gpd.read_file("data/fixtures/case_01_L_shape.geojson")
        summary = evaluate_dataset(gdf_gt, gdf_gt)

        self.assertEqual(summary.total_references, 1)
        self.assertEqual(summary.true_positives, 1)
        self.assertEqual(summary.ancpi_conform_count, 1)
        self.assertAlmostEqual(summary.mean_iou, 1.0, places=3)
        self.assertAlmostEqual(summary.mean_boundary_rmse_m, 0.0, places=3)

    def test_evaluation_identical_datasets_sanity(self):
        """Test de sanitate critic: ref == ref -> IoU=1.0, RMSE=0.0, HD=0.0, F1=1.0."""
        gdf_gt = gpd.read_file("data/fixtures/case_02_calcan_split.geojson")
        summary = evaluate_dataset(gdf_gt, gdf_gt)

        self.assertEqual(summary.total_references, len(gdf_gt))
        self.assertEqual(summary.false_positives, 0)
        self.assertEqual(summary.false_negatives, 0)
        self.assertAlmostEqual(summary.f1_score, 1.0, places=3)
        self.assertAlmostEqual(summary.mean_iou, 1.0, places=3)
        self.assertAlmostEqual(summary.mean_boundary_rmse_m, 0.0, places=3)
        self.assertAlmostEqual(summary.mean_hausdorff_m, 0.0, places=3)
        self.assertEqual(summary.clean_1_to_1_count, len(gdf_gt))

    def test_evaluation_disjoint_datasets_negative(self):
        """Test negativ: două seturi complet disjuncte spațial -> F1=0, fără erori/crash."""
        from shapely.affinity import translate
        gdf_ref = gpd.read_file("data/fixtures/case_01_L_shape.geojson")
        gdf_pred = gdf_ref.copy()
        # Translatare la 50 km distanță
        gdf_pred.geometry = gdf_pred.geometry.apply(lambda g: translate(g, xoff=50000.0, yoff=50000.0))

        summary = evaluate_dataset(gdf_pred, gdf_ref)
        self.assertEqual(summary.true_positives, 0)
        self.assertEqual(summary.f1_score, 0.0)
        self.assertEqual(summary.precision, 0.0)
        self.assertEqual(summary.recall, 0.0)
        self.assertEqual(summary.clean_1_to_1_count, 0)
        self.assertEqual(summary.false_positives, len(gdf_pred))

    def test_ci95_calculation(self):
        """Verifică formula intervalului de încredere 95% cu distribuția Student-t."""
        from engine.evaluation import compute_ci95
        # Măsurători cu medie = 10.0
        data = [9.0, 10.0, 11.0]
        ci = compute_ci95(data)
        # mean=10, std=1, n=3 -> sem = 1/sqrt(3) = 0.577, t(0.975, df=2) = 4.303 -> margin = 2.484
        self.assertAlmostEqual(ci[0], 10.0 - 2.484, places=2)
        self.assertAlmostEqual(ci[1], 10.0 + 2.484, places=2)

    def test_common_aoi_detection(self):
        """Verifică separarea clădirilor din interiorul vs exteriorul ariei de procesare (AOI)."""
        from shapely.affinity import translate
        gdf_ref = gpd.read_file("data/fixtures/case_02_calcan_split.geojson")
        gdf_pred = gdf_ref.iloc[:1].copy()  # Doar prima clădire e procesată

        summary = evaluate_dataset(gdf_pred, gdf_ref)
        self.assertEqual(summary.total_references, 2)
        self.assertEqual(summary.total_predictions, 1)
        self.assertEqual(summary.true_positives, 1)
        self.assertGreater(summary.common_aoi_area_ha, 0.0)

    def test_wgs84_to_stereo70_helmert_regression(self):
        """
        Test de regresie geodezică pentru transformarea WGS84 (EPSG:4326) -> Stereo 70 (EPSG:3844).
        Verifică concordanța dintre default pyproj și transformarea oficială 7-parametri Helmert (EPSG:15995 OGP-Rom).
        """
        import pyproj
        lon, lat = 23.570, 46.758  # Cluj USAMV
        t_def = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:3844", always_xy=True)
        x_def, y_def = t_def.transform(lon, lat)

        # Pipeline explicit EPSG:15995
        pipe_inv = (
            "+proj=pipeline +step +proj=unitconvert +xy_in=deg +xy_out=rad +step +proj=push +v_3 "
            "+step +proj=cart +ellps=WGS84 +step +inv +proj=helmert +x=2.329 +y=-147.042 +z=-92.08 "
            "+rx=0.309 +ry=-0.325 +rz=-0.497 +s=5.69 +convention=coordinate_frame +step +inv +proj=cart "
            "+ellps=krass +step +proj=pop +v_3 +step +proj=sterea +lat_0=46 +lon_0=25 +k=0.99975 +x_0=500000 +y_0=500000 +ellps=krass"
        )
        t_inv = pyproj.Transformer.from_pipeline(pipe_inv)
        x_inv, y_inv = t_inv.transform(lon, lat)

        # Verificăm că cele două produc rezultate identice (< 0.001 m)
        self.assertAlmostEqual(x_def, x_inv, places=3)
        self.assertAlmostEqual(y_def, y_inv, places=3)

        # Valori de referință fixate pentru Cluj USAMV
        self.assertAlmostEqual(x_def, 390896.060, places=2)
        self.assertAlmostEqual(y_def, 585256.749, places=2)


if __name__ == "__main__":
    unittest.main()

