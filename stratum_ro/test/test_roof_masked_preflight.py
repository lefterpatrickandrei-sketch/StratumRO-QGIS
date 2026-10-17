import unittest
import numpy as np
import rasterio
from stratum_ro.test import test_evaluation_preflight as fixtures
from stratum_ro.roof_masked_preflight import validate_masked_selection


class MaskedPreflightTests(unittest.TestCase):
    def setUp(self):
        self.f=fixtures.TestEvaluationPreflight();self.f.setUp();self.addCleanup(self.f.doCleanups)
        with rasterio.open(self.f.root/'rgb.tif','r+') as dst:
            data=dst.read();data[:,35,35]=0;dst.write(data)

    def check(self,enabled=True):
        return validate_masked_selection(self.f.manifest,manifest_dir=self.f.root,tile_dir=self.f.root,
            policies={'NEW1':'MASKED_CONTEXT_REVIEW'} if enabled else {})

    def test_masked_review_is_explicit_and_warned(self):
        self.assertFalse(self.check(False)['ready'])
        result=self.check();self.assertTrue(result['ready']);self.assertTrue(result['cases'][0]['warnings'])

    def test_invalid_anchor_is_never_accepted(self):
        self.f.write_raster(hole=True);self.assertFalse(self.check()['ready'])

    def test_missing_review_not_bypassed(self):
        self.f.manifest['cases'][0]['selection_review']['point_on_roof']=False
        self.assertFalse(self.check()['ready'])

    def test_global_schema_errors_not_erased(self):
        self.f.manifest['crs']='EPSG:4326';self.assertFalse(self.check()['ready'])
