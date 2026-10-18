"""Execute in QGIS: add stages to the common project, preserve originals.

Set RUN_DIRECTORY. Saves the current live project after a byte-exact backup of
its previous disk version; never reloads it or edits source feature geometry.
"""
import hashlib,json,shutil
from pathlib import Path
from qgis.core import (QgsProject,QgsVectorLayer,QgsFillSymbol,QgsRuleBasedRenderer,QgsRectangle,
                       QgsBookmark,QgsReferencedRectangle)
from qgis.utils import iface

root=Path('C:/Users/lefpa/Downloads/QGIS-AI');out=root/RUN_DIRECTORY
p=QgsProject.instance();original=Path(p.fileName())
expected=root/'workspace/reviews/body_recovery_20261013/inspectie_corectii.qgs'
if original.resolve()!=expected.resolve():raise ValueError('Different main project open; no changes applied')
if any(l.isEditable() for l in p.mapLayers().values() if hasattr(l,'isEditable')):
    raise ValueError('Editable layers present; preserve edits before project update')
name='B_RAFINARE_20261018 - ETAPE SI REVIZIE'
if p.layerTreeRoot().findGroup(name):raise ValueError('Stage group already exists; no duplicate update')
state={'project':str(original),'dirty_before':p.isDirty(),
       'canvas_layer_ids_before':[l.id() for l in iface.mapCanvas().layers()],
       'old_b_visibility':{}}
backup=out/'main_project_before_stages.qgs'
shutil.copy2(original,backup)
state['disk_backup_sha256']=hashlib.sha256(backup.read_bytes()).hexdigest()
group=p.layerTreeRoot().insertGroup(0,name)
gpkg=out/'refinement.gpkg'
specs=[('B4_FINAL_REVIEW','6. PROPUNERI - cyan simplu / portocaliu revizie',True,'0,220,255,255'),
       ('UNRESOLVED_REVIEW','QA - cazuri nerezolvate (nu livrabile finale)',False,'255,130,0,255'),
       ('B4_RETRY_OBSERVATIONS','5. SAM2 - incercari, inclusiv nepromovate',False,'255,0,200,255'),
       ('SAM2_ALL_ATTEMPTS','SAM2 - toate mastile, scoruri si motive de respingere',False,'255,0,200,255'),
       ('B3_BEFORE_RETRY_QA','4. QA inainte de SAM2',False,'0,220,255,255'),
       ('B3_SIMPLE_FIT','3. Simplificare cu garduri',False,'0,220,255,255'),
       ('B2_DEDUPLICATED','2. Observatii dupa deduplicare',False,'255,210,0,255'),
       ('B1_OBSERVATIONS','1. Observatii optice originale',False,'255,255,255,255'),
       ('B0_BASELINE','0. B initial - 216 propuneri',False,'255,160,0,255'),
       ('B0_REJECTED_RECALL_QUEUE','Recall - cei 71 respinsi anterior, neverificati',False,'180,180,180,255'),
       ('EXISTING_OTHER_LOTS','Context - alte loturi (copii pentru QA)',False,'100,255,100,255')]
added=[]
for layer,title,visible,color in specs:
    v=QgsVectorLayer(str(gpkg)+'|layername='+layer,title,'ogr')
    if not v.isValid():raise ValueError('Missing stage layer: '+layer)
    symbol=QgsFillSymbol.createSimple({'color':'0,0,0,0','outline_color':color,'outline_width':'.55'})
    if layer=='B4_FINAL_REVIEW':
        renderer=QgsRuleBasedRenderer(symbol);node=renderer.rootRule();node.removeChildAt(0)
        for label,expr,col in [('Forma simpla - ipoteza, nu acceptare','"qa_status" = \'SIMPLE_ROOF_HYPOTHESIS\'','0,220,255,255'),
                               ('Necesita revizie','"qa_status" <> \'SIMPLE_ROOF_HYPOTHESIS\'','255,140,0,255')]:
            s=QgsFillSymbol.createSimple({'color':'0,0,0,0','outline_color':col,'outline_width':'.55'})
            rule=QgsRuleBasedRenderer.Rule(s);rule.setFilterExpression(expr);rule.setLabel(label);node.appendChild(rule)
        v.setRenderer(renderer)
    else:v.renderer().setSymbol(symbol)
    v.setCustomProperty('stratumro/owner_verdict','PENDING_OWNER_REVIEW')
    p.addMapLayer(v,False);n=group.addLayer(v);n.setItemVisibilityChecked(visible)
    added.append(dict(layer_id=v.id(),source_layer=layer,count=v.featureCount(),visible=visible))
    if layer=='B4_FINAL_REVIEW':final=v
for l in p.mapLayers().values():
    if l.name() in ['OPT_B - Cladiri Validate nDSM (Portocaliu)','OPT_B - Amprenta Sol -0.40m (Verde)']:
        n=p.layerTreeRoot().findLayer(l.id());state['old_b_visibility'][l.id()]=n.itemVisibilityChecked()
        n.setItemVisibilityChecked(False)
for ident in ['OPT_B_006:C1','OPT_B_046:C1','OPT_B_080:C1','OPT_B_120:C1','OPT_B_154:C1','OPT_B_169:C1','OPT_B_201:C1']:
    feat=next((f for f in final.getFeatures() if f['candidate_id']==ident),None)
    if feat:
        b=QgsBookmark();b.setName('B rafinare '+ident);b.setGroup('StratumRO - B etape')
        extent=QgsRectangle(feat.geometry().boundingBox());extent.scale(1.8)
        b.setExtent(QgsReferencedRectangle(extent,final.crs()));p.bookmarkManager().addBookmark(b)
from stratum_ro.qgis_render_order import vectors_above_rasters
vectors_above_rasters(p)
new_ids={r['layer_id'] for r in added}
p.layerTreeRoot().setCustomLayerOrder([p.mapLayer(r['layer_id']) for r in added]+
    [l for l in p.layerTreeRoot().layerOrder() if l.id() not in new_ids])
iface.mapCanvas().setExtent(final.extent());iface.mapCanvas().refresh()
if not p.write():raise RuntimeError('Project save failed; disk backup retained')
state.update(added_layers=added,project_saved=True,dirty_after=p.isDirty(),
             project_after_sha256=hashlib.sha256(original.read_bytes()).hexdigest())
(out/'qgis_integration.json').write_text(json.dumps(state,indent=2))
iface.mapCanvas().saveAsImage(str(out/'main_qgis_after.png'))
print(json.dumps({'project_saved':True,'added_layers':len(added),'final_count':final.featureCount(),'dirty_after':p.isDirty()}))
