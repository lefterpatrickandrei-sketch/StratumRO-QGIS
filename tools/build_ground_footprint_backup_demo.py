"""One explicitly assumed eave-offset example; never a measured wall footprint."""
from pathlib import Path
import sys,json
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import geopandas as gpd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from stratum_ro.regional_roofs import OrthoMosaic,ground_footprint_scenarios,sha256_file


def main():
    out=ROOT/'workspace/reviews/regional_roofs_20261017/ground_backup_T10'
    out.mkdir(exist_ok=False)
    source=ROOT/'workspace/reviews/retry_six_release_20261013/retry_six.gpkg'
    layer=gpd.read_file(source,layer='CORPURI_RECTIFICATE')
    selected=layer[layer['id']=='T10:A1']
    assert len(selected)==1 and selected.iloc[0]['owner_verdict']=='ACCEPTED_BY_OWNER'
    roof=selected.iloc[0].geometry
    scenarios=ground_footprint_scenarios(roof,[.25,.50])
    gpkg=out/'T10_ground_backup.gpkg'
    gpd.GeoDataFrame([dict(id='T10:A1',role='ACCEPTED_ROOF_ONLY_NOT_GROUND',geometry=roof)],
        crs=layer.crs).to_file(gpkg,layer='OBSERVED_ROOF',driver='GPKG')
    gpd.GeoDataFrame([dict(id='T10:A1',**r) for r in scenarios],crs=layer.crs).to_file(
        gpkg,layer='ASSUMED_GROUND_SCENARIOS',driver='GPKG')
    config=json.loads((out.parent/'config.json').read_text())
    mosaic=OrthoMosaic([ROOT/p for p in config['orthophotos']])
    bounds=roof.buffer(8).bounds
    rgb,valid,tr,_=mosaic.read(bounds,.15)
    extent=[tr.c,tr.c+rgb.shape[1]*tr.a,tr.f+rgb.shape[0]*tr.e,tr.f]
    fig,axes=plt.subplots(1,3,figsize=(16,6))
    titles=['Acoperis acceptat vizual\nNu reprezinta masurarea peretilor',
            'Scenariu: streasina presupusa 0.25 m','Scenariu: streasina presupusa 0.50 m']
    for i,ax in enumerate(axes):
        ax.imshow(rgb,extent=extent);ax.plot(*roof.exterior.xy,color='#00ffff',lw=2,label='Acoperis')
        area=roof.area
        if i:
            geom=scenarios[i-1]['geometry'];area=geom.area
            ax.plot(*geom.exterior.xy,color='#ffae00',lw=2,label='Amprenta IPOTETICA')
        ax.set_title(titles[i]+f'\nArie: {area:.2f} m2',fontsize=11)
        ax.set_xlim(extent[:2]);ax.set_ylim(extent[2:]);ax.axis('off');ax.legend(fontsize=8)
    fig.suptitle('BACKUP DEMONSTRATIV / T10 - retrageri alese pentru comparatie, NU masurate din LiDAR',fontsize=12)
    fig.tight_layout();fig.savefig(out/'T10_roof_vs_assumed_ground.png',dpi=160);plt.close(fig)
    report=dict(example='T10:A1',source=str(source),layer='CORPURI_RECTIFICATE',
        source_sha256=sha256_file(source),source_geometry_wkb=roof.wkb_hex,
        roof_area_m2=roof.area,roof_owner_verdict='ACCEPTED_BY_OWNER',
        ground_owner_verdict='NOT_REVIEWED',offsets_m=[.25,.5],
        scenario_areas_m2=[r['geometry'].area for r in scenarios],
        status='IMPLEMENTED_ILLUSTRATION_NOT_MEASURED_WALL_LOCATION',
        production_default=False,lidar_used=False,
        missing_for_measured_ground=['Verified sensor CRS and acquisition correspondence',
            'Observable wall/eave geometry, survey or other independent evidence',
            'Per-edge offset evidence; an isotropic offset is an assumption'])
    (out/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report))


if __name__=='__main__':main()
