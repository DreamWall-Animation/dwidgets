from PySide2 import QtWidgets, QtCore


def move_widget_in_screen(window):
    index = QtWidgets.QApplication.desktop().screenNumber(window)
    screen = QtWidgets.QApplication.screens()[index]
    screen_geometry = screen.availableGeometry()
    x = max(
        screen_geometry.left(),
        min(window.x(), screen_geometry.right() - window.width()))
    y = max(
        screen_geometry.top(),
        min(window.y(), screen_geometry.bottom() - window.height()))
    window.move(x, y)


def grow_rect(rect, value):
    if rect is None:
        return None
    return QtCore.QRectF(
        rect.left() - value,
        rect.top() - value,
        rect.width() + (value * 2),
        rect.height() + (value * 2))
