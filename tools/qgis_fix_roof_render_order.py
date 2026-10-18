"""Actual shared-QGIS before/after proof for raster-obscured roof outlines."""
from pathlib import Path
import json,sys,hashlib,shutil
from qgis.core import QgsProject,QgsRectangle,QgsMapSettings,QgsMapRendererParallelJob
from qgis.PyQt.QtCore import QSize
from qgis.PyQt.QtGui import QColor
from qgis.utils import iface
ROOT=Path('C:/Users/lefpa/Downloads/QGIS-AI');sys.path.insert(0,str(ROOT))
from stratum_ro.qgis_render_order import vectors_above_rasters
p=QgsProject.instance();project=ROOT/'workspace/reviews/body_recovery_20261013/inspectie_corectii.qgs'
assert Path(p.fileName()).resolve()==project.resolve() and not p.isDirty()
assert not any(l.isEditable() for l in p.mapLayers().values() if hasattr(l,'isEditable'))
out=ROOT/'workspace/reviews/regional_roofs_20261017/render_order_fix';out.mkdir(exist_ok=False)
shutil.copy2(project,out/'shared_project_before.qgs.backup')
def geometry_snapshot():
    return {l.id():{'name':l.name(),'source':l.source(),'geometries':{
        str(f.id()):hashlib.sha256(bytes(f.geometry().asWkb())).hexdigest() for f in l.getFeatures()}}
        for l in p.mapLayers().values() if l.type()==0}
before=geometry_snapshot();old_order=list(iface.mapCanvas().layers())
frames={}
for l in p.mapLayers().values():
    if l.name() not in ['RECTIFICARI_T05_T06_T07_T10','ACOPERISURI_SIMPLE','LOT3 - 20 ipoteze / NECESITA VERDICT']:continue
    for f in l.getFeatures():
        field='body_id' if 'body_id' in f.fields().names() else 'id'
        value=str(f[field])
        if value in ['T07:A1','REF_TIER1_021:B00010','T18:C1']:
            extent=QgsRectangle(f.geometry().boundingBox());extent.scale(1.30);frames[value.replace(':','_')]=extent
assert len(frames)>=2
def render(order,phase):
    for name,extent in frames.items():
        settings=QgsMapSettings();settings.setDestinationCrs(p.crs());settings.setLayers(order)
        settings.setExtent(extent);settings.setOutputSize(QSize(1300,1000));settings.setBackgroundColor(QColor('white'))
        job=QgsMapRendererParallelJob(settings);job.start();job.waitForFinished()
        assert job.renderedImage().save(str(out/(name+'_'+phase+'.png')))
render(old_order,'before')
order=vectors_above_rasters(p)
visible={l.id() for l in old_order};new_order=[p.mapLayer(i) for i in order if i in visible]
render(new_order,'after')
after=geometry_snapshot();assert before==after
iface.mapCanvas().refresh();assert p.write()
report={'cause':'Nested orthophoto detail rasters rendered ABOVE earlier roof vectors, obscuring parts of closed polygons.',
    'before_custom_order':False,'after_custom_order':p.layerTreeRoot().hasCustomLayerOrder(),
    'before_draw_order':[l.id() for l in old_order],'after_draw_order':[l.id() for l in new_order],
    'all_previous_vector_geometry_sources_unchanged':before==after,'snapshot':before,
    'saved':not p.isDirty(),'project':p.fileName(),'frames':list(frames)}
(out/'verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('ROOF_RENDER_ORDER_FIXED_WITH_UNCHANGED_GEOMETRY')
