from PySide2 import QtCore, QtGui
from dwidgets.retakecanvas.shapes import Stroke
from dwidgets.retakecanvas.tools.basetool import NavigationTool
from dwidgets.retakecanvas.mathutils import distance


class DrawTool(NavigationTool):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pressure = 1
        self.stroke = None
        self.old_time = None
        self.old_mouse_time = None

    def mousePressEvent(self, event):
        if self.layerstack.is_locked or self.navigator.space_pressed:
            return
        if self.layerstack.current is None:
            self.model.add_layer(undo=False, name='Stroke')
        self.selection.clear()
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
        event.accept()

    def mouseReleaseEvent(self, event):
        if self.stroke:
            if not self.stroke.is_valid:
                self.layerstack.current.remove(self.stroke)
            self.stroke = None
        else:
            super().mouseReleaseEvent(event)
        return True

    def tabletEvent(self, event):
        if event.type() == QtGui.QTabletEvent.TabletPress:
            event.accept()
            return
        if event.type() == QtGui.QTabletEvent.TabletRelease:
            event.accept()
            return
        self.pressure = event.pressure()
        point = self.viewportmapper.to_units_coords(event.pos())
        width = self.pressure * self.drawcontext.size
        if self.stroke and distance(point, self.stroke[-1][0]) > width:
            self.stroke.add_point(
                point=point,
                size=width)
        event.accept()

    def window_cursor_visible(self):
        return self.navigator.space_pressed or self.layerstack.is_locked

    def window_cursor_override(self):
        cursor = super().window_cursor_override()
        if cursor:
            return cursor
        if self.layerstack.is_locked:
            return QtCore.Qt.ForbiddenCursor

    def draw(self, painter):
        if self.navigator.space_pressed:
            return
        radius = self.viewportmapper.to_viewport(self.drawcontext.size)
        painter.setCompositionMode(QtGui.QPainter.CompositionMode_Difference)
        painter.setPen(QtCore.Qt.white)
        painter.setBrush(QtCore.Qt.transparent)
        pos = self.canvas.mapFromGlobal(QtGui.QCursor.pos())
        painter.drawEllipse(pos, radius / 2, radius / 2)


class SmoothDrawTool(NavigationTool):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pressure = 1
        self.stroke = None
        self.buffer = []
        self.pressure_buffer = []
        self.buffer_lenght = 20

    def mousePressEvent(self, event):
        if self.layerstack.is_locked or self.navigator.space_pressed:
            return
        if self.layerstack.current is None:
            self.model.add_layer(undo=False, name='Stroke')
        self.selection.clear()
        point = self.viewportmapper.to_units_coords(event.pos())
        pressure = self.pressure * self.drawcontext.size
        self.buffer = [point]
        self.pressure_buffer = [pressure]
        self.stroke = Stroke(
            start=point, color=self.drawcontext.color, size=pressure)
        self.layerstack.current.append(self.stroke)

    def mouseMoveEvent(self, event):
        if super().mouseMoveEvent(event) or not self.stroke:
            return
        self.buffer.append(self.viewportmapper.to_units_coords(event.pos()))
        if self.stroke:
            x = sum(p.x() for p in self.buffer) / len(self.buffer)
            y = sum(p.y() for p in self.buffer) / len(self.buffer)
            self.stroke.add_point(
                point=QtCore.QPointF(x, y),
                size=sum(self.pressure_buffer) / len(self.pressure_buffer))
        self.buffer = self.buffer[-self.buffer_lenght:]
        self.pressure_buffer = self.pressure_buffer[-self.buffer_lenght:]

    def mouseReleaseEvent(self, event):
        self.buffer = []
        self.pressure_buffer = []
        if self.stroke:
            if not self.stroke.is_valid:
                self.layerstack.current.remove(self.stroke)
            self.stroke = None
        else:
            super().mouseReleaseEvent(event)
        return True

    def tabletEvent(self, event):
        self.pressure = event.pressure()

    def window_cursor_visible(self):
        return self.navigator.space_pressed

    def window_cursor_override(self):
        cursor = super().window_cursor_override()
        if cursor:
            return cursor
        if self.layerstack.is_locked:
            return QtCore.Qt.ForbiddenCursor

    def draw(self, painter):
        if self.navigator.space_pressed:
            return
        radius = self.viewportmapper.to_viewport(self.drawcontext.size)
        painter.setCompositionMode(QtGui.QPainter.CompositionMode_Difference)
        painter.setPen(QtCore.Qt.white)
        painter.setBrush(QtCore.Qt.transparent)
        pos = self.canvas.mapFromGlobal(QtGui.QCursor.pos())
        painter.drawEllipse(pos, radius / 2, radius / 2)
        if not self.stroke:
            return
        point = self.stroke.points[-1][0]
        point = self.viewportmapper.to_viewport_coords(point)
        painter.drawLine(pos, point)
