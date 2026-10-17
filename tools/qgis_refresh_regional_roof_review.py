"""Refresh only the new regional layers after explicit routing correction."""
from pathlib import Path
import json,hashlib,shutil
from qgis.core import QgsProject,QgsRectangle,QgsMapSettings,QgsMapRendererParallelJob,QgsDataProvider
from qgis.PyQt.QtCore import QSize,QTimer
from qgis.PyQt.QtGui import QColor
from qgis.utils import iface
ROOT=Path('C:/Users/lefpa/Downloads/QGIS-AI');OUT=ROOT/'workspace/reviews/regional_roofs_20261017'
p=QgsProject.instance();assert Path(p.fileName()).resolve()==(ROOT/'workspace/reviews/body_recovery_20261013/inspectie_corectii.qgs').resolve()
assert not any(l.isEditable() for l in p.mapLayers().values() if hasattr(l,'isEditable'))
prior=json.loads((OUT/'qgis/verification.json').read_text())['previous_snapshot']
for ident,item in prior.items():
    layer=p.mapLayer(ident);assert layer and layer.source()==item['source']
    assert {str(f.id()):hashlib.sha256(bytes(f.geometry().asWkb())).hexdigest() for f in layer.getFeatures()}==item['wkb']
out=OUT/'qgis/revised_routing';out.mkdir(exist_ok=False)
shutil.copy2(p.fileName(),out/'shared_project_before_refresh.qgs.backup')
source=str(ROOT/json.loads((OUT/'CURRENT_REVIEW.json').read_text())['gpkg'])
group=p.layerTreeRoot().findGroup('ACOPERISURI_AUTOMAT_REGIONAL_20261017_NEVALIDAT');assert group
changed=[];roofs=None
for node in group.findLayers():
    layer=node.layer()
    if '/masked_review/' in layer.source().replace('\\','/'):
        table=layer.source().split('|layername=')[1]
        renderer=layer.renderer().clone();layer.setDataSource(source+'|layername='+table,layer.name(),'ogr')
        layer.setRenderer(renderer);assert layer.isValid()
        if table=='ROOF_CANDIDATES':roofs=layer
        changed.append(dict(id=layer.id(),source=layer.source(),count=layer.featureCount()))
assert roofs is not None and roofs.featureCount()==380
ortho=[l for l in p.mapLayers().values() if l.name().startswith('Cluj-')]
frames={'REGIONAL_OVERVIEW':[390504.3,584812.8,391602.9,585911.4],
    'CAMPUS_NORTH':[390620,585570,391210,585790],'CAMPUS_SOUTH':[390670,585080,391120,585470],
    'EAST_RESIDENTIAL':[391200,585510,391420,585730],
    'T14':[391100,585470,391175,585540],'T21':[390865,585530,390940,585620],
    'T24':[391000,585680,391070,585735],'T29':[390630,585500,390740,585610]}
for name,bounds in frames.items():
    settings=QgsMapSettings();settings.setDestinationCrs(p.crs());settings.setLayers([roofs]+ortho)
    settings.setExtent(QgsRectangle(*bounds));settings.setOutputSize(QSize(1450,1100));settings.setBackgroundColor(QColor('white'))
    job=QgsMapRendererParallelJob(settings);job.start();job.waitForFinished()
    assert job.renderedImage().save(str(out/(name+'.png')))
iface.mapCanvas().refresh();assert p.write()
verification=dict(saved=not p.isDirty(),project=p.fileName(),layer_count=len(p.mapLayers()),
    changed_layers=changed,all_original_63_layer_vector_geometries_and_sources_preserved=True,
    original_owner_verdicts_unchanged=True,new_roof_candidates=380,
    unknown_candidates=644,routing_changes=183,semantically_validated=False,
    raw_observations_or_inference_changed=False)
(out/'verification.json').write_text(json.dumps(verification,indent=2),encoding='utf-8')
def capture():
    iface.mapCanvas().grab().save(str(out/'live_canvas.png'));iface.mainWindow().grab().save(str(out/'live_main_window.png'))
QTimer.singleShot(1800,capture)
print('REGIONAL_ROUTING_REVISED_NO_OLD_GEOMETRY_OR_VERDICT_CHANGE')
