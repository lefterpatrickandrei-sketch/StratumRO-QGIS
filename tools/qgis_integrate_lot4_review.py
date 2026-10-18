"""Integrate Lot4 into the existing shared QGIS project; preserve prior lots."""
from pathlib import Path
import json,shutil
from qgis.core import (QgsProject,QgsVectorLayer,QgsRasterLayer,QgsFillSymbol,QgsMarkerSymbol,
    QgsCategorizedSymbolRenderer,QgsRendererCategory,QgsPalLayerSettings,QgsTextFormat,
    QgsVectorLayerSimpleLabeling,QgsRectangle,QgsMapSettings,QgsMapRendererParallelJob,
    QgsBookmark,QgsReferencedRectangle)
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtCore import QSize,QTimer
from qgis.utils import iface
ROOT=Path('C:/Users/lefpa/Downloads/QGIS-AI');OUT=ROOT/'workspace/reviews/lot4_20261017';SEL=OUT/'selected'
PROJECT=ROOT/'workspace/reviews/body_recovery_20261013/inspectie_corectii.qgs'
p=QgsProject.instance();root=p.layerTreeRoot()
assert Path(p.fileName()).resolve()==PROJECT.resolve()
assert not any(l.isEditable() for l in p.mapLayers().values() if hasattr(l,'isEditable'))
assert root.findGroup('LOT4_T21_T30_IN_REVIZIE') is None
assert not (SEL/'qgis_after.json').exists()
before=len(p.mapLayers());shutil.copy2(PROJECT,SEL/'shared_project_before_lot4.qgs.backup')
prior=json.loads((OUT/'previous_visible_targets.json').read_text())
for item in prior:
    matches=[l for l in p.mapLayers().values() if l.name()==item['layer']]
    assert len(matches)==1 and matches[0].getFeature(item['fid']).geometry().asWkt()==item['wkt'], 'Previous target changed during review'
group=root.insertGroup(0,'LOT4_T21_T30_IN_REVIZIE')
gpkg=SEL/'lot4_review.gpkg'
roofs=QgsVectorLayer(str(gpkg)+'|layername=ROOF_HYPOTHESES','LOT4 - 9 contururi / in revizie','ogr')
assert roofs.isValid() and roofs.featureCount()==9
categories=[]
for value,color,label in [('VIABLE_VISUAL_HYPOTHESIS','#00d4ff','Ipoteza vizual plauzibila / fara verdict'),('NEEDS_FINISHING','#ffae00','Necesita finisare')]:
    symbol=QgsFillSymbol.createSimple({'color':'0,0,0,0','outline_color':color,'outline_width':'.6'})
    categories.append(QgsRendererCategory(value,symbol,label))
roofs.setRenderer(QgsCategorizedSymbolRenderer('agent_status',categories))
def labels(layer,field,expression=False):
    pal=QgsPalLayerSettings();pal.fieldName=field;pal.isExpression=expression
    text=QgsTextFormat();text.setColor(QColor('white'));text.setSize(10)
    buf=text.buffer();buf.setEnabled(True);buf.setColor(QColor('black'));buf.setSize(.8);text.setBuffer(buf)
    pal.setFormat(text);layer.setLabeling(QgsVectorLayerSimpleLabeling(pal));layer.setLabelsEnabled(True)
