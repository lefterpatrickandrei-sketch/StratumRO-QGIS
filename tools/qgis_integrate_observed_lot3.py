"""Execute inside the existing QGIS session through execute_code."""
from pathlib import Path
import json,shutil
from qgis.core import (QgsProject,QgsVectorLayer,QgsRasterLayer,QgsFillSymbol,QgsPalLayerSettings,
    QgsTextFormat,QgsVectorLayerSimpleLabeling,QgsRectangle,QgsMapSettings,QgsMapRendererParallelJob)
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtCore import QSize,QTimer
from qgis.utils import iface
ROOT=Path('C:/Users/lefpa/Downloads/QGIS-AI')
OUT=ROOT/'workspace/reviews/lot3_edge_audit_20261017'
PROJECT=ROOT/'workspace/reviews/body_recovery_20261013/inspectie_corectii.qgs'
p=QgsProject.instance();root=p.layerTreeRoot()
assert Path(p.fileName()).resolve()==PROJECT.resolve()
assert not [l for l in p.mapLayers().values() if hasattr(l,'isEditable') and l.isEditable()]
assert root.findGroup('LOT3_T18_MUCHII_OBSERVATE_20261017') is None
state={'file':p.fileName(),'dirty':p.isDirty(),'layers':[{'id':l.id(),'name':l.name(),'source':l.source(),'visible':root.findLayer(l.id()).isVisible()} for l in p.mapLayers().values()]}
(OUT/'qgis_before.json').write_text(json.dumps(state,indent=2))
shutil.copy2(PROJECT,OUT/'shared_project_before_edges.qgs.backup')
group=root.insertGroup(0,'LOT3_T18_MUCHII_OBSERVATE_20261017')
layers=[]
for ident,color in [('T18:C1','#00ffff'),('T18:C2','#ffb000')]:
    layer=QgsVectorLayer(str(OUT/'observed_edges.gpkg')+'|layername=ROOF_HYPOTHESES',ident+' - MUCHIE OBSERVATA / DE VERIFICAT','ogr')
    assert layer.isValid()
    layer.setSubsetString('"body_id" = '+"'"+ident+"'");assert layer.featureCount()==1
    layer.renderer().setSymbol(QgsFillSymbol.createSimple({'color':'0,0,0,0','outline_color':color,'outline_width':'0.6'}))
    pal=QgsPalLayerSettings();pal.fieldName='body_id'
    text=QgsTextFormat();text.setSize(11);text.setColor(QColor('white'))
    buf=text.buffer();buf.setEnabled(True);buf.setColor(QColor('black'));buf.setSize(1);text.setBuffer(buf)
    pal.setFormat(text);layer.setLabeling(QgsVectorLayerSimpleLabeling(pal));layer.setLabelsEnabled(True)
    p.addMapLayer(layer,False);group.addLayer(layer);layers.append(layer)
detail=QgsRasterLayer(str(OUT/'T18_detail_5cm.tif'),'T18 - DETALIU SID 5cm','gdal');assert detail.isValid()
p.addMapLayer(detail,False);group.addLayer(detail)
native=QgsRasterLayer(str(OUT/'T18_native_seam.tif'),'T18 - SURSA NATIVA / detaliu muchie','gdal');assert native.isValid()
p.addMapLayer(native,False);group.addLayer(native);root.findLayer(native.id()).setItemVisibilityChecked(False)
old_annex=root.findGroup('LOT3_T18_ANEXA_IPOTEZA_20261017')
if old_annex:old_annex.setItemVisibilityChecked(False)
for layer in list(p.mapLayers().values()):
    if layer.name().startswith('T18:C1 - FINISARE'):root.findLayer(layer.id()).setItemVisibilityChecked(False)
t17=[l for l in p.mapLayers().values() if l.name().startswith('T17:') and 'FINISARE NEVERIFICATA' in l.name()]
orthos=[l for l in p.mapLayers().values() if l.name().startswith('Cluj-')]
lot3=[l for l in p.mapLayers().values() if l.name()=='LOT3_V3_CORPURI_EXTRASE']
outlines=[l for l in p.mapLayers().values() if l.name()=='LOT3_V3_FERESTRE_SELECTIE']
frames={'T18_qgis_current':(QgsRectangle(390585,585480,390674,585590),layers+[detail]+orthos),
        'T17_qgis_checked':(QgsRectangle(390765,585430,390903,585553),t17+orthos),
        'Lot3_qgis_overview':(QgsRectangle(390570,585070,391330,585780),layers+t17+lot3+outlines+[detail]+orthos)}
for name,(extent,draw) in frames.items():
    settings=QgsMapSettings();settings.setDestinationCrs(p.crs());settings.setLayers(draw)
    settings.setExtent(extent);settings.setOutputSize(QSize(1440,1100));settings.setBackgroundColor(QColor('white'))
    job=QgsMapRendererParallelJob(settings);job.start();job.waitForFinished();assert job.renderedImage().save(str(OUT/(name+'.png')))
iface.mapCanvas().setExtent(frames['T18_qgis_current'][0]);iface.mapCanvas().refresh()
assert p.write()
(OUT/'qgis_after.json').write_text(json.dumps({'file':p.fileName(),'new_body_layers':[l.id() for l in layers],'features':sum(l.featureCount() for l in layers),'total_layers':len(p.mapLayers()),'T17_layers_retained':len(t17),'owner_verdict':'PENDING_OWNER_REVIEW'},indent=2))
def capture_observed_edges():iface.mapCanvas().grab().save(str(OUT/'live_current.png'))
QTimer.singleShot(2000,capture_observed_edges)
print('OBSERVED_LOT3_INTEGRATION_OK')
