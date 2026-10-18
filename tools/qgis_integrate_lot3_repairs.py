"""Run inside the shared QGIS session; selected proposals remain unaccepted."""
from pathlib import Path
import json,shutil
from qgis.core import (QgsProject,QgsVectorLayer,QgsRasterLayer,QgsFillSymbol,QgsPalLayerSettings,
    QgsTextFormat,QgsVectorLayerSimpleLabeling,QgsRectangle,QgsMapSettings,QgsMapRendererParallelJob,
    QgsBookmark,QgsReferencedRectangle)
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtCore import QSize,QTimer
from qgis.utils import iface
ROOT=Path('C:/Users/lefpa/Downloads/QGIS-AI');OUT=ROOT/'workspace/reviews/lot3_repairs_20261017';SEL=OUT/'selected'
PROJECT=ROOT/'workspace/reviews/body_recovery_20261013/inspectie_corectii.qgs'
p=QgsProject.instance();root=p.layerTreeRoot()
assert Path(p.fileName()).resolve()==PROJECT.resolve()
assert not [l for l in p.mapLayers().values() if hasattr(l,'isEditable') and l.isEditable()]
assert root.findGroup('LOT3_REPARAT_20261017_NEVALIDAT') is None
before={'file':p.fileName(),'dirty':p.isDirty(),'layers':[{'id':l.id(),'name':l.name(),'source':l.source(),'visible':root.findLayer(l.id()).isVisible()} for l in p.mapLayers().values()]}
(SEL/'qgis_before.json').write_text(json.dumps(before,indent=2));shutil.copy2(PROJECT,SEL/'shared_project_before_repair.qgs.backup')
for layer in p.mapLayers().values():
    if layer.type()==0 and (layer.name().startswith('LOT3_') or layer.name().startswith(('T17:','T18:'))):
        root.findLayer(layer.id()).setItemVisibilityChecked(False)
for child in root.children():
    if hasattr(child,'children') and child.name().startswith('LOT3_'):child.setItemVisibilityChecked(False)
group=root.insertGroup(0,'LOT3_REPARAT_20261017_NEVALIDAT')
roofs=QgsVectorLayer(str(SEL/'lot3_repaired.gpkg')+'|layername=REPAIRED_ROOF_CANDIDATES','LOT3 - 18 ipoteze / NECESITA VERDICT','ogr')
assert roofs.isValid() and roofs.featureCount()==18
roofs.renderer().setSymbol(QgsFillSymbol.createSimple({'color':'0,0,0,0','outline_color':'#00ffff','outline_width':'0.55'}))
pal=QgsPalLayerSettings();pal.fieldName='body_id';text=QgsTextFormat();text.setColor(QColor('white'));text.setSize(10)
buf=text.buffer();buf.setEnabled(True);buf.setColor(QColor('black'));buf.setSize(.9);text.setBuffer(buf)
pal.setFormat(text);roofs.setLabeling(QgsVectorLayerSimpleLabeling(pal));roofs.setLabelsEnabled(True)
p.addMapLayer(roofs,False);group.addLayer(roofs)
native=[]
details=group.addGroup('DETALII SID 5cm / interpretare CRS proiect')
for path in sorted((OUT/'covers').glob('*_5cm.tif')):
    raster=QgsRasterLayer(str(path),path.stem,'gdal');assert raster.isValid()
    p.addMapLayer(raster,False);details.addLayer(raster);native.append(raster)
orthos=[l for l in p.mapLayers().values() if l.name().startswith('Cluj-')]
frames=json.loads((SEL/'case_frames.json').read_text());bm=p.bookmarkManager()
names={b.name() for b in bm.bookmarks()}
for ident,bounds in frames.items():
    name='Lot3 reparat / '+ident
    if name not in names:
        mark=QgsBookmark();mark.setName(name);mark.setGroup('Lot3 reparat - in revizie')
        mark.setExtent(QgsReferencedRectangle(QgsRectangle(*bounds),p.crs()));bm.addBookmark(mark)
for name,bounds in {**frames,'LOT3_OVERVIEW':[390570,585070,391330,585780]}.items():
    settings=QgsMapSettings();settings.setDestinationCrs(p.crs());settings.setLayers([roofs]+native+orthos)
    settings.setExtent(QgsRectangle(*bounds));settings.setOutputSize(QSize(1440,1100));settings.setBackgroundColor(QColor('white'))
    job=QgsMapRendererParallelJob(settings);job.start();job.waitForFinished();assert job.renderedImage().save(str(SEL/(name+'_qgis.png')))
iface.mapCanvas().setExtent(QgsRectangle(*frames['T20']));iface.mapCanvas().refresh()
p.setTitle('StratumRO - Lot1/Lot2 si Lot3 in revizie');assert p.write()
(SEL/'qgis_after.json').write_text(json.dumps({'file':p.fileName(),'layer_id':roofs.id(),'feature_count':roofs.featureCount(),
    'source':roofs.source(),'total_layers':len(p.mapLayers()),'new_bookmarks':list(frames),'native_detail_layers':len(native),
    'owner_verdict':'PENDING_OWNER_REVIEW'},indent=2))
def capture_repaired_canvas():iface.mapCanvas().grab().save(str(SEL/'live_qgis.png'))
QTimer.singleShot(2000,capture_repaired_canvas)
print('LOT3_REPAIRED_SHARED_QGIS_OK')
