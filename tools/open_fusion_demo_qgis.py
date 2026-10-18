"""Launch with qgis --noplugins --code; builds only the isolated demo project."""
from pathlib import Path
import json,os,traceback
from qgis.core import (QgsProject,QgsRasterLayer,QgsVectorLayer,QgsFillSymbol,
    QgsCoordinateReferenceSystem,QgsRectangle,QgsPalLayerSettings,QgsTextFormat,
    QgsVectorLayerSimpleLabeling,QgsMapSettings,QgsMapRendererParallelJob,
    QgsBookmark,QgsReferencedRectangle)
from qgis.PyQt.QtCore import QTimer,QSize
from qgis.PyQt.QtGui import QColor
from qgis.utils import iface

ROOT=Path('C:/Users/lefpa/Downloads/QGIS-AI')
OUT=ROOT/'workspace/reviews/fusion_complete_20261017'


def build_project():
    try:
        project=QgsProject.instance()
        project.setCrs(QgsCoordinateReferenceSystem('EPSG:3844'))
        project.setTitle('StratumRO - FUZIUNE DEMO SEPARAT - rezultate pentru verificare')
        root=project.layerTreeRoot()
        backgrounds=root.addGroup('ORTOFOTO - surse doar citire')
        orthos=[]
        for path in sorted((ROOT/'workspace/reviews/prompt_recovery_20261013/full_aoi').glob('cache_tile_Cluj-*_halo.tif')):
            layer=QgsRasterLayer(str(path),path.stem);project.addMapLayer(layer,False);backgrounds.addLayer(layer);orthos.append(layer)
        history=root.insertGroup(0,'INAINTE - masti brute, mov - debifat')
        for name in ['MASTI_INITIALE','MASCA_GRAY_INITIALA']:
            layer=QgsVectorLayer(str(OUT/'fusion_complete.gpkg')+'|layername='+name,name,'ogr')
            layer.renderer().setSymbol(QgsFillSymbol.createSimple({'color':'0,0,0,0','outline_color':'#b24aff','outline_width':'0.45'}))
            project.addMapLayer(layer,False);history.addLayer(layer)
        history.setItemVisibilityChecked(False)
        results=root.insertGroup(0,'DUPA - ipoteze rectificate, cyan - NECESITA VERDICT')
        drawn=[]
        for body in ['T17:C1','T17:C2','T18:C1','T20:C1']:
            layer=QgsVectorLayer(str(OUT/'fusion_complete.gpkg')+'|layername=IPOTEZE_RECTIFICATE',body+' - NEVERIFICAT','ogr')
            layer.setSubsetString('"body_id" = \''+body+'\'')
            layer.renderer().setSymbol(QgsFillSymbol.createSimple({'color':'0,0,0,0','outline_color':'#00ffff','outline_width':'0.6'}))
            labels=QgsPalLayerSettings();labels.fieldName="\"body_id\" || ' - NEVERIFICAT'";labels.isExpression=True
            text=QgsTextFormat();text.setSize(10);text.setColor(QColor('white'))
            buffer=text.buffer();buffer.setEnabled(True);buffer.setSize(1);buffer.setColor(QColor('black'));text.setBuffer(buffer)
            labels.setFormat(text);layer.setLabeling(QgsVectorLayerSimpleLabeling(labels));layer.setLabelsEnabled(True)
            project.addMapLayer(layer,False);results.addLayer(layer);drawn.append(layer)
        checks=[]
        boxes={'T17':(390765,585430,390903,585553),'T18':(390585,585480,390674,585590),'T20':(390930,585195,391005,585277)}
        for name,coords in boxes.items():
            bookmark=QgsBookmark();bookmark.setName(name+' - fuziune pentru verificare');bookmark.setGroup('StratumRO demonstratie separata')
            bookmark.setExtent(QgsReferencedRectangle(QgsRectangle(*coords),project.crs()));project.bookmarkManager().addBookmark(bookmark)
        iface.mapCanvas().setExtent(QgsRectangle(*boxes['T17']));iface.mapCanvas().refresh()
        project.viewSettings().setDefaultViewExtent(QgsReferencedRectangle(QgsRectangle(*boxes['T17']),project.crs()))
        project.setFileName(str(OUT/'StratumRO_fuziune_inspectie_separata.qgz'))
        if not project.write():raise RuntimeError('Project save failed')
        iface.mainWindow().setWindowTitle('StratumRO - FUZIUNE DEMO SEPARAT - T17 / T18 / T20')
        for l in project.mapLayers().values():
            checks.append({'name':l.name(),'valid':l.isValid(),'source':l.source(),'count':l.featureCount() if isinstance(l,QgsVectorLayer) else None})
        (OUT/'qgis_verified_state.json').write_text(json.dumps({'pid':os.getpid(),'project':project.fileName(),'layers':checks},indent=2),encoding='utf-8')
        def render_evidence():
            for name,coords in boxes.items():
                settings=QgsMapSettings();settings.setDestinationCrs(project.crs());settings.setLayers(drawn+orthos)
                settings.setExtent(QgsRectangle(*coords));settings.setOutputSize(QSize(1400,1100));settings.setBackgroundColor(QColor('white'))
                job=QgsMapRendererParallelJob(settings);job.start();job.waitForFinished();job.renderedImage().save(str(OUT/(name+'_qgis.png')))
            iface.mapCanvas().setExtent(QgsRectangle(*boxes['T17']));iface.mapCanvas().refresh()
            def save_canvas():
                iface.mapCanvas().grab().save(str(OUT/'qgis_live_canvas.png'))
                project.viewSettings().setDefaultViewExtent(QgsReferencedRectangle(QgsRectangle(*boxes['T17']),project.crs()))
                project.write()
            QTimer.singleShot(1500,save_canvas)
            (OUT/'qgis_render_complete.txt').write_text('complete',encoding='utf-8')
        QTimer.singleShot(2500,render_evidence)
    except Exception:
        (OUT/'qgis_error.txt').write_text(traceback.format_exc(),encoding='utf-8')

QTimer.singleShot(1500,build_project)
