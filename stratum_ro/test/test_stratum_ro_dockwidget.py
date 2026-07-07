# coding=utf-8
"""DockWidget test.

.. note:: This program is free software; you can redistribute it and/or modify
     it under the terms of the GNU General Public License as published by
     the Free Software Foundation; either version 2 of the License, or
     (at your option) any later version.

"""

__author__ = 'lefterpatrickandrei@gmail.com'
__date__ = '2026-07-05'
__copyright__ = 'Copyright 2026, Lefter Patrick Andrei , GeoMateLINE'

import unittest

from qgis.PyQt.QtWidgets import QDockWidget

from stratum_ro_dockwidget import StratumRODockWidget

from utilities import get_qgis_app

QGIS_APP = get_qgis_app()


class StratumRODockWidgetTest(unittest.TestCase):
    """Test dockwidget works."""

    def setUp(self):
        """Runs before each test."""
        self.dockwidget = StratumRODockWidget(None)

    def tearDown(self):
        """Runs after each test."""
        self.dockwidget = None

    def test_dockwidget_ok(self):
        """Test the dockwidget is a QDockWidget and exposes its closing signal."""
        self.assertIsInstance(self.dockwidget, QDockWidget)
        self.assertTrue(hasattr(self.dockwidget, 'closingPlugin'))

if __name__ == "__main__":
    suite = unittest.makeSuite(StratumRODockWidgetTest)
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)

