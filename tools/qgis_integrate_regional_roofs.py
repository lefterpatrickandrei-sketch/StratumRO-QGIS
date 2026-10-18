"""Show automatic regional baseline in the same project, never replace lots."""
from pathlib import Path
import json,sys,hashlib,shutil
from qgis.core import (QgsProject,QgsVectorLayer,QgsFillSymbol,QgsCategorizedSymbolRenderer,
    QgsRendererCategory,QgsRectangle,QgsMapSettings,QgsMapRendererParallelJob,
    QgsBookmark,QgsReferencedRectangle)
from qgis.PyQt.QtCore import QSize,QTimer
from qgis.PyQt.QtGui import QColor
from qgis.utils import iface
ROOT=Path('C:/Users/lefpa/Downloads/QGIS-AI');sys.path.insert(0,str(ROOT))
from stratum_ro.qgis_render_order import vectors_above_rasters
OUT=ROOT/'workspace/reviews/regional_roofs_20261017';SCAN=OUT/'scan_v1'
PROJECT=ROOT/'workspace/reviews/body_recovery_20261013/inspectie_corectii.qgs'
p=QgsProject.instance();root=p.layerTreeRoot()
assert Path(p.fileName()).resolve()==PROJECT.resolve()
was_dirty=p.isDirty()
assert not any(l.isEditable() for l in p.mapLayers().values() if hasattr(l,'isEditable'))
assert not root.findGroup('ACOPERISURI_AUTOMAT_REGIONAL_20261017_NEVALIDAT')
report=json.loads((SCAN/'report.json').read_text());assert report['status']=='SCAN_COMPLETED_UNVALIDATED'
out=OUT/'qgis';out.mkdir(exist_ok=False)
shutil.copy2(PROJECT,out/'shared_project_before_regional.qgs.backup')
def snapshot():
    return {l.id():{'source':l.source(),'wkb':{str(f.id()):hashlib.sha256(bytes(f.geometry().asWkb())).hexdigest()
        for f in l.getFeatures()}} for l in p.mapLayers().values() if l.type()==0}
before=snapshot();before_count=len(p.mapLayers())
if was_dirty:
    expected=json.loads((OUT/'render_order_fix/verification.json').read_text())['snapshot']
    assert set(expected)==set(before)
    assert all(before[k]['source']==v['source'] and before[k]['wkb']==v['geometries'] for k,v in expected.items())
    # Owner authorized saving progress. Preserve current view/styles instead of
    # resetting them to the last saved XML; editable data are blocked above.
    assert p.write()
    shutil.copy2(PROJECT,out/'shared_project_current_view_preserved.qgs.backup')
group=root.insertGroup(0,'ACOPERISURI_AUTOMAT_REGIONAL_20261017_NEVALIDAT')
gpkg=ROOT/json.loads((OUT/'CURRENT_REVIEW.json').read_text())['gpkg']
new=[]
def add(path,layername,name,color,visible=True):
    layer=QgsVectorLayer(str(path)+'|layername='+layername,name,'ogr');assert layer.isValid()
    layer.renderer().setSymbol(QgsFillSymbol.createSimple({'color':'0,0,0,0','outline_color':color,'outline_width':'.35'}))
    p.addMapLayer(layer,False);node=group.addLayer(layer);node.setItemVisibilityChecked(visible);new.append(layer)
    return layer
roofs=add(gpkg,'ROOF_CANDIDATES','AUTO - candidati acoperis / NEVALIDATI','#00d4ff')
cats=[]
for status,color,title in [('SIMPLE_HYPOTHESIS_REVIEW','#00d4ff','Forma simpla / necesita verdict'),
    ('OPTICAL_HYPOTHESIS_REVIEW','#00d4ff','Ipoteza optica / necesita verdict'),
    ('GEOMETRY_NEEDS_REVIEW','#ffae00','Masca prea complexa / de reparat'),
    ('INCOMPLETE_CONTEXT_REVIEW','#ff3333','Context incomplet / de verificat')]:
    symbol=QgsFillSymbol.createSimple({'color':'0,0,0,0','outline_color':color,'outline_width':'.35'})
    cats.append(QgsRendererCategory(status,symbol,title))
