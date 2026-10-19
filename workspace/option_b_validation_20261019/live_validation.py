"""Run through the existing QGIS bridge. Read-only geometry audit and purple B styling."""
from pathlib import Path
import json, math, hashlib, shutil
from qgis.core import (QgsProject,QgsVectorLayer,QgsFillSymbol,QgsSpatialIndex,
    QgsSingleSymbolRenderer,QgsGeometry,QgsRectangle,QgsMapSettings,QgsMapRendererParallelJob,QgsMapLayerType)
from qgis.PyQt.QtCore import QSize
from qgis.utils import iface

ROOT=Path('C:/Users/lefpa/Downloads/QGIS-AI')
OUT=ROOT/'workspace/option_b_validation_20261019'

def fingerprint(layer):
    return hashlib.sha256(b''.join(bytes(f.geometry().asWkb()) for f in layer.getFeatures())).hexdigest()

def audit(layer):
    records={};features=list(layer.getFeatures());index=QgsSpatialIndex(layer.getFeatures());byfid={f.id():f for f in features}
    for f in features:
        g=f.geometry();polys=g.asMultiPolygon() if g.isMultipart() else [g.asPolygon()]
        edges=[];angles=[];holes=0;nodes=0
        for rings in polys:
            holes+=max(0,len(rings)-1)
            for ring in rings:
                nodes+=max(0,len(ring)-1)
                for i in range(len(ring)-1):
                    a,b,c=ring[i-1 if i else len(ring)-2],ring[i],ring[i+1]
                    u=(a.x()-b.x(),a.y()-b.y());v=(c.x()-b.x(),c.y()-b.y())
                    lu=math.hypot(*u);lv=math.hypot(*v);edges.append(lv)
                    if lu*lv:angles.append(math.degrees(math.acos(max(-1,min(1,(u[0]*v[0]+u[1]*v[1])/(lu*lv))))))
        ident=str(f['candidate_id'])
        records[ident]=dict(area_m2=g.area(),geos_valid=g.isGeosValid(),qgis_errors=[e.what() for e in g.validateGeometry()],
            nodes=nodes,holes=holes,min_edge_m=min(edges,default=0),min_angle_deg=min(angles,default=180))
    overlaps=[]
    for f in features:
        g=f.geometry()
        for fid in index.intersects(g.boundingBox()):
            if fid<=f.id():continue
            other=byfid[fid];h=other.geometry();inter=g.intersection(h);area=inter.area()
            if area>.05:
                overlaps.append(dict(a=str(f['candidate_id']),b=str(other['candidate_id']),area_m2=area,
                    iou=area/(g.area()+h.area()-area),containment=area/min(g.area(),h.area())))
    return dict(count=len(features),crs=layer.crs().authid(),source=layer.source(),geometry_sha256=fingerprint(layer),
        invalid_geos=sum(not r['geos_valid'] for r in records.values()),qgis_error_cases=sum(bool(r['qgis_errors']) for r in records.values()),
        short_edge_cases=sum(r['min_edge_m']<1 for r in records.values()),acute_angle_cases=sum(r['min_angle_deg']<40 for r in records.values()),
        more_than_12_node_cases=sum(r['nodes']>12 for r in records.values()),interior_ring_cases=sum(r['holes']>0 for r in records.values()),
        records=records,overlaps=sorted(overlaps,key=lambda x:-x['area_m2']))