labels(roofs,'body_id');p.addMapLayer(roofs,False);group.addLayer(roofs)
missing=QgsVectorLayer(str(gpkg)+'|layername=CASES_REVIEW','LOT4 - T22 nerezolvat','ogr')
assert missing.isValid();assert missing.setSubsetString("\"agent_status\"='UNRESOLVED_AFTER_REVIEW'")
assert len(list(missing.getFeatures()))==1
missing.updateExtents()
missing.renderer().setSymbol(QgsMarkerSymbol.createSimple({'name':'cross2','color':'#ff2222','outline_color':'#ff2222','size':'5'}))
labels(missing,"\"test_id\" || ' / NEREZOLVAT'",True);p.addMapLayer(missing,False);group.addLayer(missing)
history=group.addGroup('DIAGNOSTIC / ferestre si incercari respinse')
for layername,name,color in [('SEARCH_ENVELOPES','LOT4 - ferestre de cautare / NU contur final','#ffd700'),('REJECTED_CANDIDATES','LOT4 - T22 masca respinsa de agent','#ff2222')]:
    layer=QgsVectorLayer(str(gpkg)+'|layername='+layername,name,'ogr');assert layer.isValid()
    layer.renderer().setSymbol(QgsFillSymbol.createSimple({'color':'0,0,0,0','outline_color':color,'outline_width':'.4','outline_style':'dash'}))
    p.addMapLayer(layer,False);node=history.addLayer(layer);node.setItemVisibilityChecked(False)
history.setItemVisibilityChecked(False);history.setExpanded(False)
details=group.addGroup('Lot4 - detalii ortofoto 5cm / CRS interpretat');native=[]
for path in sorted((OUT/'covers').glob('T??_5cm.tif')):
    layer=QgsRasterLayer(str(path),'Lot4 / '+path.stem,'gdal');assert layer.isValid()
    p.addMapLayer(layer,False);details.addLayer(layer);native.append(layer)
assert len(native)==10;details.setExpanded(False)
ortho=[l for l in p.mapLayers().values() if l.name().startswith('Cluj-')]
m=json.loads((SEL/'inputs.json').read_text());frames={c['body_id'][:3]:c['search_bounds'] for c in m['cases']}
bm=p.bookmarkManager();names={b.name() for b in bm.bookmarks()}
for ident,bounds in frames.items():
    name='Lot4 / '+ident
    if name not in names:
        b=QgsBookmark();b.setName(name);b.setGroup('Lot4 T21-T30 / in revizie');b.setExtent(QgsReferencedRectangle(QgsRectangle(*bounds),p.crs()));bm.addBookmark(b)
rendered=SEL/'qgis';rendered.mkdir(exist_ok=False)
full=QgsRectangle(roofs.extent());full.combineExtentWith(missing.extent());full.scale(1.12)
for name,bounds in {**frames,'LOT4_OVERVIEW':[full.xMinimum(),full.yMinimum(),full.xMaximum(),full.yMaximum()]}.items():
    extent=QgsRectangle(*bounds)
    if name!='LOT4_OVERVIEW':extent.scale(1.06)
    settings=QgsMapSettings();settings.setDestinationCrs(p.crs());settings.setLayers([missing,roofs]+native+ortho)
    settings.setExtent(extent);settings.setOutputSize(QSize(1450,1100));settings.setBackgroundColor(QColor('white'))
    job=QgsMapRendererParallelJob(settings);job.start();job.waitForFinished();assert job.renderedImage().save(str(rendered/(name+'.png')))
iface.setActiveLayer(roofs);iface.layerTreeView().scrollToTop();iface.mapCanvas().setExtent(full);iface.mapCanvas().refresh()
p.setTitle('StratumRO - Lot1/Lot2, Lot3 si Lot4 in revizie');assert p.write()
after={'project':p.fileName(),'saved':not p.isDirty(),'previous_layer_count':before,'layer_count':len(p.mapLayers()),
    'group':group.name(),'roof_layer_id':roofs.id(),'roof_count':roofs.featureCount(),'unresolved_count':missing.featureCount(),
    'source':roofs.source(),'case_count':10,'previous_visible_geometries_preserved':len(prior),'owner_verdict_changed':False}
assert len(p.mapLayers())==before+14
(SEL/'qgis_after.json').write_bytes(json.dumps(after,indent=2).encode())
def capture():
    iface.mapCanvas().grab().save(str(SEL/'live_canvas.png'));iface.mainWindow().grab().save(str(SEL/'live_main_window.png'))
QTimer.singleShot(2000,capture)
print('LOT4_SHARED_QGIS_INTEGRATED')
