import unittest
from unittest.mock import patch,MagicMock
import numpy as np
from rasterio.transform import from_origin
from shapely.geometry import box,Point
from stratum_ro.roof_body_recovery import recover_roof_bodies


class PartitionRecoveryIntegrationTests(unittest.TestCase):
    def run_scene(self,simple_edges):
        p=box(0,0,10,10);tr=from_origin(0,10,.1,.1)
        rgb=np.full((100,100,3),120,dtype=np.uint8);rgb[:50]=[180,50,50]
        evidence={'building':np.ones((100,100)),'observed':np.ones((100,100)),'vegetation':np.zeros((100,100))}
        data={'ndsm':np.full((100,100),5.),'transform':tr,'class_evidence':evidence}
        proposal={'geometry':p,'slice':(slice(0,100),slice(0,100)),'mask':np.ones((100,100),dtype=bool),'source':'TEST','area_m2':100.}
        segmenter=MagicMock();segmenter.segment_candidate.return_value={'geometry':p,'status':'HYBRID','sam2_score':.95}
        vectorizer=MagicMock()
        vectorizer.format_hybrid_buildings.side_effect=lambda results,**kwargs:[{'geometry':r['geometry'],'geometry_sol':r['geometry'],'sam2_score':.95} for r in results]
        vectorizer.quality_gate.compute_composite_confidence.return_value={'conf_final':.9,'action_code':'REVIEW','step_valid_pct':100.,'std_acoperis':0.}
        with patch('stratum_ro.roof_body_recovery.color_body_proposals',return_value=[proposal]),patch('stratum_ro.roof_body_recovery.building_proposals',return_value=[]),patch('stratum_ro.roof_body_recovery.CadastralVectorizer',return_value=vectorizer):
            return recover_roof_bodies(data,rgb,tr,segmenter,simple_edges=simple_edges)

    def test_opt_in_keeps_parent_and_two_review_bodies(self):
        result=self.run_scene(True)
        self.assertEqual(len(result['raw']),1)
        self.assertAlmostEqual(result['raw'][0]['geometry'].area,100.)
        self.assertEqual(len(result['candidates']),2)
        first,second=result['candidates']
        self.assertLess(first['geometry'].intersection(second['geometry']).area,1e-6)
        self.assertEqual(first['raw_id'],second['raw_id'])
        for child in result['candidates']:
            self.assertEqual(child['body_count'],2)
            self.assertEqual(child['route'],'REVIZUIRE_COMPLEXA')
            self.assertNotIn('_body_mask',child)

    def test_default_does_not_activate_spectral_partition(self):
        result=self.run_scene(False)
        self.assertEqual(len(result['candidates']),1)
        self.assertEqual(result['candidates'][0]['body_count'],1)

    def test_lidar_child_retries_with_own_point_and_fresh_optical_lineage(self):
        parent=box(10,10,80,80);child=box(20,20,40,40);tr=from_origin(0,100,1,1)
        rgb=np.full((100,100,3),120,dtype=np.uint8)
        data={'ndsm':np.full((100,100),5.),'transform':tr,'class_evidence':{
              'observed':np.ones((100,100)),'building':np.ones((100,100)),'vegetation':np.zeros((100,100))}}
        proposal={'geometry':parent,'slice':(slice(20,90),slice(10,80)),
                  'mask':np.ones((70,70),dtype=bool),'source':'TEST_PARENT','area_m2':parent.area,
                  'positive_point_geo':Point(70,70)}
        model=MagicMock();model.segment_candidate.side_effect=[
            {'geometry':None,'status':'LIDAR_DIRECT','sam2_score':.2},
            {'geometry':child,'status':'CONFIRMAT_HIBRID','sam2_score':.91}]
        vectorizer=MagicMock();vectorizer.format_hybrid_buildings.return_value=[{
            'geometry':child,'geometry_sol':child,'sam2_score':.2}]
        vectorizer.quality_gate.compute_composite_confidence.return_value={
            'conf_final':.9,'action_code':'REVIEW','step_valid_pct':100.,'std_acoperis':0.}
        with patch('stratum_ro.roof_body_recovery.color_body_proposals',return_value=[proposal]),patch('stratum_ro.roof_body_recovery.building_proposals',return_value=[]),patch('stratum_ro.roof_body_recovery.CadastralVectorizer',return_value=vectorizer):
            result=recover_roof_bodies(data,rgb,tr,model,simple_edges=True)
        candidate=result['candidates'][0]
        point=model.segment_candidate.call_args_list[1].kwargs['internal_pts_geo'][0]
        self.assertTrue(child.covers(Point(point)));self.assertNotEqual(point,(70,70))
        self.assertTrue(candidate['retry_succeeded']);self.assertTrue(candidate['inherited_prompt_outside'])
        self.assertEqual(candidate['sam2_score'],.91)
        self.assertEqual(candidate['sam2_score_scope'],'LOCAL_CHILD_MASK')
        self.assertNotEqual(candidate['retry_raw_id'],candidate['raw_id'])
        self.assertEqual(candidate['action_code'],'REVIZUIRE_MANUALA')
        self.assertNotIn('_routing_optical',candidate)

    def test_retry_keeps_both_recovered_height_bodies(self):
        parent=box(10,10,80,80);child=box(20,20,40,40);tr=from_origin(0,100,1,1)
        rgb=np.full((100,100,3),120,dtype=np.uint8)
        data={'ndsm':np.full((100,100),5.),'transform':tr,'class_evidence':{
            'observed':np.ones((100,100)),'building':np.ones((100,100)),'vegetation':np.zeros((100,100))}}
        proposal={'geometry':parent,'slice':(slice(20,90),slice(10,80)),
            'mask':np.ones((70,70),dtype=bool),'source':'TEST_PARENT','area_m2':parent.area,'positive_point_geo':Point(70,70)}
        model=MagicMock();model.segment_candidate.return_value={'geometry':None,'status':'LIDAR_DIRECT','sam2_score':.2}
        v=MagicMock();v.format_hybrid_buildings.return_value=[{'geometry':child,'geometry_sol':child,'sam2_score':.2}]
        v.quality_gate.compute_composite_confidence.return_value={'conf_final':.9,'action_code':'REVIEW','step_valid_pct':100.,'std_acoperis':0.}
        bodies=[box(20,20,30,40),box(30,20,40,40)]
        candidates=[{'geometry':g,'sam2_score':.91,'simple_method':'SUPPORTED_RECTANGLE','simple_support':1.,'simple_coverage':1.,
                     'color_method':'LOCAL_HEIGHT','seed_x':g.centroid.x,'seed_y':g.centroid.y,'attempt_index':i} for i,g in enumerate(bodies,1)]
        retry={'status':'RECTIFIED_HYPOTHESES_PENDING_REVIEW','candidates':candidates,
               'attempts':[{'index':i,'raw_optical':g,'status':'CONFIRMAT_HIBRID','sam2_score':.91,'point':g.centroid.coords[0]} for i,g in enumerate(bodies,1)]}
        with patch('stratum_ro.roof_body_recovery.color_body_proposals',return_value=[proposal]),patch('stratum_ro.roof_body_recovery.building_proposals',return_value=[]),patch('stratum_ro.roof_body_recovery.CadastralVectorizer',return_value=v),patch('stratum_ro.roof_body_recovery.retry_roof_geometry',return_value=retry):
            result=recover_roof_bodies(data,rgb,tr,model,simple_edges=True)
        self.assertEqual(len(result['candidates']),2)
        self.assertEqual(len(result['raw']),3)
        self.assertEqual({f['body_index'] for f in result['candidates']},{1,2})
        self.assertTrue(all(f['body_count']==2 for f in result['candidates']))
        self.assertEqual(len({f['retry_raw_id'] for f in result['candidates']}),2)
        self.assertLess(result['candidates'][0]['geometry'].intersection(result['candidates'][1]['geometry']).area,1e-6)
        self.assertTrue(all(f['route']=='REVIZUIRE_COMPLEXA' for f in result['candidates']))


if __name__=='__main__':unittest.main()