def main():
    p=QgsProject.instance();tree=p.layerTreeRoot()
    assert Path(p.fileName()).resolve()==(ROOT/'workspace/reviews/body_recovery_20261013/inspectie_corectii.qgs').resolve()
    assert not any(l.isEditable() for l in p.mapLayers().values() if hasattr(l,'isEditable'))
    OUT.mkdir(exist_ok=True);(OUT/'styles').mkdir(exist_ok=True);(OUT/'qgis_cases').mkdir(exist_ok=True)
    if not (OUT/'project_disk_before.qgs').exists():shutil.copy2(p.fileName(),OUT/'project_disk_before.qgs')
    # Preserve current unsaved project presentation before styling; no edit buffers active.
    assert p.write()
    if not (OUT/'project_before_style.qgs').exists():shutil.copy2(p.fileName(),OUT/'project_before_style.qgs')
    visibility={l.id():tree.findLayer(l.id()).isVisible() for l in p.mapLayers().values() if tree.findLayer(l.id())}
    colors=[]
    for l in p.mapLayers().values():
        if not isinstance(l,QgsVectorLayer):continue
        node=tree.findLayer(l.id());ancestor=node.parent() if node else None;belongs=False
        while ancestor:
            belongs|=ancestor.name().startswith(('B_FORME_','B_RAFINARE_','B_CORECTII_','OPTIUNEA_B_'))
            ancestor=ancestor.parent()
        if not belongs:continue
        before=fingerprint(l)
        l.setRenderer(QgsSingleSymbolRenderer(QgsFillSymbol.createSimple({'color':'0,0,0,0','outline_color':'176,48,224,255','outline_width':'.45'})))
        l.triggerRepaint();l.saveNamedStyle(str(OUT/'styles'/(l.id()+'.qml')))
        assert before==fingerprint(l)
        colors.append(dict(id=l.id(),name=l.name(),visible=node.isVisible(),geometry_sha256=before,color='#b030e0'))
    assert all(tree.findLayer(ident).isVisible()==v for ident,v in visibility.items())
    old=next(l for l in p.mapLayers().values() if l.name()=='B - FORME SIMPLE / necesita verificare')
    newpath=ROOT/'workspace/reviews/option_b_repair_20261019_v2/simple_variations.gpkg'
    new=QgsVectorLayer(str(newpath)+'|layername=B_SIMPLE','new B all 216','ogr')
    proposals=QgsVectorLayer(str(newpath)+'|layername=B_ROOF_PROPOSALS','new B proposals 152','ogr')
    assert new.isValid() and proposals.isValid()
    result={'engine':'live QGIS GEOS + QGIS internal validation; projected EPSG:3844 metres',
        'flags_are_development_diagnostics_not_legal_tolerances':True,'old_visible_B':audit(old),'new_all_B':audit(new),
        'new_proposals_only':audit(proposals),'style_changes':colors,'layer_visibility_unchanged':True}
    oldby={str(f['candidate_id']):f.geometry() for f in old.getFeatures()};newby={str(f['candidate_id']):f.geometry() for f in new.getFeatures()}
    assert set(oldby)==set(newby)
    result['changed_ids']=[i for i in oldby if not oldby[i].isGeosEqual(newby[i])]
    result['comparisons']={i:dict(old_nodes=result['old_visible_B']['records'][i]['nodes'],new_nodes=result['new_all_B']['records'][i]['nodes'],symmetric_difference_m2=oldby[i].symDifference(newby[i]).area(),boundary_hausdorff_m=oldby[i].hausdorffDistance(newby[i])) for i in oldby}
    # Actual QGIS renderings with shared ortho rasters; no canvas layer toggles.
    rasters=[l for l in iface.mapCanvas().layers() if l.type()==QgsMapLayerType.RasterLayer]
    for n in [17,35,39,43,49,68,108,126,144,152,187,210]:
        ident=f'OPT_B_{n:03d}:C1';rect=QgsRectangle(oldby[ident].boundingBox());rect.combineExtentWith(newby[ident].boundingBox());rect.scale(1.55)
        for tag,source in [('old',old),('new',new)]:
            clone=source.clone();clone.setLabelsEnabled(False)
            clone.renderer().setSymbol(QgsFillSymbol.createSimple({'color':'0,0,0,0','outline_color':'176,48,224,255','outline_width':'.55'}))
            clone.setSubsetString('"candidate_id" = \''+ident+'\'')
            settings=QgsMapSettings();settings.setDestinationCrs(p.crs());settings.setOutputSize(QSize(850,700));settings.setExtent(rect);settings.setLayers([clone]+rasters)
            job=QgsMapRendererParallelJob(settings);job.start();job.waitForFinished();assert job.renderedImage().save(str(OUT/'qgis_cases'/f'{n:03d}_{tag}.png'))
    iface.mapCanvas().refresh();assert p.write();shutil.copy2(p.fileName(),OUT/'project_after_style.qgs')
    (OUT/'live_qgis_validation.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({k:{'count':result[k]['count'],'invalid_geos':result[k]['invalid_geos'],'qgis_error_cases':result[k]['qgis_error_cases'],'overlaps':len(result[k]['overlaps']),'short_edges':result[k]['short_edge_cases'],'acute_angles':result[k]['acute_angle_cases'],'over_12_nodes':result[k]['more_than_12_node_cases']} for k in ['old_visible_B','new_all_B','new_proposals_only']}))

if __name__=='__main__':main()
