"""Execute through the live QGIS bridge after review generation completes."""
from pathlib import Path
import json,shutil,sys
from qgis.core import QgsProject,QgsVectorLayer,QgsFillSymbol,QgsRectangle
from qgis.utils import iface
root=Path('C:/Users/lefpa/Downloads/QGIS-AI');sys.path.insert(0,str(root))
from stratum_ro.qgis_render_order import vectors_above_rasters
out=root/'workspace/reviews/option_b_simple_variations_20261018_v2'
project=QgsProject.instance();tree=project.layerTreeRoot()
assert Path(project.fileName()).resolve()==(root/'workspace/reviews/body_recovery_20261013/inspectie_corectii.qgs').resolve()
assert not any(l.isEditable() for l in project.mapLayers().values() if hasattr(l,'isEditable'))
name='B_FORME_SIMPLE_SI_VARIATII_20261018'
assert tree.findGroup(name) is None
shutil.copy2(project.fileName(),out/'project_before_simple_shapes.qgs')
old_ids=set(project.mapLayers());group=tree.insertGroup(0,name);loaded=[]
for layername,title,color,visible in [
    ('B_SIMPLE','B - FORME SIMPLE / necesita verificare','0,230,255,255',True),
    ('B_VARIATIONS','B - ALTERNATIVE / eligibile si respinse','245,75,210,255',False),
    ('B_PREVIOUS','B - ETAPA ANTERIOARA','255,165,0,255',False)]:
    layer=QgsVectorLayer(str(out/'simple_variations.gpkg')+'|layername='+layername,title,'ogr')
    assert layer.isValid()
    layer.renderer().setSymbol(QgsFillSymbol.createSimple({'color':'0,0,0,0','outline_color':color,'outline_width':'.5'}))
    project.addMapLayer(layer,False);node=group.addLayer(layer);node.setItemVisibilityChecked(visible);loaded.append(layer)
old_group=tree.findGroup('B_RAFINARE_20261018 - ETAPE SI REVIZIE')
if old_group:old_group.setItemVisibilityChecked(False)
existing_order=list(tree.customLayerOrder()) if tree.hasCustomLayerOrder() else list(iface.mapCanvas().layers())
tree.setHasCustomLayerOrder(True)
tree.setCustomLayerOrder(loaded+[l for l in existing_order if l.id() not in {x.id() for x in loaded}])
vectors_above_rasters(project)
target=next((f for f in loaded[0].getFeatures() if f['candidate_id']=='OPT_B_046:C1'),None)
if target:
    extent=QgsRectangle(target.geometry().boundingBox());extent.scale(2.2);iface.mapCanvas().setExtent(extent)
iface.mapCanvas().refresh()
assert old_ids.issubset(set(project.mapLayers()))
assert project.write()
receipt=dict(project=project.fileName(),old_layer_count=len(old_ids),added_layer_count=3,
    saved=True,dirty=project.isDirty(),count=loaded[0].featureCount(),variant_count=loaded[1].featureCount(),
    invalid_layers=[l.name() for l in project.mapLayers().values() if not l.isValid()])
(out/'qgis_integration.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print(receipt)
