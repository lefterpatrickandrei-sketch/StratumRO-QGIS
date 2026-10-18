"""Run using QGIS Python/GDAL: crop native SID mosaic at 5cm, preserve source files."""
from pathlib import Path
import json
from osgeo import gdal
gdal.UseExceptions()
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'workspace/reviews/lot3_repairs_20261017'
m=json.loads((OUT/'workflow_inputs.json').read_text());(OUT/'covers').mkdir(exist_ok=True)
vrt=ROOT/'workspace/reviews/lot3_edge_audit_20261017/native_sources.vrt'
for scene in sorted({c['body_id'].split(':')[0] for c in m['cases']}):
    cases=[c for c in m['cases'] if c['body_id'].startswith(scene+':')]
    a=min(c['search_bounds'][0] for c in cases)-8;b=min(c['search_bounds'][1] for c in cases)-8
    c=max(c['search_bounds'][2] for c in cases)+8;d=max(c['search_bounds'][3] for c in cases)+8
    dest=OUT/'covers'/(scene+'_5cm.tif')
    if dest.exists():raise FileExistsError('Preserve previous cover')
    ds=gdal.Translate(str(dest),str(vrt),projWin=[a,d,c,b],xRes=.05,yRes=.05,resampleAlg='bilinear',
        creationOptions=['COMPRESS=DEFLATE','TILED=YES']);assert ds is not None;ds=None
print('Native source covers ready')
