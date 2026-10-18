"""Execute in live QGIS: reproducible stage images, no geometry edits.

Set RUN_DIRECTORY, START_INDEX, END_INDEX in the execution namespace. Sources
are read after runner completion. Every baseline object gets a before/after view.
"""
import hashlib,json
from pathlib import Path
from qgis.core import (QgsProject,QgsVectorLayer,QgsFeature,QgsGeometry,QgsMapSettings,
    QgsMapRendererParallelJob,QgsRectangle,QgsFillSymbol,QgsCoordinateReferenceSystem)
from qgis.PyQt.QtCore import QSize
from qgis.PyQt.QtGui import QImage,QPainter,QColor,QFont
from qgis.utils import iface

root=Path('C:/Users/lefpa/Downloads/QGIS-AI')
out=root/RUN_DIRECTORY
gpkg=out/'refinement.gpkg'
before_state=(QgsProject.instance().isDirty(),[l.id() for l in iface.mapCanvas().layers()])
basemaps=[l for l in iface.mapCanvas().layers() if l.name().startswith('Cluj-')]
layers={name:QgsVectorLayer(str(gpkg)+'|layername='+name,name,'ogr') for name in [
    'B0_BASELINE','B1_OBSERVATIONS','B3_SIMPLE_FIT','B3_BEFORE_RETRY_QA','B4_RETRY_OBSERVATIONS','B4_FINAL_REVIEW']}
features={name:{f['candidate_id']:f for f in layer.getFeatures()} for name,layer in layers.items() if layer.isValid()}
ids=sorted(features['B0_BASELINE'])
report=json.loads((out/'report.json').read_text())
aliases={r['suppressed']:r['retained'] for r in report['duplicate_links']}
images=out/'images';images.mkdir(exist_ok=True)
manifest_path=out/'visual_manifest.json'
manifest=json.loads(manifest_path.read_text()) if manifest_path.exists() else []
manifest={e['candidate_id']:e for e in manifest}

def render(geometry,extent,color,width=550,height=420):
    v=QgsVectorLayer('Polygon?crs=EPSG:3844','offscreen evidence','memory')
    f=QgsFeature();f.setGeometry(QgsGeometry(geometry));v.dataProvider().addFeatures([f])
    v.renderer().setSymbol(QgsFillSymbol.createSimple({'color':'0,0,0,0','outline_color':color,'outline_width':'.6'}))
    settings=QgsMapSettings();settings.setDestinationCrs(QgsCoordinateReferenceSystem('EPSG:3844'))
    settings.setLayers([v]+basemaps);settings.setExtent(extent);settings.setOutputSize(QSize(width,height))
    job=QgsMapRendererParallelJob(settings);job.start();job.waitForFinished()
    return job.renderedImage()

for ident in ids[START_INDEX:END_INDEX]:
    old=features['B0_BASELINE'][ident];final_id=aliases.get(ident,ident)
    new=features['B4_FINAL_REVIEW'].get(final_id)
    if new is None:raise ValueError('Lost output lineage: '+ident)
    extent=QgsRectangle(old.geometry().boundingBox());extent.combineExtentWith(new.geometry().boundingBox());extent.scale(1.5)
    sheet=QImage(1100,460,QImage.Format_ARGB32);sheet.fill(QColor('white'))
    painter=QPainter(sheet);painter.setFont(QFont('Arial',11));painter.setPen(QColor('black'))
    painter.drawText(10,25,ident+' - B initial')
    painter.drawText(560,25,final_id+' - '+str(new['qa_status']))
    painter.drawImage(0,40,render(old.geometry(),extent,'255,160,0,255'))
    color='0,220,255,255' if new['qa_status']=='SIMPLE_ROOF_HYPOTHESIS' else '255,160,0,255'
    painter.drawImage(550,40,render(new.geometry(),extent,color));painter.end()
    dest=images/(ident.replace(':','_')+'.png');assert sheet.save(str(dest))
    manifest[ident]=dict(candidate_id=ident,final_id=final_id,path=dest.relative_to(out).as_posix(),
        sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),qa_status=str(new['qa_status']))

# Six panels show the actual observation, fitted mask and retry, not just final.
if START_INDEX==0:
    for ident in ['OPT_B_006:C1','OPT_B_046:C1','OPT_B_154:C1','OPT_B_169:C1','OPT_B_120:C1','OPT_B_201:C1']:
        old=features['B0_BASELINE'][ident]
        extent=QgsRectangle(old.geometry().boundingBox());extent.scale(1.7)
        final_id=aliases.get(ident,ident)
        sheet=QImage(1650,930,QImage.Format_ARGB32);sheet.fill(QColor('white'))
        painter=QPainter(sheet);painter.setFont(QFont('Arial',11))
        stages=[('B0_BASELINE','1. B initial'),('B1_OBSERVATIONS','2. Observatia optica originala'),
                ('B3_SIMPLE_FIT','3. Forma cu garduri'),('B4_RETRY_OBSERVATIONS','4. Incercare SAM2 (diagnostic)'),
                ('B3_BEFORE_RETRY_QA','5. QA inainte de SAM2'),('B4_FINAL_REVIEW','6. Rezultat propus / revizie')]
        for n,(name,title) in enumerate(stages):
            key=final_id if name=='B4_FINAL_REVIEW' else ident
            f=features.get(name,{}).get(key)
            x=(n%3)*550;y=(n//3)*465
            painter.setPen(QColor('black'));painter.drawText(x+8,y+24,title)
            if f is not None:painter.drawImage(x,y+40,render(f.geometry(),extent,'0,220,255,255'))
            else:painter.drawText(x+20,y+180,'Nu s-a rulat / fara observatie separata')
        painter.end();dest=images/(ident.replace(':','_')+'_stages.png');assert sheet.save(str(dest))

manifest_path.write_text(json.dumps(list(manifest.values()),indent=2))
assert before_state==(QgsProject.instance().isDirty(),[l.id() for l in iface.mapCanvas().layers()])
print(json.dumps({'rendered_range':[START_INDEX,END_INDEX],'total_images':len(manifest),'project_unchanged':True}))
