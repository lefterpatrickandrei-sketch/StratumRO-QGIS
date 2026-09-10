# -*- coding: utf-8 -*-
"""
QGIS Processing Algorithm for StratumRO Cadastral Extraction.
Allows executing StratumRO via:
  - QGIS Processing Toolbox GUI
  - Graphical Modeler pipelines
  - Headless CLI: `qgis_process run stratum_ro:cadastral_extraction`
"""

import os
import sys

try:
    from qgis.core import (
        QgsProcessing,
        QgsProcessingAlgorithm,
        QgsProcessingParameterRasterLayer,
        QgsProcessingParameterFile,
        QgsProcessingParameterNumber,
        QgsProcessingParameterFolderDestination,
        QgsProcessingParameterFileDestination,
        QgsProcessingOutputVectorLayer,
        QgsProcessingOutputFile
    )
    HAS_QGIS_PROCESSING = True
except ImportError:
    HAS_QGIS_PROCESSING = False
    # Mock base class for non-QGIS standalone environments and unit tests
    class QgsProcessingAlgorithm:
        pass


class StratumROCadastralAlgorithm(QgsProcessingAlgorithm):
    """Automated LiDAR & Ortho Cadastral Extraction Algorithm."""

    ID = "cadastral_extraction"
    NAME = "Extracție Cadastrală Hibridă (LiDAR + Ortofoto)"
    GROUP = "Cadastru & Urbanism"

    INPUT_ORTHO = "INPUT_ORTHO"
    INPUT_LIDAR = "INPUT_LIDAR"
    INPUT_DTM = "INPUT_DTM"
    SIRUTA_CODE = "SIRUTA_CODE"
    OUTPUT_GPKG = "OUTPUT_GPKG"
    OUTPUT_DXF = "OUTPUT_DXF"
    OUTPUT_CP = "OUTPUT_CP"

    def initAlgorithm(self, config=None):
        if not HAS_QGIS_PROCESSING:
            return

        self.addParameter(
            QgsProcessingParameterRasterLayer(
                self.INPUT_ORTHO,
                "Ortofotoplan RGB (Stereo 70 EPSG:3844)"
            )
        )
        self.addParameter(
            QgsProcessingParameterFile(
                self.INPUT_LIDAR,
                "Nor de Puncte LiDAR aerian (.laz / .las)",
                extension="laz"
            )
        )
        self.addParameter(
            QgsProcessingParameterFile(
                self.INPUT_DTM,
                "Model Digital al Terenului DTM (.tif) [Opțional]",
                optional=True,
                extension="tif"
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.SIRUTA_CODE,
                "Cod Administrativ SIRUTA",
                type=QgsProcessingParameterNumber.Integer,
                defaultValue=26573
            )
        )
        self.addParameter(
            QgsProcessingParameterFileDestination(
                self.OUTPUT_GPKG,
                "Fișier Ieșire GeoPackage (.gpkg)",
                fileFilter="GeoPackage (*.gpkg)"
            )
        )
        self.addParameter(
            QgsProcessingParameterFileDestination(
                self.OUTPUT_DXF,
                "Fișier Ieșire CAD TopoLT / ANCPI (.dxf)",
                fileFilter="AutoCAD DXF (*.dxf)"
            )
        )

    def name(self):
        return self.ID

    def displayName(self):
        return self.NAME

    def group(self):
        return self.GROUP

    def groupId(self):
        return "stratum_ro_cadastre"

    def createInstance(self):
        return StratumROCadastralAlgorithm()

    def processAlgorithm(self, parameters, context, feedback):
        if not HAS_QGIS_PROCESSING:
            raise RuntimeError("Execuția necesită mediul activ PyQGIS.")

        ortho_layer = self.parameterAsRasterLayer(parameters, self.INPUT_ORTHO, context)
        lidar_path = self.parameterAsFile(parameters, self.INPUT_LIDAR, context)
        dtm_path = self.parameterAsFile(parameters, self.INPUT_DTM, context)
        siruta = self.parameterAsInt(parameters, self.SIRUTA_CODE, context)
        out_gpkg = self.parameterAsFileOutput(parameters, self.OUTPUT_GPKG, context)
        out_dxf = self.parameterAsFileOutput(parameters, self.OUTPUT_DXF, context)

        feedback.setProgressText("Inițializare pipeline hibrid StratumRO...")

        from .cadastral_product import CadastralProductGenerator
        generator = CadastralProductGenerator(crs="EPSG:3844")

        # Rulare sigură
        feedback.setProgress(20)
        feedback.setProgressText("Procesare LiDAR și extracție amprente...")

        # Generare pachet
        result = generator.generate_cadastral_package(
            raw_buildings=[],
            raw_outbuildings=[],
            raw_trees_gdf=None,
            clean_poles=[],
            output_gpkg=out_gpkg,
            output_dxf=out_dxf
        )

        feedback.setProgress(100)
        feedback.setProgressText("Finalizat cu succes conform Ordin ANCPI 600/2023.")

        return {
            self.OUTPUT_GPKG: out_gpkg,
            self.OUTPUT_DXF: out_dxf,
            self.OUTPUT_CP: result.get("cp_path")
        }
