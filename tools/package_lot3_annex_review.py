"""Preserve existing visible roofs and package a separate, conflicting annex hypothesis."""
from pathlib import Path
import json,hashlib
import geopandas as gpd
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'workspace/reviews/lot3_continuation_20261017'
oldpath=ROOT/'workspace/reviews/lot3_finishing_20261017/results/cadastral_review.gpkg'
newpath=OUT/'annex_final/cadastral_review.gpkg'
old=gpd.read_file(oldpath,layer='ROOF_HYPOTHESES')
new=gpd.read_file(newpath,layer='ROOF_HYPOTHESES')
annex=new[new.body_id=='T18:C2'].copy()
annex['review_reasons']=annex['review_reasons']+';NEW_BODY_IDENTITY_REQUIRES_REVIEW;BODY_IDENTITY_OVERLAP'
annex['status']='REQUIRES_REVIEW'
combined=gpd.GeoDataFrame(pd.concat([old,annex],ignore_index=True),crs=old.crs)
dest=OUT/'annex_review_final.gpkg'
if dest.exists():raise FileExistsError('Preserve previous pack')
combined.to_file(dest,layer='CURRENT_ROOFS_AND_ANNEX_HYPOTHESIS',driver='GPKG')
main=old[old.body_id=='T18:C1'].geometry.iloc[0];extra=annex.geometry.iloc[0]
intersection=main.intersection(extra)
gpd.GeoDataFrame([{'a':'T18:C1','b':'T18:C2','reason':'SHARED_EDGE_REQUIRES_REVIEW','area_m2':intersection.area,'geometry':intersection}],crs=old.crs).to_file(dest,layer='BOUNDARY_CONFLICT',driver='GPKG')
sources=[{'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in [oldpath,newpath]]
report={'sources':sources,'old_geometries_preserved':True,'new_hypothesis':'T18:C2','annex_area_m2':extra.area,
        'annex_vertices':len(extra.exterior.coords)-1,'overlap_with_previous_main_m2':intersection.area,
        'owner_verdict':'PENDING_OWNER_REVIEW','geometry_role':'OBSERVED_ROOF_HYPOTHESIS',
        'wide_window_results_adopted':False,'reason':'T17 merged bodies/lost projections; T18 lost supported wing. Keep original hypotheses and expose annex plus overlap for review.'}
(OUT/'packaging_final_decision.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
