"""A complete tiny job tests orchestration with a deterministic model double.

This is a software regression test, not a real-model benchmark or visual verdict.
"""
import json,sys,tempfile,unittest,contextlib,io
from pathlib import Path
from unittest.mock import patch
import numpy as np
import rasterio
from rasterio.transform import from_origin
from shapely.geometry import box


class RegionalRunnerTests(unittest.TestCase):
    def test_whole_job_preserves_unknown_roof_and_invalid_hole_without_reviewed_anchor(self):
        from tools.run_regional_roofs import main
        class FakeGenerator:
            def __init__(self,*args,**kwargs):self.predictor=None
            def generate(self,rgb):
                mask=np.zeros(rgb.shape[:2],dtype=bool);mask[3:9,3:9]=True
                return [dict(segmentation=mask,predicted_iou=.95,stability_score=.99)]
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);source=root/'source.tif';checkpoint=root/'checkpoint.pt'
            checkpoint.write_bytes(b'unit test model identity only')
            valid=np.ones((8,8),dtype='uint8')*255;valid[2:4,4:6]=0
            with rasterio.open(source,'w',driver='GTiff',width=8,height=8,count=3,
                dtype='uint8',crs='EPSG:3844',transform=from_origin(0,8,1,1)) as dst:
                dst.write(np.full((3,8,8),120,dtype='uint8'));dst.write_mask(valid)
            config=root/'config.json'
            config.write_text(json.dumps(dict(orthophotos=[str(source)],checkpoint=str(checkpoint),
                parameters=dict(resolution_m=1.,core_m=8.,halo_m=2.))),encoding='utf-8')
            output=root/'result'
            with patch.object(sys,'argv',['runner','--config',str(config),'--output',str(output)]),\
                 patch('torch.cuda.is_available',return_value=False),\
                 patch('sam2.build_sam.build_sam2',return_value=object()),\
                 patch('sam2.automatic_mask_generator.SAM2AutomaticMaskGenerator',FakeGenerator),\
                 contextlib.redirect_stdout(io.StringIO()):
                main()
            report=json.loads((output/'report.json').read_text())
            self.assertEqual(report['windows_scanned'],1)
            self.assertEqual(report['routes']['OPTICAL_UNKNOWN_REVIEW'],1)
            self.assertEqual(report['routes']['ROOF_CANDIDATE_REVIEW'],0)
            self.assertEqual(report['incomplete_context'],1)
            import geopandas as gpd
            geometry=gpd.read_file(output/'regional_roofs.gpkg',layer='OPTICAL_UNKNOWN').geometry.iloc[0]
            self.assertAlmostEqual(geometry.intersection(box(4,4,6,6)).area,0)
            self.assertIsNone(report['accuracy'])
            self.assertTrue((output/'final_valid_mask_clips.json').exists())


if __name__=='__main__':unittest.main()
