import os
from PySide2 import QtGui, QtCore, QtWidgets


def icon(filename):
    folder = os.path.dirname(__file__)
    return QtGui.QIcon(f'{folder}/../icons/{filename}')


def pixmap(filename):
    folder = os.path.dirname(__file__)
    return QtGui.QPixmap(f'{folder}/../icons/{filename}')


def set_shortcut(keysequence, parent, method, context=None):
    shortcut = QtWidgets.QShortcut(QtGui.QKeySequence(keysequence), parent)
    shortcut.setContext(context or QtCore.Qt.WidgetWithChildrenShortcut)
    shortcut.activated.connect(method)
    return shortcut
