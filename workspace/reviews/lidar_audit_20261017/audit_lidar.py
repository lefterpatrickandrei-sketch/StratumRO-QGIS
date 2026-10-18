"""Read-only source audit; outputs restricted to this inspection directory."""
from pathlib import Path
import json
import laspy
import numpy as np
import rasterio
from rasterio.transform import from_origin

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
SOURCE = Path('C:/Users/lefpa/Desktop/date/Z_VladP/Comparatie/LAZ/NorPuncte_St70_S42.laz')
DTM = SOURCE.parent.parent / 'DTM3m/DTM3m.tif'
las = laspy.read(SOURCE)
x, y, z = np.asarray(las.x), np.asarray(las.y), np.asarray(las.z)
cls = np.asarray(las.classification)
x0, ytop = float(np.floor(x.min())), float(np.ceil(y.max()))
w, h = int(np.ceil(x.max()-x0))+1, int(np.ceil(ytop-y.min()))+1
c, r = (x-x0).astype(int), (ytop-y).astype(int)
idx = r*w+c
counts = np.bincount(idx, minlength=h*w).reshape(h,w).astype('float32')
build = np.bincount(idx[cls == 6], minlength=h*w).reshape(h,w).astype('float32')
dsm = np.full(h*w, -9999, dtype='float32')
np.maximum.at(dsm, idx, z)
dsm = dsm.reshape(h,w)
for name, arr, nodata in [('point_density_1m',counts,None),('class6_density_1m',build,None),('surface_height_1m',dsm,-9999)]:
    if (OUT/(name+'.tif')).exists():
        continue
    with rasterio.open(OUT / (name+'.tif'),'w',driver='GTiff',height=h,width=w,count=1,dtype='float32',crs='EPSG:3844',transform=from_origin(x0,ytop,1,1),nodata=nodata,compress='deflate') as dst:
        dst.write(arr,1)
        dst.update_tags(CRS_STATUS='HYPOTHESIS_3844_FROM_COORDINATE_RANGE_NOT_INDEPENDENTLY_VALIDATED',SOURCE=str(SOURCE))
with rasterio.open(DTM) as ds:
    dtm_crs=str(ds.crs)
    terrain=ds.read(1)
    inv=~ds.transform
    dc=np.floor(inv.a*x+inv.b*y+inv.c).astype(int)
    dr=np.floor(inv.d*x+inv.e*y+inv.f).astype(int)
    inside=(dc>=0)&(dc<ds.width)&(dr>=0)&(dr<ds.height)
    ground=(cls==2)&inside
    zz=terrain[dr[ground],dc[ground]]
    dz=z[ground]-zz
    good=(zz!=ds.nodata)&np.isfinite(zz)
    dz=dz[good]
    ground_check={'count':len(dz),'median_m':float(np.median(dz)),'p05_m':float(np.percentile(dz,5)),'p95_m':float(np.percentile(dz,95)),'median_absolute_m':float(np.median(np.abs(dz)))}
    relative=np.full(len(z),np.nan)
    positions=np.flatnonzero(inside)
    tv=terrain[dr[inside],dc[inside]]
    valid=(tv!=ds.nodata)&np.isfinite(tv)
    relative[positions[valid]]=z[positions[valid]]-tv[valid]
    rel_grid=np.full(h*w,-9999,dtype='float32')
    np.maximum.at(rel_grid,idx[np.isfinite(relative)],relative[np.isfinite(relative)])
    with rasterio.open(OUT/'relative_surface_1m.tif','w',driver='GTiff',height=h,width=w,count=1,dtype='float32',crs='EPSG:3844',transform=from_origin(x0,ytop,1,1),nodata=-9999,compress='deflate') as dst:
        dst.write(rel_grid.reshape(h,w),1)
        dst.update_tags(CRS_STATUS='HYPOTHESIS_3844',HEIGHT_METHOD='max point z minus nearest 3m DTM sample; diagnostic only')
values,nums=np.unique(cls,return_counts=True)
report={'source':str(SOURCE),'points':len(x),'header_creation_date':str(las.header.creation_date),'acquisition_date':'NOT_VERIFIED_HEADER_DATE_IS_NOT_ACQUISITION_PROOF','declared_crs':str(las.header.parse_crs()),'declared_crs_wkt':las.header.parse_crs().to_wkt(),'coordinate_bounds':[las.header.mins.tolist(),las.header.maxs.tolist()],'classification_counts':{str(int(k)):int(v) for k,v in zip(values,nums)},'density':{'grid_m':1,'occupied_cells':int(np.count_nonzero(counts)),'mean_points_per_occupied_m2':float(counts[counts>0].mean()),'median_points_per_occupied_m2':float(np.median(counts[counts>0]))},'dtm':{'path':str(DTM),'declared_crs':dtm_crs,'ground_minus_dtm':ground_check},'crs_status':'Coordinates treated as EPSG3844 hypothesis only. No reprojection or source edits.'}
manifest=ROOT/'workspace/reviews/lot3_revision_v3_20261016/selection_manifest.json'
report['case_windows']=[]
if manifest.exists():
    for case in json.loads(manifest.read_text(encoding='utf-8'))['cases']:
        a,b,d,e=case['search_bbox']
        sel=(x>=a)&(x<=d)&(y>=b)&(y<=e)
        cv,cn=np.unique(cls[sel],return_counts=True)
        rr=relative[sel&np.isfinite(relative)]
        report['case_windows'].append({'id':case['test_id'],'bounds':[a,b,d,e],'points':int(sel.sum()),'points_per_bbox_m2':float(sel.sum()/((d-a)*(e-b))),'classes':{str(int(k)):int(v) for k,v in zip(cv,cn)},'relative_height_p05_p50_p95_m':np.percentile(rr,[5,50,95]).tolist() if len(rr) else None})
(OUT/'lidar_metadata_audit.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
