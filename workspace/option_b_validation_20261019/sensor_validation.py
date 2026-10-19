"""Re-read local RGB/validity/nDSM through the existing StratumRO reader, no inference."""
from pathlib import Path
import sys,json,hashlib
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
import geopandas as gpd
from stratum_ro.api.service import PlatformService
from stratum_ro.regional_refinement import scene_evidence

def main():
    out=Path(__file__).parent
    config=json.loads((ROOT/'workspace/option_b_refinement_20261018/config_replay.json').read_text())
    engine=PlatformService(ROOT).create_regional_roof_refiner([ROOT/p for p in config['orthophotos']],height_path=ROOT/config['height'])
    oldpath=ROOT/'workspace/reviews/option_b_simple_variations_20261018_v2/simple_variations.gpkg'
    newpath=ROOT/'workspace/reviews/option_b_repair_20261019_v2/simple_variations.gpkg'
    old=gpd.read_file(oldpath,layer='B_SIMPLE').set_index('candidate_id');new=gpd.read_file(newpath,layer='B_SIMPLE').set_index('candidate_id')
    records={}
    for index,ident in enumerate(old.index):
        a=old.loc[ident].geometry;b=new.loc[ident].geometry
        scene=engine.observe(a.union(b))
        record={}
        for tag,g in [('old',a),('new',b)]:
            record[tag]=scene_evidence(g,scene['rgb'],scene['valid'],scene['transform'],scene['height'])
        record['read_sources']=scene['sources'];record['read_bounds']=scene['bounds'];records[ident]=record
        if index%30==0:print(index+1,'/216',flush=True)
    result=dict(role='Fresh observations, not independent ground truth; nDSM is experimental context, not class 6 or roof identity',
        resolution_m=engine.config.resolution_m,records=records,
        summary={tag:dict(incomplete_rgb=sum(r[tag].get('rgb_valid_fraction',0)<.995 for r in records.values()),
            touches_nodata=sum(r[tag].get('touches_nodata',False) for r in records.values()),
            height_missing_or_partial=sum(r[tag].get('height_valid_fraction',0)<.995 for r in records.values())) for tag in ['old','new']},
        source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [oldpath,newpath]})
    (out/'sensor_validation.json').write_text(json.dumps(result,indent=2,default=str),encoding='utf-8')
    print(json.dumps(result['summary']))

if __name__=='__main__':main()
