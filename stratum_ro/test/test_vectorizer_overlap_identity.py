"""Synthetic regressions for accidental building merges, not survey fixtures."""
import unittest
from shapely.geometry import box
from stratum_ro.vectorizer import CadastralVectorizer

class TestOverlapIdentity(unittest.TestCase):
    def format(self, polygons, **kwargs):
        items=[{'geometry':p,'sam2_score':.9,'mean_h':5.,'max_h':6.} for p in polygons]
        return CadastralVectorizer().format_hybrid_buildings(items,tolerance=0.,eave_offset_m=0.,use_quality_v2=False,**kwargs)

    def test_thin_overlap_does_not_glue_two_buildings(self):
        features=self.format([box(0,0,10,10),box(9.9,0,19.9,10)])
        self.assertEqual(len(features),2)
        self.assertAlmostEqual(features[0]['geometry'].intersection(features[1]['geometry']).area,0.,places=6)
        self.assertGreater(sum(f['geometry'].area for f in features),190.)

    def test_duplicate_masks_are_consolidated(self):
        features=self.format([box(0,0,10,10),box(.1,0,10.1,10)])
        self.assertEqual(len(features),1)

    def test_chain_of_thin_overlaps_keeps_objects_separate(self):
        features=self.format([box(0,0,10,10),box(9.9,0,19.9,10),box(19.8,0,29.8,10)])
        self.assertEqual(len(features),3)

    def test_invalid_merge_policy_fails(self):
        with self.assertRaises(ValueError):
            self.format([box(0,0,10,10)],merge_min_overlap_ratio=1.1)

if __name__=='__main__':
    unittest.main()
