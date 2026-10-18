"""Build and render a separate comparison project with the installed QGIS runtime."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from pathlib import Path
import argparse,json
from qgis.core import (QgsApplication,QgsProject,QgsRasterLayer,QgsVectorLayer,
    QgsFillSymbol,QgsCoordinateReferenceSystem,QgsRectangle,QgsReferencedRectangle,
    QgsMapSettings,QgsMapRendererParallelJob,QgsBookmark)
from qgis.PyQt.QtCore import QSize
from qgis.PyQt.QtGui import QColor

parser=argparse.ArgumentParser()
parser.add_argument('--review-dir',type=Path,required=True)
parser.add_argument('--baseline',type=Path,required=True)
args=parser.parse_args();out=args.review_dir.resolve();baseline=args.baseline.resolve()
app=QgsApplication([],False);app.initQgis()
project=QgsProject();project.setCrs(QgsCoordinateReferenceSystem('EPSG:3844'))
project.setTitle('StratumRO - comparatie integrare flux cadastral - NEVERIFICAT')
root=project.layerTreeRoot();base=root.addGroup('Ortofoto - numai citire');ortho=[]
repo=Path(__file__).resolve().parents[1]
for path in sorted((repo/'workspace/reviews/prompt_recovery_20261013/full_aoi').glob('cache_tile_Cluj-*_halo.tif')):
    layer=QgsRasterLayer(str(path),path.stem);project.addMapLayer(layer,False);base.addLayer(layer);ortho.append(layer)
layers={}
for key,path,layername,color,title in [
    ('baseline',baseline,'IPOTEZE_RECTIFICATE','#00ffff','DEMONSTRATIE ANTERIOARA - cyan - neacceptata'),
    ('current',out/'cadastral_review.gpkg','ROOF_HYPOTHESES','#ff8800','FLUX PRODUS - portocaliu - necesita verificare')]:
    group=root.insertGroup(0,title)
    layer=QgsVectorLayer(str(path)+'|layername='+layername,title,'ogr')
    if not layer.isValid():raise RuntimeError('Invalid result layer: '+str(path))
    layer.renderer().setSymbol(QgsFillSymbol.createSimple({'color':'0,0,0,0','outline_color':color,'outline_width':'0.6'}))
    project.addMapLayer(layer,False);group.addLayer(layer);layers[key]=layer
boxes={'T17':(390765,585430,390903,585553),'T18':(390585,585480,390674,585590),'T20':(390930,585195,391005,585277)}
for name,coords in boxes.items():
    bookmark=QgsBookmark();bookmark.setName(name+' - comparatie');bookmark.setExtent(QgsReferencedRectangle(QgsRectangle(*coords),project.crs()))
    project.bookmarkManager().addBookmark(bookmark)
    for mode in ['baseline','current']:
        settings=QgsMapSettings();settings.setDestinationCrs(project.crs());settings.setLayers([layers[mode]]+ortho)
        settings.setExtent(QgsRectangle(*coords));settings.setOutputSize(QSize(1200,1000));settings.setBackgroundColor(QColor('white'))
        job=QgsMapRendererParallelJob(settings);job.start();job.waitForFinished();job.renderedImage().save(str(out/(name+'_'+mode+'_qgis.png')))
project.viewSettings().setDefaultViewExtent(QgsReferencedRectangle(QgsRectangle(*boxes['T17']),project.crs()))
project.setFileName(str(out/'StratumRO_flux_cadastral_comparatie.qgz'))
if not project.write():raise RuntimeError('Project save failed')
(out/'qgis_validation.json').write_text(json.dumps({'project':project.fileName(),'baseline_count':layers['baseline'].featureCount(),
    'current_count':layers['current'].featureCount(),'layers_valid':all(l.isValid() for l in project.mapLayers().values()),
    'main_project_modified':False},indent=2),encoding='utf-8')
print(project.fileName())
# Explicit release avoids QGIS provider teardown after QApplication deletion.
project.clear();del project
app.exitQgis()
