"""Development review: split rejected B5 and test ten additional spatial objects.

Uses saved candidate prompts plus fresh native-tile SAM2 inference. No reference
polygon is loaded. Selection is frozen before inference, all outcomes retained.
"""
from pathlib import Path
import argparse,json,sys
import numpy as np
import geopandas as gpd
import rasterio
from rasterio.windows import from_bounds,bounds as window_bounds
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from shapely.ops import unary_union

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from stratum_ro.roof_body_partition import split_color_roof_bodies
from stratum_ro.roof_simple_geometry import simple_roof_geometry
from stratum_ro.optical_roof_edges import refine_roof_color
from stratum_ro.roof_refinement_prompts import refinement_prompts
from stratum_ro.sam2_engine import SAM2BuildingSegmenter
from stratum_ro.lidar_processor import LidarProcessor


def draw(ax,ortho,old,parts,title,colors=None):
    xmin,ymin,xmax,ymax=unary_union([old]+parts).buffer(4).bounds
    win=from_bounds(xmin,ymin,xmax,ymax,ortho.transform).round_offsets().round_lengths()
    rgb=np.moveaxis(ortho.read([1,2,3],window=win),0,-1);l,b,r,t=window_bounds(win,ortho.transform)
    ax.imshow(rgb,extent=[l,r,b,t])
    if old.geom_type=='Polygon':ax.plot(*old.exterior.xy,color='magenta',lw=1.8)
    for i,p in enumerate(parts):
        if p.geom_type=='Polygon':ax.plot(*p.exterior.xy,color=(colors or ['lime','cyan','orange'])[i%len(colors or ['lime','cyan','orange'])],lw=1.8)
    ax.set_xlim(l,r);ax.set_ylim(b,t);ax.axis('off');ax.set_title(title,fontsize=10)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',required=True)
    args=parser.parse_args();out=Path(args.output_dir);out.mkdir(parents=True,exist_ok=True)
    if (out/'selection.json').exists():raise FileExistsError('Use a fresh run directory')
    original=ROOT/'workspace/reviews/body_recovery_20261013/roof_recovery.gpkg'
    current=gpd.read_file(ROOT/'workspace/reviews/simple_roofs_rectified_20261013/simple_roofs.gpkg',layer='ACOPERISURI_SIMPLE')
    selected=gpd.read_file(original,layer='PROPUNERI_SELECTATE')
    all_candidates=gpd.read_file(original,layer='TOATE_PROPUNERILE')
    raw=gpd.read_file(original,layer='MASTI_OPTICE');rawmap={r.id:r for r in raw.itertuples()}
    mapping=json.loads((ROOT/'workspace/reviews/body_recovery_20261013/final_tiles/results.json').read_text())
    shown=current[current.id.str.startswith('REF_TIER1_021')]
    occupied=list(shown.geometry);samples=[];seen=set(shown.id)
    # Four existing priority objects from other regions, then stable-id review
    # objects. No score-based outcome filtering; excludes spatial duplicates.
    pool=list(selected[~selected.id.isin(seen)].sort_values('id').itertuples())
    pool+=list(all_candidates[~all_candidates.id.isin(set(selected.id))].sort_values('id').itertuples())
    for row in pool:
        geom=row.geometry
        if geom.geom_type!='Polygon' or not geom.is_valid or not 40<=geom.area<=3000:continue
        if row.id in seen:continue
        if any(geom.intersection(p).area/min(geom.area,p.area)>.20 or geom.centroid.distance(p.centroid)<5 for p in occupied):continue
        samples.append(row);seen.add(row.id);occupied.append(geom)
        if len(samples)==10:break
    if len(samples)!=10:raise RuntimeError('Insufficient distinct additional objects')
    selection=[{'test_id':f'T{i+1:02d}','source_id':r.id,'prior_route':r.route,'area_m2':r.geometry.area} for i,r in enumerate(samples)]
    (out/'selection.json').write_text(json.dumps({'selection_before_inference':selection,'policy':'4 unseen priority objects then stable-id review, area40..3000m2, pairwise overlap<=20%, centroid separation>=5m','scope':'Development review, not independent holdout'},indent=2))
    (out/'owner_feedback.json').write_text(json.dumps({'reviewed_sample_count':8,'owner_passed':7,'owner_failed':1,'failed_id':'REF_TIER1_021:B00005','reason':'Owner identifies two buildings; merged body and shape rejected','status_of_additional_10':'PENDING_OWNER_REVIEW','no_generalization_claim':True},indent=2))
    data=LidarProcessor('C:/Users/lefpa/Desktop/date/Z_VladP/Comparatie/LAZ/NorPuncte_St70_S42.laz','C:/Users/lefpa/Desktop/date/Z_VladP/Comparatie/DTM3m/DTM3m.tif').process_multicategory()
    b5=current[current.id=='REF_TIER1_021:B00005'].iloc[0]
    tile=ROOT/'workspace/reviews/prompt_recovery_20261013/full_aoi/cache_tile_Cluj-0-0_halo.tif'
    with rasterio.open(tile) as src:rgb=np.moveaxis(src.read([1,2,3]),0,-1);tr=src.transform
    split=split_color_roof_bodies(b5.geometry,rgb,tr)
    assert len(split)==2,'Rejected B5 still needs separation'
    bodies=[dict(id=b5.id+f':C{i+1}',parent_id=b5.id,owner_identity='TWO_BUILDINGS_CONFIRMED_FOR_PARENT',**body) for i,body in enumerate(split)]
    gpd.GeoDataFrame(bodies,crs=current.crs).to_file(out/'review18.gpkg',layer='B5_DOUA_CORPURI',driver='GPKG')
    current[current.id!=b5.id].to_file(out/'review18.gpkg',layer='CONTURURI_PASTRATE',driver='GPKG')
    current[current.id==b5.id].to_file(out/'review18.gpkg',layer='B5_RESPINS_ANTERIOR',driver='GPKG')
    model=SAM2BuildingSegmenter();cached_tile=None
    records=[];masks=[];report=[]
    for index,row in enumerate(samples,1):
        test_id=f'T{index:02d}';region=row.id.split(':')[0];tile=mapping[region]['tile']
        if cached_tile!=tile:
            with rasterio.open(ROOT/f'workspace/reviews/prompt_recovery_20261013/full_aoi/cache_tile_{tile}_halo.tif') as src:
                rgb=np.moveaxis(src.read([1,2,3]),0,-1);tr=src.transform
            model.set_image(rgb,tr);cached_tile=tile
        parent=rawmap[row.raw_id]
        prompts=refinement_prompts(row.geometry,rgb,tr,data)
        positives=prompts['positive_points'] or [(parent.prompt_x,parent.prompt_y)]
        result=model.segment_candidate(*row.geometry.bounds,mean_h=row.inaltime_med_m,max_h=row.inaltime_max_m,
             lidar_area=row.geometry.area,internal_pts_geo=positives,external_pts_geo=prompts['negative_points'],height_min_threshold=2.)
        optical=result.get('geometry');reason=''
        if optical is None:optical=row.geometry;reason='NO_FRESH_OPTICAL_MASK'
        masks.append({'id':test_id,'source_id':row.id,'geometry':optical,'sam2_score':result.get('sam2_score',0)})
        parts=split_color_roof_bodies(optical,rgb,tr) if optical.geom_type=='Polygon' else [{'geometry':optical,'split_status':'COMPLEX_MASK'}]
        info_rows=[]
        for part_index,part in enumerate(parts,1):
            geom=part['geometry'];method='NEEDS_REVIEW';color='NONE';info={}
            if len(parts)>1:
                method='SUPPORTED_SEPARATE_BODY';color='PARTITION_PRESERVED'
            elif geom.geom_type=='Polygon':
                trimmed,color=refine_roof_color(geom,rgb,tr,data)
                geom,info=simple_roof_geometry(trimmed)
                method=info['method']
            record={'id':test_id+f':C{part_index}','test_id':test_id,'source_id':row.id,'geometry':geom,
                    'sam2_score':result.get('sam2_score',0),'sam2_status':result['status'],
                    'simple_method':method,'color_method':color,'split_status':part['split_status'],
                    'qa_status':'NECESITA_VERIFICARE','owner_verdict':'PENDING',
                    'vertices':len(geom.exterior.coords)-1 if geom.geom_type=='Polygon' else 0,
                    'failure_reason':reason or ('NO_SUPPORTED_SIMPLE_FIT' if method=='NEEDS_REVIEW' else '')}
            records.append(record);info_rows.append({k:v for k,v in record.items() if k!='geometry'})
        report.append({'test_id':test_id,'source_id':row.id,'result_status':'PENDING_VISUAL_REVIEW','parts':info_rows})
        print(test_id,row.id,[r['simple_method'] for r in info_rows],flush=True)
    gpd.GeoDataFrame(records,crs=current.crs).to_file(out/'review18.gpkg',layer='TESTE_10_REZULTATE',driver='GPKG')
    gpd.GeoDataFrame(masks,crs=current.crs).to_file(out/'review18.gpkg',layer='TESTE_10_MASTI_SAM2',driver='GPKG')
    gpd.GeoDataFrame([{'id':f'T{i+1:02d}','source_id':r.id,'geometry':r.geometry} for i,r in enumerate(samples)],crs=current.crs).to_file(out/'review18.gpkg',layer='TESTE_10_ANTERIOR',driver='GPKG')
    (out/'test10_results.json').write_text(json.dumps(report,indent=2))
    with rasterio.open(ROOT/'workspace/output/ortofoto_cluj_usamv_rgb.vrt') as ortho:
        fig,ax=plt.subplots(figsize=(8,8),layout='constrained')
        draw(ax,ortho,b5.geometry,[r['geometry'] for r in bodies],'B00005: mov=respins; verde/cyan=doua corpuri separate')
        fig.savefig(out/'B00005_separat.png',dpi=160);plt.close(fig)
        fig,axes=plt.subplots(5,2,figsize=(13,23),layout='constrained')
        for index,(ax,row) in enumerate(zip(axes.flat,samples),1):
            ident=f'T{index:02d}';parts=[r['geometry'] for r in records if r['test_id']==ident]
            group=[r for r in records if r['test_id']==ident]
            colors=['red' if r['simple_method']=='NEEDS_REVIEW' or r['failure_reason'] else 'lime' for r in group]
            title=ident+' '+row.id+' | '+('REVIZIE NECESARA' if 'red' in colors else 'FORMA SIMPLA - de verificat')
            draw(ax,ortho,row.geometry,parts,title,colors)
            single,sax=plt.subplots(figsize=(8,8),layout='constrained');draw(sax,ortho,row.geometry,parts,title,colors)
            single.savefig(out/(ident+'.png'),dpi=150);plt.close(single)
        fig.suptitle('10 teste — mov: anterior; verde: forma simpla; rosu: esec/revizie; verdict utilizator in asteptare')
        fig.savefig(out/'test10_contact_sheet.png',dpi=140);plt.close(fig)
    check=gpd.read_file(out/'review18.gpkg',layer='TESTE_10_REZULTATE')
    assert check.geometry.is_valid.all() and check.test_id.nunique()==10
    print('Saved ten distinct visual tests, all outcomes retained, no automatic pass',flush=True)


if __name__=='__main__':main()
