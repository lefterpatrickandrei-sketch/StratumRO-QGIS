"""Update the existing shared review layer without overwriting a loaded GeoPackage."""
from pathlib import Path
import json,shutil
from qgis.core import QgsProject,QgsRectangle,QgsMapSettings,QgsMapRendererParallelJob
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtCore import QSize,QTimer
from qgis.utils import iface
ROOT=Path('C:/Users/lefpa/Downloads/QGIS-AI');OUT=ROOT/'workspace/reviews/lot3_repairs_20261017';SEL=OUT/'selected_v3'
p=QgsProject.instance();PROJECT=ROOT/'workspace/reviews/body_recovery_20261013/inspectie_corectii.qgs'
assert Path(p.fileName()).resolve()==PROJECT.resolve()
assert not any(l.isEditable() for l in p.mapLayers().values() if hasattr(l,'isEditable'))
state=json.loads((OUT/'selected_v2/qgis_after.json').read_text());roofs=p.mapLayer(state['layer_id'])
assert roofs and roofs.isValid() and roofs.source()==state['source']
assert not (SEL/'qgis_after.json').exists()
shutil.copy2(PROJECT,SEL/'shared_project_before_update.qgs.backup')
(SEL/'qgis_before.json').write_text(json.dumps({'file':p.fileName(),'dirty':p.isDirty(),'source':roofs.source(),'layer_id':roofs.id()},indent=2))
renderer=roofs.renderer().clone();labeling=roofs.labeling().clone()
expected=len(json.loads((SEL/'selection_report.json').read_text())['bodies'])
roofs.setDataSource(str(SEL/'lot3_repaired.gpkg')+'|layername=REPAIRED_ROOF_CANDIDATES',f'LOT3 - {expected} ipoteze / NECESITA VERDICT','ogr')
assert roofs.isValid() and roofs.featureCount()==expected
roofs.setRenderer(renderer);roofs.setLabeling(labeling);roofs.setLabelsEnabled(True);roofs.triggerRepaint()
native=[l for l in p.mapLayers().values() if l.name().endswith('_5cm') and '/lot3_repairs_20261017/' in l.source().replace('\\','/')]
orthos=[l for l in p.mapLayers().values() if l.name().startswith('Cluj-')]
assert len(native)==9
frames=json.loads((SEL/'case_frames.json').read_text())
for name,bounds in {**frames,'LOT3_OVERVIEW':[390570,585070,391330,585780]}.items():
 settings=QgsMapSettings();settings.setDestinationCrs(p.crs());settings.setLayers([roofs]+native+orthos)
 settings.setExtent(QgsRectangle(*bounds));settings.setOutputSize(QSize(1440,1100));settings.setBackgroundColor(QColor('white'))
 job=QgsMapRendererParallelJob(settings);job.start();job.waitForFinished();assert job.renderedImage().save(str(SEL/(name+'_qgis.png')))
iface.mapCanvas().setExtent(QgsRectangle(*frames['T19']));iface.mapCanvas().refresh();assert p.write()
(SEL/'qgis_after.json').write_text(json.dumps({'file':p.fileName(),'layer_id':roofs.id(),'source':roofs.source(),'feature_count':roofs.featureCount(),'native_detail_layers':len(native),'total_layers':len(p.mapLayers()),'owner_verdict':'PENDING_OWNER_REVIEW'},indent=2))
def capture_updated():iface.mapCanvas().grab().save(str(SEL/'live_qgis.png'))
QTimer.singleShot(1500,capture_updated)
print('LOT3_SHARED_QGIS_UPDATED_OK')
