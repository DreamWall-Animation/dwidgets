import os
from PySide2 import QtGui, QtCore, QtWidgets


COLORS = [
    'red', '#141923', '#414168', '#3a7fa7', '#35e3e3', '#8fd970',
    '#5ebb49', '#458352', '#dcd37b', '#fffee5', '#ffd035', '#cc9245',
    '#a15c3e', '#a42f3b', '#f45b7a', '#c24998', '#81588d', '#bcb0c2',
    '#ffffff', 'black']


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


def grow_rect(rect, value):
    if rect is None:
        return None
    return QtCore.QRectF(
        rect.left() - value,
        rect.top() - value,
        rect.width() + (value * 2),
        rect.height() + (value * 2))
