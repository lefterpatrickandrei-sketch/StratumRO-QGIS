"""Execute through the live QGIS bridge after review generation completes."""
from pathlib import Path
import json,shutil,sys
from qgis.core import QgsProject,QgsVectorLayer,QgsFillSymbol,QgsRectangle,QgsPalLayerSettings,QgsVectorLayerSimpleLabeling,QgsTextFormat
from qgis.utils import iface
root=Path('C:/Users/lefpa/Downloads/QGIS-AI');sys.path.insert(0,str(root))
from stratum_ro.qgis_render_order import vectors_above_rasters
def integrate_simple_review(output_directory=None,group_name=None,repair=False):
    from stratum_ro.qgis_render_order import vectors_above_rasters
    out=Path(output_directory) if output_directory else root/'workspace/reviews/option_b_simple_variations_20261018_v2'
    project=QgsProject.instance();tree=project.layerTreeRoot()
    assert Path(project.fileName()).resolve()==(root/'workspace/reviews/body_recovery_20261013/inspectie_corectii.qgs').resolve()
    assert not project.isDirty(), 'Unsaved project edits must be accounted for first'
    assert not any(l.isEditable() for l in project.mapLayers().values() if hasattr(l,'isEditable'))
    name=group_name or 'B_FORME_SIMPLE_SI_VARIATII_20261018'
    assert tree.findGroup(name) is None
    shutil.copy2(project.fileName(),out/'project_before_integration.qgs')
    old_ids=set(project.mapLayers());loaded=[]
    specs=[('B_ROOF_PROPOSALS','B - acoperisuri in revizie / corectii locale','0,230,255,255',True),
           ('B_DIAGNOSTIC_ONLY','B - false sau incomplete / necesita recuperare','255,140,0,255',False),
           ('B_BEFORE_REPAIR','B - inainte de corectii','210,70,200,255',False)] if repair else [
           ('B_SIMPLE','B - FORME SIMPLE / necesita verificare','0,230,255,255',True),
           ('B_VARIATIONS','B - ALTERNATIVE / eligibile si respinse','245,75,210,255',False),
           ('B_PREVIOUS','B - ETAPA ANTERIOARA','255,165,0,255',False)]
    # Validate all sources before changing the layer tree.
    for layername,title,color,visible in specs:
        layer=QgsVectorLayer(str(out/'simple_variations.gpkg')+'|layername='+layername,title,'ogr')
        assert layer.isValid() and layer.crs().authid()=='EPSG:3844'
        layer.renderer().setSymbol(QgsFillSymbol.createSimple({'color':'0,0,0,0','outline_color':color,'outline_width':'.5'}))
        loaded.append(layer)
    group=tree.insertGroup(0,name)
    for layer,spec in zip(loaded,specs):
        project.addMapLayer(layer,False);node=group.addLayer(layer);node.setItemVisibilityChecked(spec[3])
    if repair:
        pal=QgsPalLayerSettings();pal.fieldName='candidate_id';fmt=QgsTextFormat();fmt.setSize(10);pal.setFormat(fmt)
        loaded[0].setLabeling(QgsVectorLayerSimpleLabeling(pal));loaded[0].setLabelsEnabled(True)
    for old_name in ['B_RAFINARE_20261018 - ETAPE SI REVIZIE','B_FORME_SIMPLE_SI_VARIATII_20261018']:
        old_group=tree.findGroup(old_name)
        if old_group and old_group!=group:old_group.setItemVisibilityChecked(False)
    previous_vector_visibility={}
    if repair:
        for old_id in old_ids:
            old_layer=project.mapLayer(old_id);old_node=tree.findLayer(old_id)
            if isinstance(old_layer,QgsVectorLayer) and old_node:
                previous_vector_visibility[old_id]=old_node.itemVisibilityChecked()
                old_node.setItemVisibilityChecked(False)
    existing_order=list(tree.customLayerOrder()) if tree.hasCustomLayerOrder() else list(iface.mapCanvas().layers())
    tree.setHasCustomLayerOrder(True)
    tree.setCustomLayerOrder(loaded+[l for l in existing_order if l.id() not in {x.id() for x in loaded}])
    vectors_above_rasters(project)
    target=next((f for f in loaded[0].getFeatures() if f['candidate_id']==('OPT_B_049:C1' if repair else 'OPT_B_046:C1')),None)
    if target:
        extent=QgsRectangle(target.geometry().boundingBox());extent.scale(1.5);iface.mapCanvas().setExtent(extent)
    iface.mapCanvas().refresh()
    assert old_ids.issubset(set(project.mapLayers()))
    assert project.write()
    shutil.copy2(project.fileName(),out/'shared_project_after.qgs')
    receipt=dict(project=project.fileName(),old_layer_count=len(old_ids),added_layer_count=len(loaded),
        saved=True,dirty=project.isDirty(),previous_vector_visibility=previous_vector_visibility,layers=[dict(name=l.name(),count=l.featureCount(),id=l.id()) for l in loaded],
        invalid_layers=[l.name() for l in project.mapLayers().values() if not l.isValid()])
    (out/'qgis_integration.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    print(receipt)
    return receipt

if __name__=='__main__':integrate_simple_review()
