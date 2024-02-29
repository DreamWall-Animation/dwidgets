
from PySide2 import QtCore
from dwidgets.retakecanvas.shapes import Arrow, Rectangle, Circle, Line
from dwidgets.retakecanvas.tools.basetool import NavigationTool


class ShapeTool(NavigationTool):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.layername = 'Shape'
        self.shape = None

    def mouseMoveEvent(self, event):
        if super().mouseMoveEvent(event):
            return
        if self.shape:
            self.shape.handle(self.viewportmapper.to_units_coords(event.pos()))

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        if self.shape:
            if not self.shape.is_valid:
                self.layerstack.current.remove(self.shape)
            self.shape = None
            self.selection.clear()
        else:
            super().mouseReleaseEvent(event)
        return True

    def tabletMoveEvent(self, event):
        self.mouseMoveEvent(event)

    def window_cursor_override(self):
        result = super().window_cursor_override()
        if result:
            return result
        if self.layerstack.is_locked:
            return QtCore.Qt.ForbiddenCursor


class LineTool(ShapeTool):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.layername = 'Line'
        self.linewidth = 10

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if self.layerstack.is_locked or self.navigator.space_pressed:
            return
        if event.button() != QtCore.Qt.LeftButton:
            return
        if self.layerstack.current is None:
            self.model.add_layer(undo=False, name=self.layername)
        self.selection.clear()
        self.shape = Line(
            start=self.viewportmapper.to_units_coords(event.pos()),
            color=self.drawcontext.color,
            linewidth=self.drawcontext.size)
        self.layerstack.current.append(self.shape)


class ArrowTool(ShapeTool):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.layername = 'Arrow'
        self.headsize = 10
        self.tailwidth = 10

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if self.layerstack.is_locked or self.navigator.space_pressed:
            return
        if event.button() != QtCore.Qt.LeftButton:
            return
        if self.layerstack.current is None:
            self.model.add_layer(undo=False, name=self.layername)
        self.selection.clear()
        self.shape = Arrow(
            start=self.viewportmapper.to_units_coords(event.pos()),
            color=self.drawcontext.color,
            linewidth=self.drawcontext.size)
        self.layerstack.current.append(self.shape)
        if self.shape:
            self.shape.headsize = self.headsize
            self.shape.tailwidth = self.tailwidth


class RectangleTool(ShapeTool):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.layername = 'Rectangle'
        self.shape_cls = Rectangle

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if self.layerstack.is_locked or self.navigator.space_pressed:
            return
        if event.button() != QtCore.Qt.LeftButton:
            return
        if self.layerstack.current is None:
            self.model.add_layer(undo=False, name=self.layername)
        self.selection.clear()
        self.shape = Rectangle(
            start=self.viewportmapper.to_units_coords(event.pos()),
            color=self.drawcontext.color,
            bgcolor=self.drawcontext.bgcolor,
            bgopacity=self.drawcontext.bgopacity,
            linewidth=self.drawcontext.size,
            filled=self.drawcontext.filled)
        self.layerstack.current.append(self.shape)


class CircleTool(ShapeTool):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.layername = 'Circle'

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if self.layerstack.is_locked or self.navigator.space_pressed:
            return
        if event.button() != QtCore.Qt.LeftButton:
            return
        if self.layerstack.current is None:
            self.model.add_layer(undo=False, name=self.layername)
        self.selection.clear()
        self.shape = Circle(
            start=self.viewportmapper.to_units_coords(event.pos()),
            color=self.drawcontext.color,
            bgcolor=self.drawcontext.bgcolor,
            bgopacity=self.drawcontext.bgopacity,
            linewidth=self.drawcontext.size,
            filled=self.drawcontext.filled)
        self.layerstack.current.append(self.shape)
