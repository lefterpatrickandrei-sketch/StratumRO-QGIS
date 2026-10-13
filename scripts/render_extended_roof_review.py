"""Re-render the saved ten-object experiment without repeating SAM inference."""
import argparse
from pathlib import Path
import geopandas as gpd
import rasterio
import matplotlib.pyplot as plt
from extend_roof_visual_review import draw,ROOT


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run-dir',required=True)
    out=Path(p.parse_args().run_dir)
    current=gpd.read_file(out/'review18.gpkg',layer='TESTE_10_REZULTATE')
    old=gpd.read_file(out/'review18.gpkg',layer='TESTE_10_ANTERIOR')
    with rasterio.open(ROOT/'workspace/output/ortofoto_cluj_usamv_rgb.vrt') as ortho:
        fig,axes=plt.subplots(5,2,figsize=(13,23),layout='constrained')
        for ax,row in zip(axes.flat,old.sort_values('id').itertuples()):
            group=current[current.test_id==row.id]
            parts=list(group.geometry)
            colors=['red' if r.simple_method=='NEEDS_REVIEW' or bool(r.failure_reason) else 'lime' for r in group.fillna({'failure_reason':''}).itertuples()]
            title=row.id+' '+row.source_id+' | '+('REVIZIE NECESARA' if 'red' in colors else 'FORMA SIMPLA - de verificat')
            draw(ax,ortho,row.geometry,parts,title,colors)
            single,sax=plt.subplots(figsize=(8,8),layout='constrained');draw(sax,ortho,row.geometry,parts,title,colors)
            single.savefig(out/(row.id+'.png'),dpi=150);plt.close(single)
        fig.suptitle('10 teste — mov: anterior; verde: forma simpla; rosu: esec/revizie; verdict utilizator in asteptare')
        fig.savefig(out/'test10_contact_sheet.png',dpi=140);plt.close(fig)
    print(out/'test10_contact_sheet.png')


if __name__=='__main__':main()
