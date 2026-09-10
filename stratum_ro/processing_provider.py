# -*- coding: utf-8 -*-
"""
QGIS Processing Provider for StratumRO.
Registers StratumRO in the QGIS Processing Toolbox under the 'StratumRO Cadastru' group.
"""

import os
try:
    from qgis.core import QgsProcessingProvider
    from qgis.PyQt.QtGui import QIcon
    HAS_QGIS_PROCESSING = True
except ImportError:
    HAS_QGIS_PROCESSING = False
    class QgsProcessingProvider:
        pass

from .cadastral_algorithm import StratumROCadastralAlgorithm


class StratumROProcessingProvider(QgsProcessingProvider):
    """Exposes StratumRO algorithms in QGIS Processing Toolbox."""

    def __init__(self):
        super().__init__()

    def id(self):
        return "stratum_ro"

    def name(self):
        return "StratumRO Cadastru & AI"

    def icon(self):
        icon_path = os.path.join(os.path.dirname(__file__), "icon.png")
        if os.path.exists(icon_path) and HAS_QGIS_PROCESSING:
            return QIcon(icon_path)
        return super().icon() if HAS_QGIS_PROCESSING else None

    def longName(self):
        return "StratumRO — Sistem Inteligent de Segmentare și Regularizare Cadastrală Hibridă"

    def loadAlgorithms(self):
        if not HAS_QGIS_PROCESSING:
            return
        self.addAlgorithm(StratumROCadastralAlgorithm())
