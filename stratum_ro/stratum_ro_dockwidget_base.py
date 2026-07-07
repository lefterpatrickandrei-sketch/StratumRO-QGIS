# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'stratum_ro_dockwidget_base.ui'
from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_StratumRODockWidgetBase(object):
    def setupUi(self, StratumRODockWidgetBase):
        StratumRODockWidgetBase.setObjectName("StratumRODockWidgetBase")
        StratumRODockWidgetBase.resize(447, 166)
        self.dockWidgetContents = QtWidgets.QWidget()
        self.dockWidgetContents.setObjectName("dockWidgetContents")
        self.gridLayout = QtWidgets.QGridLayout(self.dockWidgetContents)
        self.gridLayout.setObjectName("gridLayout")
        self.btnSelectAOI = QtWidgets.QPushButton(self.dockWidgetContents)
        self.btnSelectAOI.setObjectName("btnSelectAOI")
        self.gridLayout.addWidget(self.btnSelectAOI, 5, 0, 1, 1)
        self.lblStatus_2 = QtWidgets.QLabel(self.dockWidgetContents)
        self.lblStatus_2.setObjectName("lblStatus_2")
        self.gridLayout.addWidget(self.lblStatus_2, 7, 0, 1, 1)
        self.btnRunSegmentation = QtWidgets.QPushButton(self.dockWidgetContents)
        self.btnRunSegmentation.setObjectName("btnRunSegmentation")
        self.gridLayout.addWidget(self.btnRunSegmentation, 6, 0, 1, 1)
        StratumRODockWidgetBase.setWidget(self.dockWidgetContents)

        self.retranslateUi(StratumRODockWidgetBase)
        QtCore.QMetaObject.connectSlotsByName(StratumRODockWidgetBase)

    def retranslateUi(self, StratumRODockWidgetBase):
        _translate = QtCore.QCoreApplication.translate
        StratumRODockWidgetBase.setWindowTitle(_translate("StratumRODockWidgetBase", "StratumRO"))
        self.btnSelectAOI.setText(_translate("StratumRODockWidgetBase", "Selectează AOI"))
        self.lblStatus_2.setText(_translate("StratumRODockWidgetBase", "Status: gata\n\n"))
        self.btnRunSegmentation.setText(_translate("StratumRODockWidgetBase", "Rulează segmentare"))