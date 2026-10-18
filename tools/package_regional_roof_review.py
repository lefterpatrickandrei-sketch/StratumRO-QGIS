"""Keep the first full scan immutable; add an explicit final NoData boundary guard."""
from pathlib import Path
import sys,json,time,sqlite3,shutil
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
import geopandas as gpd
from stratum_ro.regional_roofs import OrthoMosaic,sha256_file,route_summary
from stratum_ro.regional_review import clip_to_valid_mosaic


def main():
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--output-name',default='masked_review')
    parser.add_argument('--revise-height-only-routing',action='store_true');args=parser.parse_args()
    if Path(args.output_name).name!=args.output_name:raise ValueError('One output directory name required')
    base=ROOT/'workspace/reviews/regional_roofs_20261017';scan=base/'scan_v1'
    report=json.loads((scan/'report.json').read_text());request=json.loads((base/'config.json').read_text())
    out=base/args.output_name;out.mkdir(exist_ok=False)
    mosaic=OrthoMosaic([ROOT/p for p in request['orthophotos']])
    source=scan/'regional_roofs.gpkg';target=out/'regional_review.gpkg'
    changes=[];counts={};invalid=[];start=time.perf_counter()
    names=['ROOF_CANDIDATES','OPTICAL_UNKNOWN','LIKELY_VEGETATION']
    frames={name:gpd.read_file(source,layer=name) for name in names}
    transitions=[]
    if args.revise_height_only_routing:
        import pandas as pd
        combined=gpd.GeoDataFrame(pd.concat(list(frames.values()),ignore_index=True),crs=3844)
        combined['initial_route']=combined['route']
        combined['route']=[route_summary(r.vegetation_fraction,r.class6_fraction) for _,r in combined.iterrows()]
        transitions=[dict(candidate_id=r.candidate_id,initial=r.initial_route,revised=r.route)
            for _,r in combined[combined.route!=combined.initial_route].iterrows()]
        frames={name:combined[combined.route==route].copy() for name,route in zip(names,
            ['ROOF_CANDIDATE_REVIEW','OPTICAL_UNKNOWN_REVIEW','LIKELY_VEGETATION_REVIEW'])}
    for layer in names+['RAW_SELECTED_OBSERVATIONS','SCAN_COVERAGE']:
        frame=frames[layer] if layer in frames else gpd.read_file(source,layer=layer)
        if layer in ['ROOF_CANDIDATES','OPTICAL_UNKNOWN','LIKELY_VEGETATION']:
            for index,row in frame.iterrows():
                geometry=row.geometry
                if row['touches_nodata']:
                    clipped,removed=clip_to_valid_mosaic(geometry,mosaic)
                    if not clipped.equals(geometry):
                        if clipped.is_empty:
                            raise ValueError('Whole candidate lost valid coverage; inspect '+row['candidate_id'])
                        frame.at[index,'geometry']=clipped
                        frame.at[index,'geometry_status']='INCOMPLETE_CONTEXT_REVIEW'
                        changes.append(dict(candidate_id=row['candidate_id'],removed_m2=removed,
                            before_area_m2=geometry.area,after_area_m2=clipped.area))
            frame['vertices']=[sum(len(r.coords)-1 for p in (list(g.geoms) if g.geom_type=='MultiPolygon' else [g])
                for r in [p.exterior,*p.interiors]) for g in frame.geometry]
            invalid.extend(frame.loc[~frame.geometry.is_valid,'candidate_id'].tolist())
        counts[layer]=len(frame);frame.to_file(target,layer=layer,driver='GPKG')
    with sqlite3.connect(target) as connection:connection.execute('PRAGMA wal_checkpoint(FULL)')
    audit=dict(scope='VALID_PIXEL_CLIP_NOT_SEMANTIC_VALIDATION',source=str(source),
        source_sha256=sha256_file(source),input_fingerprint=report['fingerprint'],
        product_code_sha256=sha256_file(ROOT/'stratum_ro/regional_review.py'),
        tool_code_sha256=sha256_file(Path(__file__)),counts=counts,changed=changes,
        removed_total_m2=sum(r['removed_m2'] for r in changes),invalid_candidates=invalid,
        elapsed_s=time.perf_counter()-start,owner_verdict_changed=False,
        routing_policy='CLASS6_CONTEXT_OR_UNKNOWN_NO_HEIGHT_ONLY_IDENTITY' if args.revise_height_only_routing else 'INITIAL_HEIGHT_OR_CLASS6_CONTEXT',
        routing_changes=transitions,regional_product_code_sha256=sha256_file(ROOT/'stratum_ro/regional_roofs.py'))
    assert not invalid
    (out/'mask_guard_report.json').write_text(json.dumps(audit,indent=2),encoding='utf-8')
    (base/'CURRENT_REVIEW.json').write_text(json.dumps(dict(gpkg=str(target.relative_to(ROOT)),
        report=str((out/'mask_guard_report.json').relative_to(ROOT)),scan_report=str((scan/'report.json').relative_to(ROOT)),
        scope='AUTOMATIC_REGIONAL_REVIEW_NOT_ACCEPTED_INVENTORY'),indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in audit.items() if k not in ['changed','routing_changes']}))


if __name__=='__main__':main()
