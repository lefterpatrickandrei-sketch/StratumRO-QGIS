"""Prepare mosaic preview or native crops for a reviewed roof lot (QGIS Python)."""
from pathlib import Path
import argparse,json
from osgeo import gdal
gdal.UseExceptions()
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output-dir',type=Path,required=True)
parser.add_argument('--selection',type=Path)
args=parser.parse_args();out=args.output_dir.resolve()
out.mkdir(exist_ok=True)
if args.selection is None:
    tiles=sorted((ROOT/'workspace/reviews/prompt_recovery_20261013/full_aoi').glob('cache_tile_Cluj-*_halo.tif'))
    assert len(tiles)==8
    vrt=out/'cached_mosaic.vrt'
    assert not vrt.exists()
    ds=gdal.BuildVRT(str(vrt),[str(p) for p in tiles]);assert ds;ds=None
    ds=gdal.Translate(str(out/'selection_overview.tif'),str(vrt),xRes=.4,yRes=.4,resampleAlg='bilinear',creationOptions=['COMPRESS=DEFLATE','TILED=YES']);assert ds;ds=None
    print('Cached preview prepared; no reviewed selection or inference is implied.')
else:
    selection=json.loads(args.selection.read_text(encoding='utf-8'))
    covers=out/'covers';covers.mkdir(exist_ok=True)
    vrt=ROOT/'workspace/reviews/lot3_edge_audit_20261017/native_sources.vrt'
    for case in selection['cases']:
        a,b,c,d=case['search_bounds'];padding=max(10.,(28.-min(c-a,d-b))/2)
        path=covers/(case['body_id'].split(':')[0]+'_5cm.tif')
        if path.exists():raise FileExistsError(path)
        ds=gdal.Translate(str(path),str(vrt),projWin=[a-padding,d+padding,c+padding,b-padding],xRes=.05,yRes=.05,resampleAlg='bilinear',creationOptions=['COMPRESS=DEFLATE','TILED=YES']);assert ds;ds=None
        print(case['body_id'],flush=True)
