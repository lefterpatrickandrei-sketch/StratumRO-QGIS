from pathlib import Path
import json
from qgis.core import QgsProject,QgsVectorLayer,QgsFillSymbol,QgsPalLayerSettings,QgsTextFormat,QgsVectorLayerSimpleLabeling,QgsRectangle,QgsMapSettings,QgsMapRendererParallelJob
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtCore import QSize,QTimer
from qgis.utils import iface
p=QgsProject.instance();root=p.layerTreeRoot()
assert Path(p.fileName()).resolve()==Path('C:\\Users\\lefpa\\Downloads\\QGIS-AI\\workspace\\reviews\\body_recovery_20261013\\inspectie_corectii.qgs').resolve()
assert not [l for l in p.mapLayers().values() if hasattr(l,'isEditable') and l.isEditable()]
assert root.findGroup('LOT3_T18_ANEXA_IPOTEZA_20261017') is None
group=root.insertGroup(0,'LOT3_T18_ANEXA_IPOTEZA_20261017')
annex=QgsVectorLayer('C:/Users/lefpa/Downloads/QGIS-AI/workspace/reviews/lot3_continuation_20261017/annex_review_final.gpkg'+'|layername=CURRENT_ROOFS_AND_ANNEX_HYPOTHESIS','T18:C2 - IPOTEZA ANEXA / MUCHIE DE VERIFICAT','ogr')
assert annex.isValid();annex.setSubsetString('"body_id" = \'T18:C2\'');assert annex.featureCount()==1
annex.renderer().setSymbol(QgsFillSymbol.createSimple({'color':'0,0,0,0','outline_color':'#ffb000','outline_width':'0.7'}))
pal=QgsPalLayerSettings();pal.fieldName='body_id'
text=QgsTextFormat();text.setSize(12);text.setColor(QColor('white'))
buf=text.buffer();buf.setEnabled(True);buf.setColor(QColor('black'));buf.setSize(1);text.setBuffer(buf)
pal.setFormat(text);annex.setLabeling(QgsVectorLayerSimpleLabeling(pal));annex.setLabelsEnabled(True)
p.addMapLayer(annex,False);group.addLayer(annex)
conflict=QgsVectorLayer('C:/Users/lefpa/Downloads/QGIS-AI/workspace/reviews/lot3_continuation_20261017/annex_review_final.gpkg'+'|layername=BOUNDARY_CONFLICT','T18 - CONFLICT MUCHIE 5.8 m2 / NEVERIFICAT','ogr')
assert conflict.isValid();assert conflict.featureCount()==1
conflict.renderer().setSymbol(QgsFillSymbol.createSimple({'color':'255,40,70,150','outline_color':'#ff1744','outline_width':'0.45'}))
p.addMapLayer(conflict,False);group.insertLayer(0,conflict)
current=[l for l in p.mapLayers().values() if 'FINISARE NEVERIFICATA' in l.name()]
orthos=[l for l in p.mapLayers().values() if l.name().startswith('Cluj-')]
out=Path('C:\\Users\\lefpa\\Downloads\\QGIS-AI\\workspace\\reviews\\lot3_continuation_20261017')
settings=QgsMapSettings();settings.setDestinationCrs(p.crs());settings.setLayers([conflict,annex]+current+orthos)
settings.setExtent(QgsRectangle(390585,585480,390674,585590));settings.setOutputSize(QSize(1400,1100));settings.setBackgroundColor(QColor('white'))
job=QgsMapRendererParallelJob(settings);job.start();job.waitForFinished();job.renderedImage().save(str(out/'T18_shared_annex_qgis.png'))
iface.mapCanvas().setExtent(QgsRectangle(390585,585480,390674,585590));iface.mapCanvas().refresh()
assert p.write()
(out/'shared_qgis_after.json').write_text(json.dumps({'file':p.fileName(),'new_layers':[annex.id(),conflict.id()],'annex_count':annex.featureCount(),'conflict_count':conflict.featureCount(),'previous_finishing_layers_preserved':len(current),'total_layers':len(p.mapLayers())},indent=2))
def capture_annex():iface.mapCanvas().grab().save(str(out/'live_shared_annex.png'))
QTimer.singleShot(2000,capture_annex)
print('ANNEX_SHARED_INTEGRATION_OK')
