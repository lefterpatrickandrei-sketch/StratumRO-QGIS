"""Run with QGIS Python/GDAL to preserve native SID detail around T18 seam."""
from pathlib import Path
import json
from osgeo import gdal
gdal.UseExceptions()
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'workspace/reviews/lot3_edge_audit_20261017'
OUT.mkdir(exist_ok=True)
source=Path('C:/Users/lefpa/Desktop/date/Z_VladP/OrtoFoto Cluj USAMV')
paths=sorted(source.glob('Orto Cluj-*.sid'))
assert len(paths)==8
metadata=[]
for p in paths:
    ds=gdal.Open(str(p));metadata.append({'path':str(p),'size_bytes':p.stat().st_size,
        'transform':ds.GetGeoTransform(),'width':ds.RasterXSize,'height':ds.RasterYSize,
        'projection':ds.GetProjection()});ds=None
vrt=OUT/'native_sources.vrt'
ds=gdal.BuildVRT(str(vrt),[str(p) for p in paths]);assert ds is not None;ds=None
for name,bounds,res in [('T18_native_seam.tif',[390600,585546,390628,585518],None),
                         ('T18_detail_5cm.tif',[390590,585560,390660,585500],.05)]:
    dest=OUT/name
    if dest.exists():raise FileExistsError('Preserve native evidence')
    args={'projWin':bounds,'creationOptions':['COMPRESS=DEFLATE','TILED=YES']}
    if res:args.update(xRes=res,yRes=res,resampleAlg='bilinear')
    ds=gdal.Translate(str(dest),str(vrt),**args);assert ds is not None
    metadata.append({'output':name,'transform':ds.GetGeoTransform(),'width':ds.RasterXSize,'height':ds.RasterYSize});ds=None
(OUT/'native_sources.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
print(json.dumps(metadata[-2:]))
