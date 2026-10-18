"""The independent audit must not report success when its comparisons differ."""
import contextlib
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

MODULE_PATH=Path(__file__).resolve().parents[2]/"tools/verify_ground_truth_and_metrics.py"
spec=importlib.util.spec_from_file_location("metric_verification_gate",MODULE_PATH)
audit=importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class TestMetricVerificationGate(unittest.TestCase):
    def test_comparison_discrepancies_and_missing_values_fail(self):
        self.assertTrue(audit.metrics_match([("count",2,2),("IoU",.7,.7)]))
        self.assertFalse(audit.metrics_match([("count",2,3)]))
        self.assertFalse(audit.metrics_match([("count",None,3)]))

    def test_hash_mismatch_fails_before_data_loading(self):
        with patch.object(audit.os.path,"exists",return_value=True), patch.object(audit,"compute_md5",return_value="WRONG"), patch.object(audit.gpd,"read_file") as read, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(audit.main(),1)
            read.assert_not_called()

    def test_metric_drift_fails_without_overwriting_ablation(self):
        fresh=SimpleNamespace(**{k:0 for k in (
            "total_references","total_predictions","true_positives","false_positives","false_negatives",
            "clean_1_to_1_count","clean_median_iou","clean_mean_iou","clean_std_iou",
            "clean_median_boundary_rmse_m","clean_mean_boundary_rmse_m","clean_median_hausdorff_m",
            "mean_iou","ancpi_conform_count")})
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"reported.json"
            path.write_text(json.dumps({"total_predictions":9}),encoding="utf-8")
            stream=io.StringIO()
            with patch.object(audit,"REPORTED_SUMMARY_PATH",str(path)), patch.object(audit.os.path,"exists",return_value=True), patch.object(audit,"compute_md5",return_value=audit.EXPECTED_GT_MD5), patch.object(audit.gpd,"read_file",return_value=None), patch.object(audit,"evaluate_dataset",return_value=fresh), patch.object(audit.csv,"DictWriter") as writer, contextlib.redirect_stdout(stream):
                self.assertEqual(audit.main(),1)
                writer.assert_not_called()
            self.assertIn("[FAIL]",stream.getvalue())

    def test_missing_predictions_are_explicitly_partial(self):
        stream=io.StringIO()
        with patch.object(audit.os.path,"exists",side_effect=lambda p:p!=audit.PRED_PATH), patch.object(audit,"compute_md5",return_value=audit.EXPECTED_GT_MD5), contextlib.redirect_stdout(stream):
            self.assertEqual(audit.main(),0)
        self.assertIn("[PARTIAL]",stream.getvalue())
        self.assertNotIn("TOATE CIFRELE SUNT REPRODUSE",stream.getvalue())
