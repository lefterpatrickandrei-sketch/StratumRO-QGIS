"""Synthetic assignment regression fixtures; no survey accuracy claims."""
import unittest
from unittest.mock import patch
import geopandas as gpd
from shapely.geometry import box
from engine.evaluation import evaluate_dataset

def frame(ids, geometries):
    return gpd.GeoDataFrame({'id': ids}, geometry=geometries, crs='EPSG:3844')

class TestEvaluationAssignment(unittest.TestCase):
    def assert_conservation(self, result):
        self.assertEqual(result.true_positives + result.false_negatives, result.total_references)
        self.assertEqual(result.true_positives + result.false_positives, result.total_predictions)
        pairs=[r for r in result.building_results if r.matched]
        self.assertEqual(len(pairs), result.true_positives)
        self.assertEqual(len({r.pred_id for r in pairs}),len(pairs))

    def test_below_threshold_is_unmatched_on_both_sides(self):
        result=evaluate_dataset(frame(['P'],[box(8,0,18,10)]),frame(['R'],[box(0,0,10,10)]),min_iou_match=.3)
        self.assertEqual((result.true_positives,result.false_negatives,result.false_positives),(0,1,1))
        self.assert_conservation(result)

    def test_shared_prediction_is_counted_only_once(self):
        result=evaluate_dataset(frame(['P'],[box(0,0,22,10)]),frame(['R1','R2'],[box(0,0,10,10),box(12,0,22,10)]),min_iou_match=.3)
        self.assertEqual((result.true_positives,result.false_negatives),(1,1))
        self.assert_conservation(result)

    def test_threshold_inclusive_and_no_epsilon_relaxation(self):
        pred=frame(['P'],[box(5,0,15,10)])
        refs=frame(['R'],[box(0,0,10,10)])
        result=evaluate_dataset(pred,refs,min_iou_match=1/3)
        self.assertEqual(result.true_positives,1)
        self.assertEqual(result.clean_1_to_1_count,1)
        self.assertEqual(evaluate_dataset(pred,refs,min_iou_match=1/3+5e-10).true_positives,0)

    def test_no_candidate_and_outside_aoi_is_explicit(self):
        result=evaluate_dataset(frame(['P'],[box(100,0,110,10)]),frame(['R'],[box(0,0,10,10)]))
        self.assert_conservation(result)
        self.assertEqual(result.refs_outside_aoi_count,1)
        self.assertIn('FALSE_NEGATIVE_OUTSIDE_AOI',result.building_results[0].error_flags)

    def test_empty_predictions(self):
        result=evaluate_dataset(frame([],[]),frame(['R'],[box(0,0,10,10)]))
        self.assertEqual(result.false_negatives,1)
        self.assert_conservation(result)

    def test_empty_references(self):
        result=evaluate_dataset(frame(['P'],[box(0,0,10,10)]),frame([],[]))
        self.assertEqual(result.false_positives,1)
        self.assert_conservation(result)

    def test_permutation_stability_for_competing_matches(self):
        pred=frame(['P2','P1'],[box(0,0,22,10),box(0,0,22,10)])
        refs=frame(['R2','R1'],[box(12,0,22,10),box(0,0,10,10)])
        def pairs(p,r):
            result=evaluate_dataset(p,r,min_iou_match=.3)
            self.assert_conservation(result)
            return sorted((v.ref_id,v.pred_id) for v in result.building_results if v.matched)
        self.assertEqual(pairs(pred,refs),pairs(pred.iloc[::-1],refs.iloc[::-1]))

    def test_cardinality_precedes_total_iou_with_subthreshold_pair(self):
        # Controlled IoU matrix for the combinatorial assignment boundary.
        # Raw maximum-IoU assignment picks (.9,.49), leaving one valid match;
        # threshold-qualified maximum cardinality must pick (.51,.51).
        refs=frame(['R1','R2'],[box(0,0,10,10),box(1,0,11,10)])
        pred=frame(['P1','P2'],[box(2,0,12,10),box(3,0,13,10)])
        values={(2.,0.):.9,(3.,0.):.51,(2.,1.):.51,(3.,1.):.49}
        with patch('engine.evaluation.compute_iou',side_effect=lambda p,r:values[p.bounds[0],r.bounds[0]]):
            result=evaluate_dataset(pred,refs,min_iou_match=.5)
        self.assertEqual(result.true_positives,2)
        self.assert_conservation(result)

    def test_unassociated_predictions_are_not_labelled_physical_artefacts(self):
        result=evaluate_dataset(frame(['P'],[box(100,0,110,10)]),frame(['R'],[box(0,0,10,10)]))
        self.assertEqual(result.reference_coverage_status,'UNVERIFIED_CONDITIONAL_METRICS')
        unassigned=[r for r in result.building_results if r.ref_id.startswith('NONE')]
        self.assertTrue(unassigned)
        self.assertNotIn('FALSE_POSITIVE_ARTEFACT',unassigned[0].error_flags)

if __name__=='__main__':
    unittest.main()
