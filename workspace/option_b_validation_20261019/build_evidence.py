"""Assemble the actual QGIS comparison renders and preserve observed source bytes."""
from pathlib import Path
import subprocess,shutil,json,hashlib
from PIL import Image,ImageDraw
import geopandas as gpd
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).parent

def main():
    old=ROOT/'workspace/reviews/option_b_simple_variations_20261018_v2/simple_variations.gpkg'
    observed=OUT/'observed_old_B.gpkg';baseline=OUT/'old_B_at_git_checkpoint.gpkg'
    if not observed.exists():shutil.copy2(old,observed)
    if not baseline.exists():baseline.write_bytes(subprocess.check_output(['git','show','HEAD:workspace/reviews/option_b_simple_variations_20261018_v2/simple_variations.gpkg'],cwd=ROOT))
    a=gpd.read_file(observed,layer='B_SIMPLE').set_index('candidate_id');b=gpd.read_file(baseline,layer='B_SIMPLE').set_index('candidate_id')
    difference=[i for i in a.index if i not in b.index or not a.loc[i].geometry.equals(b.loc[i].geometry)]
    (OUT/'source_comparison.json').write_text(json.dumps(dict(observed_sha256=hashlib.sha256(observed.read_bytes()).hexdigest(),git_checkpoint_sha256=hashlib.sha256(baseline.read_bytes()).hexdigest(),changed_geometry_ids=difference,git_revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()),indent=2),encoding='utf-8')
    for oldimg in (OUT/'qgis_cases').glob('*_old.png'):
        key=oldimg.name.split('_')[0];im=Image.new('RGB',(1700,740),'white');draw=ImageDraw.Draw(im)
        draw.text((15,10),f'OPT_B_{key}:C1 | BEFORE: B previously visible',fill='black')
        draw.text((865,10),'AFTER: repaired B candidate (not accepted)',fill='black')
        im.paste(Image.open(oldimg),(0,35));im.paste(Image.open(oldimg.with_name(key+'_new.png')),(850,35))
        im.save(OUT/'qgis_cases'/(key+'_comparison.jpg'),quality=94)
    print('Geometry changes vs Git in previously modified source:',difference)

if __name__=='__main__':main()
