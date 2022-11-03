from PySide2 import QtCore, QtWidgets, QtGui
from dwidgets.retakecanvas.shapes import Stroke, Arrow, Rectangle, Circle


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


class BaseTool:
    """
    This baseclass is only there to avoid reimplement unused method in each
    children. This is NOT doing anything.
    """
    def __init__(self, drawcontext, layerstack, navigator, viewportmapper):
        self.drawcontext = drawcontext
        self.layerstack = layerstack
        self.navigator = navigator
        self.viewportmapper = viewportmapper

    def keyPressEvent(self, event):
        ...

    def keyReleaseEvent(self, event):
        ...

    def mousePressEvent(self, event):
        ...

    def mouseMoveEvent(self, event):
        ...

    def mouseReleaseEvent(self, event):
        ...

    def mouseWheelEvent(self, event):
        ...

    def tabletEvent(self, event):
        ...

    def wheelEvent(self, event):
        ...


class NavigationTool(BaseTool):
    def mouseMoveEvent(self, event):
        zooming = self.navigator.shift_pressed and self.navigator.alt_pressed
        if zooming:
            offset = self.navigator.mouse_offset(event.pos())
            if offset is not None and self.navigator.zoom_anchor:
                factor = (offset.x() + offset.y()) / 10
                self.zoom(factor, self.navigator.zoom_anchor)
                return True

        if self.navigator.left_pressed and self.navigator.space_pressed:
            offset = self.navigator.mouse_offset(event.pos())
            if offset is not None:
                self.viewportmapper.origin = (
                    self.viewportmapper.origin - offset)
            return True
        return False

    def wheelEvent(self, event):
        factor = .25 if event.angleDelta().y() > 0 else -.25
        zoom(self.viewportmapper, factor, event.position())

    def mouseReleaseEvent(self, event):
        return False


class ShapeTool(NavigationTool):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.shape_cls = Arrow
        self.shape = None

    def mousePressEvent(self, event):
        if self.navigator.space_pressed or self.layerstack.current is None:
            return
        self.shape = self.shape_cls(
            start=self.viewportmapper.to_units_coords(event.pos()),
            color=self.drawcontext.color)
        self.layerstack.current.append(self.shape)

    def mouseMoveEvent(self, event):
        if super().mouseMoveEvent(event):
            return
        if self.shape:
            self.shape.handle(self.viewportmapper.to_units_coords(event.pos()))

    def mouseReleaseEvent(self, event):
        if self.shape:
            if not self.shape.is_valid:
                self.layerstack.current.remove(self.shape)
            self.shape = None
        else:
            super().mouseReleaseEvent(event)
        return True


class ArrowTool(ShapeTool):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.shape_cls = Arrow
        self.headsize = 5
        self.tailwidth = 5

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if self.shape:
            self.shape.headsize = self.headsize
            self.shape.tailwidth = self.tailwidth


class RectangleTool(ShapeTool):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.shape_cls = Rectangle


class CircleTool(ShapeTool):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.shape_cls = Circle


class DrawTool(NavigationTool):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pressure = 1
        self.stroke = None

    def mousePressEvent(self, event):
        if self.navigator.space_pressed or self.layerstack.current is None:
            return
        self.stroke = Stroke(
            start=self.viewportmapper.to_units_coords(event.pos()),
            color=self.drawcontext.color,
            size=self.pressure * self.drawcontext.size)
        self.layerstack.current.append(self.stroke)

    def mouseMoveEvent(self, event):
        if super().mouseMoveEvent(event):
            return
        if self.stroke:
            self.stroke.add_point(
                point=self.viewportmapper.to_units_coords(event.pos()),
                size=self.pressure * self.drawcontext.size)

    def mouseReleaseEvent(self, event):
        if self.stroke:
            if not self.stroke.is_valid:
                self.layerstack.current.remove(self.stroke)
            self.stroke = None
        else:
            super().mouseReleaseEvent(event)
        return True

    def tabletEvent(self, event):
        self.pressure = event.pressure()


def zoom(viewportmapper, factor, reference):
    abspoint = viewportmapper.to_units_coords(reference)
    if factor > 0:
        viewportmapper.zoomin(abs(factor))
    else:
        viewportmapper.zoomout(abs(factor))
    relcursor = viewportmapper.to_viewport_coords(abspoint)
    vector = relcursor - reference
    viewportmapper.origin = viewportmapper.origin + vector