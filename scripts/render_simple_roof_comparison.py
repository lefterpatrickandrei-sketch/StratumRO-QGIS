"""Render old/new roof outlines over the native orthophoto for manual review."""
import argparse
from pathlib import Path
import geopandas as gpd
import numpy as np
import rasterio
from rasterio.windows import from_bounds,bounds as window_bounds
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--gpkg',required=True);p.add_argument('--ortho',required=True)
    p.add_argument('--region',required=True);p.add_argument('--output',required=True)
    args=p.parse_args()
    current=gpd.read_file(args.gpkg,layer='ACOPERISURI_SIMPLE')
    old=gpd.read_file(args.gpkg,layer='CONTURURI_ANTERIOARE')
    prior=dict(zip(old.id,old.geometry));rows=current[current.id.str.startswith(args.region)]
    fig,axes=plt.subplots(int(np.ceil(len(rows)/2)),2,figsize=(12,20),layout='constrained',squeeze=False)
    with rasterio.open(args.ortho) as src:
        for ax,row in zip(axes.flat,rows.itertuples()):
            g=row.geometry;before=prior[row.id];extent=g.union(before).buffer(4).bounds
            xmin,ymin,xmax,ymax=extent
            win=from_bounds(xmin,ymin,xmax,ymax,src.transform).round_offsets().round_lengths()
            rgb=np.moveaxis(src.read([1,2,3],window=win),0,-1);l,b,r,t=window_bounds(win,src.transform)
            ax.imshow(rgb,extent=[l,r,b,t]);ax.plot(*before.exterior.xy,color='magenta',lw=1.8)
            ax.plot(*g.exterior.xy,color='lime',lw=1.8)
            ax.set_xlim(l,r);ax.set_ylim(b,t);ax.axis('off')
            ax.set_title(row.id.split(':')[-1]+f' | {row.vertices} colturi | '+
                         ('pastrat' if row.simple_method=='PRESERVED_PREVIOUS_AUDIT' else 'simplificat'))
        for ax in list(axes.flat)[len(rows):]:ax.axis('off')
    fig.suptitle('Magenta: anterior | Verde: rectificat — contur de acoperis pentru inspectie',fontsize=13)
    fig.savefig(args.output,dpi=140);plt.close(fig)
    print(str(Path(args.output).resolve()))


if __name__=='__main__':main()
