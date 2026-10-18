"""Reproducible simple-shape refinement of a reviewed optical candidate layer.

The input is the RGB/LiDAR-trimmed hypothesis, not cadastral reference geometry.
An older candidate layer supplies orientation only and is retained for comparison.
"""
import argparse
import json
import sys
from pathlib import Path
import geopandas as gpd
import numpy as np
import rasterio
from rasterio.features import rasterize
from rasterio.windows import from_bounds

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from stratum_ro.roof_simple_geometry import simple_roof_geometry
from stratum_ro.sensor_review import review_candidates
from stratum_ro.lidar_processor import LidarProcessor
from stratum_ro.vectorizer import CadastralVectorizer
from stratum_ro.roof_candidate_routing import vegetation_color_fraction


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',required=True)
    parser.add_argument('--input-layer',default='PROPUNERI_CORECTATE')
    parser.add_argument('--prior',required=True)
    parser.add_argument('--prior-layer',default='PROPUNERI_SELECTATE')
    parser.add_argument('--output-dir',required=True)
    parser.add_argument('--laz',required=True)
    parser.add_argument('--dtm',required=True)
    parser.add_argument('--ortho',required=True)
    parser.add_argument('--sam-masks',required=True,help='Fresh SAM2 masks with id/score columns')
    args=parser.parse_args()
    out=Path(args.output_dir);out.mkdir(parents=True,exist_ok=True)
    target=out/'simple_roofs.gpkg'
    if target.exists():raise FileExistsError('Use a new output directory; results are never silently overwritten')
    source=gpd.read_file(args.input,layer=args.input_layer)
    prior=gpd.read_file(args.prior,layer=args.prior_layer)
    if source.crs is None or source.crs.to_epsg()!=3844 or source.crs!=prior.crs:
        raise ValueError('Input layers must both use EPSG:3844 projected metres')
    if source.id.duplicated().any() or prior.id.duplicated().any():raise ValueError('Unique ids required')
    previous={r.id:r.geometry for r in prior.itertuples()}
    sam=gpd.read_file(args.sam_masks)
    scores=dict(zip(sam.id,sam.score))
    data=LidarProcessor(args.laz,args.dtm).process_multicategory()
    vectorizer=CadastralVectorizer()
    records=[];report=[];grounds=[]
    for item in source.to_dict('records'):
        observed=item['geometry'];ident=item['id']
        if ident not in previous:raise ValueError('Missing prior id: '+ident)
        # Explicit audit scope is recorded upstream, not inferred from reference ids.
        preserved=item.get('edge_method')=='PRESERVED_VISUALLY_ACCEPTABLE'
        if preserved:
            result=observed;info={'method':'PRESERVED_PREVIOUS_AUDIT'}
        else:
            # Expanded optical recovery determines the greenhouse's new angle.
            hint=observed if item.get('edge_method')=='RAW_OPTICAL_RECTANGLE' else previous[ident]
            result,info=simple_roof_geometry(observed,orientation_hint=hint)
        historical={k:item[k] for k in list(item) if k.startswith('qa_') or k in
                    ('conf_final','action_code','step_valid_pct','std_acoperis','optical_support','rectangularity','route','route_reason','validare','sam2_score','inaltime_med_m','inaltime_max_m','vegetation_color_fraction')}
        for k in historical:item.pop(k,None)
        ground=result.buffer(-.4,join_style=2)
        ground_method='ASSUMED_EAVE_OFFSET_0_4M'
        if ground.is_empty or not ground.is_valid or ground.geom_type!='Polygon':
            ground=result;ground_method='OFFSET_FAILED_ROOF_RETAINED'
        item.update(geometry=result,area_m2=round(result.area,2),perimeter_m=round(result.length,2),
                    vertices=len(result.exterior.coords)-1,center_x=round(result.centroid.x,2),
                    center_y=round(result.centroid.y,2),area_sol_m2=round(ground.area,2),
                    repair_type='SUPPORTED_SIMPLE_EDGES' if not preserved else 'PRESERVED',
                    clasa_forma=info['method'],simple_method=info['method'],
                    simple_support=info.get('support'),simple_coverage=info.get('coverage'),
                    optical_support=result.intersection(observed).area/result.area,
                    rectangularity=min(1.,result.area/result.minimum_rotated_rectangle.area),
                    edge_status='REVIEW_REQUIRED',route='REVIZUIRE_MANUALA',
                    route_reason='CONTUR_ACOPERIS_SIMPLIFICAT;SOL_ESTIMAT',ground_method=ground_method)
        item['validare']='IPOTEZA_NEVERIFICATA'
        item['semantic_status']='TIP_CONSTRUCTIE_MOSTENIT_NEVERIFICAT'
        item['sam2_score']=float(historical.get('sam2_score',0)) if preserved else float(scores.get(ident,0))
        item['sam2_score_source']='PREVIOUS_MASK' if preserved else 'REFINED_SAM2_MASK'
        lt=data['transform'];points=[(~lt)*(x,y) for x in (result.bounds[0],result.bounds[2]) for y in (result.bounds[1],result.bounds[3])]
        c0=max(0,int(np.floor(min(v[0] for v in points))));c1=min(data['ndsm'].shape[1],int(np.ceil(max(v[0] for v in points))))
        r0=max(0,int(np.floor(min(v[1] for v in points))));r1=min(data['ndsm'].shape[0],int(np.ceil(max(v[1] for v in points))))
        heights=np.array([])
        if c1>c0 and r1>r0:
            mask=rasterize([(result,1)],out_shape=(r1-r0,c1-c0),transform=lt*rasterio.Affine.translation(c0,r0),dtype='uint8').astype(bool)
            heights=data['ndsm'][r0:r1,c0:c1][mask];heights=heights[np.isfinite(heights)]
        item['inaltime_med_m']=float(np.mean(heights)) if len(heights) else None
        item['inaltime_max_m']=float(np.max(heights)) if len(heights) else None
        with rasterio.open(args.ortho) as ortho:
            win=from_bounds(*result.buffer(1).bounds,ortho.transform).round_offsets().round_lengths()
            rgb=np.moveaxis(ortho.read([1,2,3],window=win),0,-1)
            item['vegetation_color_fraction']=vegetation_color_fraction(result,rgb,ortho.window_transform(win))
        quality=vectorizer.quality_gate.compute_composite_confidence(poly=result,
                    sam2_score=float(item.get('sam2_score',0)),ndsm_array=data['ndsm'],transform=data['transform'])
        item.update({k:quality[k] for k in ('conf_final','step_valid_pct','std_acoperis')})
        item['action_code']='REVIZUIRE_MANUALA'
        item=review_candidates([item],data['class_evidence'],data['transform'])[0]
        item['qa_status']='NECESITA_VERIFICARE'
        records.append(item)
        grounds.append({'id':ident,'geometry':ground,'ground_method':ground_method,'status':'ESTIMARE_NECONFIRMATA'})
        report.append({'id':ident,'before_vertices':len(observed.exterior.coords)-1,
                       'after_vertices':item['vertices'],'before_area_m2':observed.area,
                       'after_area_m2':result.area,'fit':info,'historical_attributes':historical})
    result=gpd.GeoDataFrame(records,crs=source.crs)
    assert result.geometry.is_valid.all() and len(result)==len(source)
    result.to_file(target,layer='ACOPERISURI_SIMPLE',driver='GPKG')
    source.to_file(target,layer='IPOTEZE_OPTICE_INTRARE',driver='GPKG')
    prior.to_file(target,layer='CONTURURI_ANTERIOARE',driver='GPKG')
    gpd.GeoDataFrame(grounds,crs=source.crs).to_file(target,layer='SOL_ESTIMAT_NEVERIFICAT',driver='GPKG')
    check=gpd.read_file(target,layer='ACOPERISURI_SIMPLE')
    assert len(check)==len(result) and check.geometry.is_valid.all()
    (out/'rectification_report.json').write_text(json.dumps({'inputs':vars(args),'records':report,
       'scope':'Reviewed development candidates; not full-AOI or independent cadastral validation',
       'readback_valid':True},indent=2,default=str),encoding='utf8')
    print(json.dumps([{'id':r['id'],'vertices':r['after_vertices'],'method':r['fit']['method']} for r in report],indent=2))


if __name__=='__main__':main()
