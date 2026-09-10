# -*- coding: utf-8 -*-
"""
Unit tests for QGIS Processing Provider and Algorithm.
"""

import unittest
from stratum_ro.processing_provider import StratumROProcessingProvider
from stratum_ro.cadastral_algorithm import StratumROCadastralAlgorithm


class TestProcessingProvider(unittest.TestCase):

    def test_provider_metadata(self):
        provider = StratumROProcessingProvider()
        self.assertEqual(provider.id(), "stratum_ro")
        self.assertIn("StratumRO", provider.name())

    def test_algorithm_metadata(self):
        alg = StratumROCadastralAlgorithm()
        self.assertEqual(alg.name(), "cadastral_extraction")
        self.assertEqual(alg.groupId(), "stratum_ro_cadastre")


if __name__ == "__main__":
    unittest.main()
