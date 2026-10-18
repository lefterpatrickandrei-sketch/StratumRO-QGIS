"""Prepare actual RGB review crops; never self-attest visual inspection."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import geopandas as gpd
import numpy as np
import rasterio
from PIL import Image,ImageDraw
from shapely.geometry import box
from shapely.ops import unary_union
from stratum_ro.api.service import PlatformService

cfg=json.loads((ROOT/'workspace/option_b_refinement_20261018/config.json').read_text())
engine=PlatformService(ROOT).create_regional_roof_refiner([ROOT/p for p in cfg['orthophotos']],height_path=ROOT/cfg['height'])
data=gpd.read_file(ROOT/cfg['source'],layer=cfg['layer']).set_index('body_id')
out=ROOT/'workspace/reviews/option_b_refinement_20261018_evaluation';out.mkdir(exist_ok=False)
groups=[['OPT_B_006:C1'],['OPT_B_046:C1'],['OPT_B_080:C1'],['OPT_B_120:C1'],['OPT_B_154:C1','OPT_B_169:C1']]
cases=[]
for ids in groups:
    g=unary_union([data.loc[i].geometry for i in ids]);target=box(*g.bounds).buffer(5).bounds
    search=box(*target).buffer(5).bounds;bounds=box(*search).buffer(20).bounds
    rgb,valid,tr,used=engine.mosaic.read(bounds,.15)
    name=ids[0].replace(':','_');tile=out/(name+'.tif');picture=out/(name+'.png')
    with rasterio.open(tile,'w',driver='GTiff',height=rgb.shape[0],width=rgb.shape[1],count=3,
                       dtype='uint8',crs='EPSG:3844',transform=tr,compress='deflate') as dst:
        dst.write(np.moveaxis(rgb,-1,0));dst.write_mask(valid.astype('uint8')*255)
    im=Image.fromarray(rgb);draw=ImageDraw.Draw(im)
    for ident in ids:
        poly=data.loc[ident].geometry
        xy=[(~tr)*p for p in poly.exterior.coords];draw.line(xy,fill='orange',width=3)
        p=poly.representative_point();x,y=(~tr)*(p.x,p.y)
        draw.ellipse((x-5,y-5,x+5,y+5),fill='cyan')
    im.thumbnail((1100,900));im.save(picture)
    anchor=data.loc[ids[0]].geometry.representative_point()
    cases.append(dict(test_id=name,source_body_ids=ids,tile=str(tile),search_center=[anchor.x,anchor.y],
        target_extent=list(target),search_bbox=list(search),selection_image=str(picture),
        valid_fraction=float(valid.mean()),selection_review={'status':'AWAITING_ACTUAL_VISUAL_REVIEW'}))
(out/'selection_draft.json').write_text(json.dumps(dict(schema_version=2,crs='EPSG:3844',cases=cases),indent=2))
print(json.dumps({'output':str(out),'cases':len(cases)}))