roofs.setRenderer(QgsCategorizedSymbolRenderer('geometry_status',cats))
unknown=add(gpkg,'OPTICAL_UNKNOWN','AUTO - obiecte optice INCERTE / nu presupune cladiri','#ffa500',False)
vegetation=add(gpkg,'LIKELY_VEGETATION','AUTO - vegetatie probabila / diagnostic','#998844',False)
coverage=add(gpkg,'SCAN_COVERAGE','AUTO - acoperire scanare / nu parcele','#888888',False)
raw=add(gpkg,'RAW_SELECTED_OBSERVATIONS','AUTO - observatii brute / diagnostic','#bb44ee',False)
demo=OUT/'ground_backup_T10/T10_ground_backup.gpkg'
ground=add(demo,'ASSUMED_GROUND_SCENARIOS','T10 BACKUP - retrageri PRESUPUSE / NU masuratori','#ffae00',False)
assert roofs.featureCount()==report['routes']['ROOF_CANDIDATE_REVIEW']
vectors_above_rasters(p)
after=snapshot();assert all(after[k]==v for k,v in before.items())
ortho=[l for l in p.mapLayers().values() if l.name().startswith('Cluj-')]
frames={'REGIONAL_OVERVIEW':[390504.3,584812.8,391602.9,585911.4],
    'CAMPUS_NORTH':[390620,585570,391210,585790],
    'CAMPUS_SOUTH':[390670,585080,391120,585470],
    'EAST_RESIDENTIAL':[391200,585510,391420,585730],
    'T14':[391100,585470,391175,585540],
    'T21':[390865,585530,390940,585620],
    'T24':[391000,585680,391070,585735],
    'T29':[390630,585500,390740,585610],
    'T10_BACKUP':[390920,585650,390954,585687]}
for name,bounds in frames.items():
    extent=QgsRectangle(*bounds)
    settings=QgsMapSettings();settings.setDestinationCrs(p.crs())
    settings.setLayers(([ground] if name=='T10_BACKUP' else [roofs])+ortho)
    settings.setExtent(extent);settings.setOutputSize(QSize(1450,1100));settings.setBackgroundColor(QColor('white'))
    job=QgsMapRendererParallelJob(settings);job.start();job.waitForFinished()
    assert job.renderedImage().save(str(out/(name+'.png')))
    bookmark=QgsBookmark();bookmark.setName('Auto regional / '+name);bookmark.setGroup('Auto regional / NEVALIDAT')
    bookmark.setExtent(QgsReferencedRectangle(extent,p.crs()));p.bookmarkManager().addBookmark(bookmark)
extent=QgsRectangle(*frames['REGIONAL_OVERVIEW']);extent.scale(1.02)
iface.setActiveLayer(roofs);iface.mapCanvas().setExtent(extent);iface.mapCanvas().refresh()
assert p.write()
verification={'project':p.fileName(),'saved':not p.isDirty(),'preexisting_dirty_view_preserved':was_dirty,'previous_layer_count':before_count,
    'layer_count':len(p.mapLayers()),'new_layers':[{'id':l.id(),'name':l.name(),'count':l.featureCount(),'source':l.source()} for l in new],
    'all_previous_vector_geometries_and_sources_unchanged':True,'previous_snapshot':before,
    'custom_render_order':root.hasCustomLayerOrder(),'roof_count':roofs.featureCount(),
    'frames':list(frames),'owner_verdict_changed':False}
(out/'verification.json').write_text(json.dumps(verification,indent=2),encoding='utf-8')
def capture():
    iface.mapCanvas().grab().save(str(out/'live_canvas.png'));iface.mainWindow().grab().save(str(out/'live_main_window.png'))
QTimer.singleShot(1800,capture)
print('REGIONAL_BASELINE_IN_SHARED_QGIS_NOT_OWNER_ACCEPTED')
