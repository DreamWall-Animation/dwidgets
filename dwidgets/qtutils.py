from PySide2 import QtWidgets


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
