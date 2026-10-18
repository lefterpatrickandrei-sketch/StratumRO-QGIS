"""Package visually selected repairs with explicit provenance and topology QA."""
from pathlib import Path
import sys,json,hashlib,argparse
import geopandas as gpd
import numpy as np,rasterio
from shapely.geometry import Polygon
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from stratum_ro.roof_simple_geometry import simple_roof_geometry
from stratum_ro.roof_mask_fidelity import rectangular_roof_core
from stratum_ro.cadastral_roof_workflow import clip_roof_to_valid_grid
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output-name',default='selected')
args=parser.parse_args()
if Path(args.output_name).name!=args.output_name:raise ValueError('A directory name is required')
OUT=ROOT/'workspace/reviews/lot3_repairs_20261017';dest=OUT/args.output_name;dest.mkdir(exist_ok=True)
if (dest/'lot3_repaired.gpkg').exists():raise FileExistsError('Preserve previous selected package')
old=gpd.read_file(ROOT/'workspace/reviews/lot3_edge_audit_20261017/lot3_display_snapshot.gpkg',layer='CURRENT_REVIEW_HYPOTHESES')
chosen={};lineage={};diagnostics={}
for _,r in old.iterrows():
    ident=r.body_id if isinstance(r.body_id,str) else r.id
    chosen[ident]=r.geometry;lineage[ident]='PRESERVED_PREVIOUS';diagnostics[ident]={}
for folder in ['simplified2','masked_T12','T18_surfaces','T20_edges','T16_surfaces','T16_porch']:
    data=gpd.read_file(OUT/folder/'cadastral_review.gpkg',layer='ROOF_HYPOTHESES')
    for _,r in data.iterrows():
        if folder=='simplified2' and (r.body_id=='T18:C1' or r.body_id.startswith('T20:')):continue
        chosen[r.body_id]=r.geometry;lineage[r.body_id]=folder;diagnostics[r.body_id]={'method':r.get('method')}
# For reviewed rectilinear T18 surfaces, fit the complete real optical masks,
# rather than the previous incorrect rectangle. Annex C2 retains its curved outline.
raw=gpd.read_file(OUT/'T18_surfaces/cadastral_review.gpkg',layer='RAW_OPTICAL_MASKS')
for _,r in raw.iterrows():
    g,d=simple_roof_geometry(Polygon(r.geometry.exterior),min_support=.95,min_coverage=.95,max_vertices=20)
    if d['method']!='NEEDS_REVIEW':chosen[r.body_id]=g;diagnostics[r.body_id]=d
raw=gpd.read_file(OUT/'attempt1/cadastral_review.gpkg',layer='RAW_OPTICAL_MASKS')
# T19's complete articulated roof supports an 18-corner orthogonal fit.
# This removes thin mask spikes; support/coverage remain mask comparisons,
# never cadastral accuracy or owner acceptance.
row=raw[raw.body_id=='T19:C1'].iloc[0]
g,d=simple_roof_geometry(Polygon(row.geometry.exterior),min_support=.95,min_coverage=.95,max_vertices=24,angle_search_degrees=8)
if d['method']!='NEEDS_REVIEW':chosen['T19:C1']=g;diagnostics['T19:C1']=d
manifest=json.loads((OUT/'attempt1/inputs.json').read_text())
row=raw[raw.body_id=='T15:C1'].iloc[0];case=next(c for c in manifest['cases'] if c['body_id']=='T15:C1')
g,d=rectangular_roof_core(row.geometry,case['anchor'],opening_radius_m=.5)
if d['status']=='RECTIFIED_HYPOTHESIS_PENDING_OWNER_REVIEW':chosen['T15:C1']=g;diagnostics['T15:C1']=d
porch=gpd.read_file(OUT/'T16_porch/cadastral_review.gpkg',layer='RAW_OPTICAL_MASKS').iloc[0]
g,d=rectangular_roof_core(porch.geometry,[390805.8,585317.8],opening_radius_m=.5)
if d['status']=='RECTIFIED_HYPOTHESIS_PENDING_OWNER_REVIEW':chosen['T16:C3']=g;diagnostics['T16:C3']=d
# Reapply the exact validity grid to the mask-aware T12 result after any simplification.
mm=json.loads((OUT/'masked_T12/inputs.json').read_text())['cases'][0]
with rasterio.open(OUT/'masked_T12/T12_C2_ortho.tif') as src:
    chosen['T12:C2']=clip_roof_to_valid_grid(chosen['T12:C2'],np.all(src.read_masks([1,2,3])>0,axis=0),src.transform,mm['anchor'])
rows=[]
for ident,g in sorted(chosen.items()):
    upstream_folder={'simplified2':'attempt1','T20_edges':'attempt1'}.get(lineage[ident],lineage[ident])
    upstream=[];upstream_path=OUT/upstream_folder/'report.json'
    if upstream_path.exists():
        upstream_report=json.loads(upstream_path.read_text())
        if isinstance(upstream_report,dict):
            upstream=next((c.get('review_reasons',[]) for c in upstream_report.get('cases',[]) if c['body_id']==ident),[])
    rows.append({'body_id':ident,'test_id':ident.split(':')[0],'owner_verdict':'PENDING_OWNER_REVIEW',
       'geometry_role':'OBSERVED_ROOF_HYPOTHESIS','ground_status':'NOT_MEASURED','lineage':lineage[ident],
       'qa_status':'REQUIRES_OWNER_REVIEW','upstream_review_reasons':';'.join(upstream),
       'vertices':len(g.exterior.coords)-1+sum(len(r.coords)-1 for r in g.interiors),
       'area_m2':g.area,'geometry':g})
df=gpd.GeoDataFrame(rows,crs=3844)
assert df.is_valid.all()
df.to_file(dest/'lot3_repaired.gpkg',layer='REPAIRED_ROOF_CANDIDATES',driver='GPKG')
conflicts=[]
for i,a in df.iterrows():
    for j,b in df.iterrows():
        if j<=i:continue
        intersection=a.geometry.intersection(b.geometry)
        if intersection.area>.25:conflicts.append({'a':a.body_id,'b':b.body_id,'area_m2':intersection.area,'geometry':intersection})
if conflicts:gpd.GeoDataFrame(conflicts,crs=3844).to_file(dest/'lot3_repaired.gpkg',layer='OVERLAP_REVIEW',driver='GPKG')
report={'scope':'DISPLAY_CANDIDATES_NOT_OWNER_ACCEPTANCE','all_valid':True,'bodies':[{k:v for k,v in r.items() if k!='geometry'} for r in rows],
        'overlaps':[{k:v for k,v in r.items() if k!='geometry'} for r in conflicts],
        'postprocessing':diagnostics,'warnings':['T12:C2 has masked NoData near target; completeness unconfirmed.',
            'T16 is split into three observed roof-surface hypotheses; cadastral identities and junctions remain unconfirmed.',
            'Body/roof-surface identities T18:C3 and T20:C2 require explicit owner review.',
            'T17 is preserved, with its previous completeness warnings.','Model/mask support is not positional or cadastral accuracy.']}
(dest/'selection_report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({'bodies':len(df),'overlaps':report['overlaps'],'vertices':dict(zip(df.body_id,df.vertices))}))
