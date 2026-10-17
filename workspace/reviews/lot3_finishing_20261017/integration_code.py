import json,os
from pathlib import Path
from qgis.core import (QgsProject,QgsVectorLayer,QgsFillSymbol,QgsPalLayerSettings,QgsTextFormat,QgsVectorLayerSimpleLabeling,QgsRectangle,QgsMapSettings,QgsMapRendererParallelJob)
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtCore import QSize,QTimer
from qgis.utils import iface
p=QgsProject.instance()
assert Path(p.fileName()).resolve()==Path('C:/Users/lefpa/Downloads/QGIS-AI/workspace/reviews/body_recovery_20261013/inspectie_corectii.qgs').resolve()
assert not [l for l in p.mapLayers().values() if hasattr(l,'isEditable') and l.isEditable()]
root=p.layerTreeRoot()
assert root.findGroup('LOT3_FINISARE_T17_T18_20261017') is None,'Already integrated; inspect before rerunning'
new=root.insertGroup(0,'LOT3_FINISARE_T17_T18_20261017')
loaded=[]
for body in ['T17:C1','T17:C2','T18:C1']:
    layer=QgsVectorLayer('C:/Users/lefpa/Downloads/QGIS-AI/workspace/reviews/lot3_finishing_20261017/results/cadastral_review.gpkg'+'|layername=ROOF_HYPOTHESES',body+' - FINISARE NEVERIFICATA','ogr')
    assert layer.isValid()
    layer.setSubsetString('"body_id" = '+"'"+body+"'")
    assert layer.featureCount()==1
    layer.renderer().setSymbol(QgsFillSymbol.createSimple({'color':'0,0,0,0','outline_color':'#00ffff','outline_width':'0.6'}))
    pal=QgsPalLayerSettings();pal.fieldName='"body_id"';pal.isExpression=True
    text=QgsTextFormat();text.setSize(11);text.setColor(QColor('white'))
    buffer=text.buffer();buffer.setEnabled(True);buffer.setColor(QColor('black'));buffer.setSize(1);text.setBuffer(buffer)
    pal.setFormat(text);layer.setLabeling(QgsVectorLayerSimpleLabeling(pal));layer.setLabelsEnabled(True)
    p.addMapLayer(layer,False);new.addLayer(layer);loaded.append(layer)
raw=QgsVectorLayer('C:/Users/lefpa/Downloads/QGIS-AI/workspace/reviews/lot3_finishing_20261017/results/cadastral_review.gpkg'+'|layername=RAW_OPTICAL_MASKS','MASTI_BRUTE_FINISARE - mov','ogr')
assert raw.isValid()
raw.renderer().setSymbol(QgsFillSymbol.createSimple({'color':'0,0,0,0','outline_color':'#b24aff','outline_width':'0.4'}))
p.addMapLayer(raw,False);new.addLayer(raw);root.findLayer(raw.id()).setItemVisibilityChecked(False)
# Suppress only previous visual alternatives for these two cases. Keep other
# Lot3 features, accepted lots, sources and layer data intact.
previous_display=[]
for layer in list(p.mapLayers().values()):
    if layer in loaded or layer==raw:continue
    if isinstance(layer,QgsVectorLayer) and 'lot3' in layer.source().lower() and 'test_id' in layer.fields().names():
        before=layer.subsetString()
        clause='"test_id" NOT IN (\'T17\',\'T18\')'
        if clause not in before:
            layer.setSubsetString('('+before+') AND ('+clause+')' if before else clause)
            previous_display.append({'id':layer.id(),'name':layer.name(),'previous_subset':before,'new_subset':layer.subsetString()})
out=Path('C:/Users/lefpa/Downloads/QGIS-AI/workspace/reviews/lot3_finishing_20261017')
(out/'previous_display_filters.json').write_text(json.dumps(previous_display,indent=2),encoding='utf-8')
boxes={'T17':(390765,585430,390903,585553),'T18':(390585,585480,390674,585590)}
orthos=[l for l in p.mapLayers().values() if l.name().startswith('Cluj-')]
for name,coords in boxes.items():
    settings=QgsMapSettings();settings.setDestinationCrs(p.crs());settings.setLayers(loaded+orthos)
    settings.setExtent(QgsRectangle(*coords));settings.setOutputSize(QSize(1400,1100));settings.setBackgroundColor(QColor('white'))
    job=QgsMapRendererParallelJob(settings);job.start();job.waitForFinished();job.renderedImage().save(str(out/(name+'_shared_qgis.png')))
iface.mapCanvas().setExtent(QgsRectangle(*boxes['T17']));iface.mapCanvas().refresh()
assert p.write()
(out/'shared_qgis_after.json').write_text(json.dumps({'pid':os.getpid(),'project':p.fileName(),'new_layers':[{'id':l.id(),'name':l.name(),'count':l.featureCount()} for l in loaded],'total_layers':len(p.mapLayers())},indent=2),encoding='utf-8')
def capture_finishing_canvas():
    iface.mapCanvas().grab().save(str(out/'live_shared_canvas.png'))
QTimer.singleShot(2000,capture_finishing_canvas)
print('LOT3_FINISHING_SHARED_INTEGRATION_OK')
