
from PySide2 import QtGui, QtCore, QtWidgets


class Navigator:
    def __init__(self):
        self.left_pressed = False
        self.center_pressed = False
        self.right_pressed = False
        self.space_pressed = False
        self.mouse_ghost = None
        self.anchor = None
        self.zoom_anchor = None

    def update(self, event, pressed=False):
        space = QtCore.Qt.Key_Space
        if isinstance(event, QtGui.QKeyEvent) and event.key() == space:
            self.space_pressed = pressed

        if isinstance(event, QtGui.QMouseEvent):
            buttons = QtCore.Qt.LeftButton, QtCore.Qt.MiddleButton
            if pressed and event.button() in buttons:
                self.mouse_anchor = event.pos()
            elif not pressed and event.button() in buttons:
                self.mouse_anchor = None
                self.mouse_ghost = None
            if event.button() == QtCore.Qt.LeftButton:
                self.left_pressed = pressed
            elif event.button() == QtCore.Qt.MiddleButton:
                self.center_pressed = pressed
            elif event.button() == QtCore.Qt.RightButton:
                self.right_pressed = pressed

    @property
    def shift_pressed(self):
        modifiers = QtWidgets.QApplication.keyboardModifiers()
        return modifiers == (modifiers | QtCore.Qt.ShiftModifier)

    @property
    def alt_pressed(self):
        modifiers = QtWidgets.QApplication.keyboardModifiers()
        return modifiers == (modifiers | QtCore.Qt.AltModifier)

    @property
    def ctrl_pressed(self):
        modifiers = QtWidgets.QApplication.keyboardModifiers()
        return modifiers == (modifiers | QtCore.Qt.ControlModifier)

    def mouse_offset(self, position):
        result = position - self.mouse_ghost if self.mouse_ghost else None
        self.mouse_ghost = position
        return result or None
