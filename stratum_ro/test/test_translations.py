# coding=utf-8
"""Safe Translations Test.

.. note:: This program is free software; you can redistribute it and/or modify
     it under the terms of the GNU General Public License as published by
     the Free Software Foundation; either version 2 of the License, or
     (at your option) any later version.

"""
import unittest
import os

try:
    from qgis.PyQt.QtCore import QCoreApplication, QTranslator
    from .utilities import get_qgis_app
    QGIS_APP = get_qgis_app()
    HAS_QGIS = True
except (ImportError, ModuleNotFoundError):
    HAS_QGIS = False
    QGIS_APP = None


@unittest.skipUnless(HAS_QGIS, "QGIS library is required for this test")
class SafeTranslationsTest(unittest.TestCase):
    """Test translations work."""

    def setUp(self):
        """Runs before each test."""
        if 'LANG' in iter(os.environ.keys()):
            os.environ.__delitem__('LANG')

    def tearDown(self):
        """Runs after each test."""
        if 'LANG' in iter(os.environ.keys()):
            os.environ.__delitem__('LANG')

    def test_qgis_translations(self):
        """Test that translations work."""
        parent_path = os.path.join(__file__, os.path.pardir, os.path.pardir)
        dir_path = os.path.abspath(parent_path)
        file_path = os.path.join(
            dir_path, 'i18n', 'af.qm')
        if not os.path.isfile(file_path):
            self.skipTest('af.qm not found — run "make" to compile translations first')
        translator = QTranslator()
        self.assertTrue(translator.load(file_path), 'Failed to load af.qm')
        QCoreApplication.installTranslator(translator)

        expected_message = 'Goeie more'
        real_message = QCoreApplication.translate("@default", 'Good morning')
        self.assertEqual(real_message, expected_message)


if __name__ == "__main__":
    suite = unittest.makeSuite(SafeTranslationsTest)
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)
