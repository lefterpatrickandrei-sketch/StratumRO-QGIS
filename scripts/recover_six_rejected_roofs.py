"""Retry the six rejected visual cases with component-local sensor seeds.

Keep failed masks/attempts for audit. Never use GMW/reference geometry or fake
rectangles where roof evidence is absent. Results need fresh human review.
"""
from pathlib import Path
import sys,argparse,json
import geopandas as gpd
import rasterio,numpy as np
from shapely.geometry import box,Point
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from stratum_ro.roof_retry import retry_roof_geometry
from stratum_ro.sam2_engine import SAM2BuildingSegmenter
from stratum_ro.lidar_processor import LidarProcessor
from stratum_ro.optical_roof_edges import refine_roof_color
from stratum_ro.roof_simple_geometry import simple_roof_geometry
from stratum_ro.roof_candidate_routing import vegetation_color_fraction
from stratum_ro.sensor_review import review_candidates
from extend_roof_visual_review import draw
import matplotlib.pyplot as plt


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output-dir',required=True)
    out=Path(p.parse_args().output_dir);out.mkdir(parents=True,exist_ok=True)
    if (out/'retry_report.json').exists():raise FileExistsError('New output directory required')
    old=gpd.read_file(ROOT/'workspace/reviews/review18_20261013/review18.gpkg',layer='TESTE_10_ANTERIOR')
    failed=old[old.id>='T05']
    tiles=[]
    for path in sorted((ROOT/'workspace/reviews/prompt_recovery_20261013/full_aoi').glob('cache_tile_*_halo.tif')):
        with rasterio.open(path) as src:tiles.append((path,box(*src.bounds)))
    data=LidarProcessor('C:/Users/lefpa/Desktop/date/Z_VladP/Comparatie/LAZ/NorPuncte_St70_S42.laz','C:/Users/lefpa/Desktop/date/Z_VladP/Comparatie/DTM3m/DTM3m.tif').process_multicategory()
    model=SAM2BuildingSegmenter();cached=None;attempts=[];records=[];reports=[]
    for row in failed.itertuples():
        options=[(bounds.boundary.distance(row.geometry),str(path),path) for path,bounds in tiles if bounds.covers(row.geometry.buffer(5))]
        if not options:raise RuntimeError('No tile fully covers '+row.id)
        path=max(options)[2]
        if cached!=path:
            with rasterio.open(path) as src:rgb=np.moveaxis(src.read([1,2,3]),0,-1);tr=src.transform
            model.set_image(rgb,tr);cached=path
        retry=retry_roof_geometry(row.geometry,rgb,tr,data,model)
        report={'test_id':row.id,'source_id':row.source_id,'tile':str(path),'prompts':retry['prompts'],'attempts':[]}
        for attempt in retry['attempts']:
            diagnostic={k:v for k,v in attempt.items() if k not in ('geometry','raw_optical')}
            report['attempts'].append(diagnostic)
            if attempt.get('geometry') is not None:
                attempts.append({k:v for k,v in dict(attempt,id=row.id+f":A{attempt['index']}",test_id=row.id,source_id=row.source_id,
                    qa_status='NECESITA_VERIFICARE',owner_verdict='PENDING').items() if k not in ('raw_optical','point')})
            print(row.id,attempt['index'],diagnostic,flush=True)
        kept=[dict(candidate,id=row.id+f":A{candidate['attempt_index']}",test_id=row.id,source_id=row.source_id,
                   qa_status='NECESITA_VERIFICARE',owner_verdict='PENDING') for candidate in retry['candidates']]
        records.extend(kept)
        report['outcome']=retry['status']
        report['retained_ids']=[r['id'] for r in kept];reports.append(report)
    target=out/'retry_six.gpkg'
    if records:gpd.GeoDataFrame(records,crs=old.crs).to_file(target,layer='CORPURI_RECTIFICATE',driver='GPKG')
    if attempts:gpd.GeoDataFrame(attempts,crs=old.crs).to_file(target,layer='TOATE_INCERCARILE',driver='GPKG')
    failed.to_file(target,layer='RESPINSE_ANTERIOR',driver='GPKG')
    (out/'retry_report.json').write_text(json.dumps(reports,indent=2))
    with rasterio.open(ROOT/'workspace/output/ortofoto_cluj_usamv_rgb.vrt') as ortho:
        fig,axes=plt.subplots(3,2,figsize=(13,15),layout='constrained')
        for ax,row,report in zip(axes.flat,failed.itertuples(),reports):
            parts=[r['geometry'] for r in records if r['test_id']==row.id]
            title=row.id+' '+('CORPURI RECTIFICATE - de verificat' if parts else report['outcome'])
            draw(ax,ortho,row.geometry,parts,title)
            single,sax=plt.subplots(figsize=(8,8),layout='constrained');draw(sax,ortho,row.geometry,parts,title)
            single.savefig(out/(row.id+'.png'),dpi=160);plt.close(single)
        fig.suptitle('Mov: contur respins anterior | Verde/cyan: corpuri recuperate | Fara verde: fara contur nou sustinut')
        fig.savefig(out/'six_before_after.png',dpi=140);plt.close(fig)
    print([(r['test_id'],r['outcome'],len(r['retained_ids'])) for r in reports],flush=True)


if __name__=='__main__':main()
