from pathlib import Path
import json, os, traceback
from qgis.core import (QgsProject, QgsCoordinateReferenceSystem, QgsRasterLayer,
    QgsPointCloudLayer, QgsRectangle, QgsMapSettings, QgsMapRendererParallelJob,
    QgsSingleBandPseudoColorRenderer, QgsColorRampShader, QgsRasterShader)
from qgis.PyQt.QtCore import QTimer, QSize
from qgis.PyQt.QtGui import QColor
from qgis.utils import iface

OUT=Path('C:/Users/lefpa/Downloads/QGIS-AI/workspace/reviews/lidar_audit_20261017')
ROOT=OUT.parents[2]
def start_audit():
    try:
        project=QgsProject.instance()
        project.setCrs(QgsCoordinateReferenceSystem('EPSG:3844'))
        project.setTitle('StratumRO - INSPECTIE LiDAR separata - CRS ipoteza Stereo70')
        base=project.layerTreeRoot().addGroup('ORTOFOTO - surse existente, doar citire')
        orthos=[]
        for p in sorted((ROOT/'workspace/reviews/prompt_recovery_20261013/full_aoi').glob('cache_tile_Cluj-*_halo.tif')):
            layer=QgsRasterLayer(str(p),p.stem)
            project.addMapLayer(layer,False);base.addLayer(layer);orthos.append(layer)
        audit=project.layerTreeRoot().insertGroup(0,'DIAGNOSTIC LiDAR - EPSG3844 IPOTEZA, fara reproiectare')
        rasters=[]
        for stem,title,maximum in [('point_density_1m','DENSITATE - puncte pe celula 1m',12),('surface_height_1m','SUPRAFATA - cota absoluta, nu inaltime cladire',450),('class6_density_1m','CLASA 6 - puncte cladiri, 0 transparent',10),('relative_surface_1m','INALTIME RELATIVA - toate clasele, diagnostic DTM 3m',20)]:
            layer=QgsRasterLayer(str(OUT/(stem+'.tif')),title)
            ramp=QgsColorRampShader();ramp.setColorRampType(QgsColorRampShader.Interpolated)
            ramp.setColorRampItemList([QgsColorRampShader.ColorRampItem(0,QColor(255,0,0,0),'0'),QgsColorRampShader.ColorRampItem(1,QColor('#ffeb3b'),'1'),QgsColorRampShader.ColorRampItem(maximum,QColor('#e00050'),str(maximum))])
            shader=QgsRasterShader();shader.setRasterShaderFunction(ramp)
            layer.setRenderer(QgsSingleBandPseudoColorRenderer(layer.dataProvider(),1,shader))
            project.addMapLayer(layer,False);audit.insertLayer(0,layer)
            audit.findLayer(layer.id()).setItemVisibilityChecked(stem=='class6_density_1m')
            rasters.append(layer)
        cloud=QgsPointCloudLayer('C:/Users/lefpa/Desktop/date/Z_VladP/Comparatie/LAZ/NorPuncte_St70_S42.laz','NOR ORIGINAL - CRS header 4284 incompatibil; afisare ipoteza 3844','pdal')
        if cloud.isValid():
            cloud.setCrs(QgsCoordinateReferenceSystem('EPSG:3844'))
            project.addMapLayer(cloud,False);node=audit.addLayer(cloud);node.setItemVisibilityChecked(False)
        extent=QgsRectangle(390470,584970,391540,585890)
        iface.mapCanvas().setExtent(extent);iface.mapCanvas().refresh()
        project.setFileName(str(OUT/'inspectie_lidar_separata.qgz'))
        project.write()
        (OUT/'separate_qgis_state.json').write_text(json.dumps({'pid':os.getpid(),'project':project.fileName(),'point_cloud_valid':cloud.isValid(),'layers':[{'name':l.name(),'valid':l.isValid(),'source':l.source()} for l in project.mapLayers().values()]},indent=2),encoding='utf-8')
        def render():
            for name,box in [('overview',[390470,584970,391540,585890]),('T17',[390755,585425,390885,585540]),('T18',[390575,585475,390680,585600]),('T20',[390920,585185,391015,585290])]:
                for mode,layers in [('ortho',orthos),('class6',[rasters[2]]+orthos),('height',[rasters[3]]+orthos)]:
                    settings=QgsMapSettings();settings.setDestinationCrs(project.crs());settings.setLayers(layers);settings.setExtent(QgsRectangle(*box));settings.setOutputSize(QSize(1200,1000));settings.setBackgroundColor(QColor('white'))
                    job=QgsMapRendererParallelJob(settings);job.start();job.waitForFinished();job.renderedImage().save(str(OUT/(name+'_'+mode+'.png')))
            (OUT/'render_complete.txt').write_text('complete',encoding='utf-8')
        QTimer.singleShot(2000,render)
    except Exception:
        (OUT/'startup_error.txt').write_text(traceback.format_exc(),encoding='utf-8')
QTimer.singleShot(1500,start_audit)
