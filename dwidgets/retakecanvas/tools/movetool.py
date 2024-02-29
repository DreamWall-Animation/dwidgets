from PySide2 import QtCore, QtGui
from dwidgets.retakecanvas.geometry import get_shape_rect
from dwidgets.retakecanvas.tools.basetool import NavigationTool
from dwidgets.retakecanvas.selection import selection_rect, Selection
from dwidgets.retakecanvas.shapes import (
    Arrow, Rectangle, Circle, Bitmap, Stroke, Text, Line)


class MoveTool(NavigationTool):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._mouse_ghost = None
        self.element_hover = None

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        return_condition = (
            self.navigator.space_pressed or
            self.layerstack.current is None or
            self.layerstack.is_locked)
        if return_condition:
            return
        self._mouse_ghost = event.pos()
        if self.element_hover is self.selection:
            return
        if self.element_hover:
            self.selection.set(self.element_hover)
            self.canvas.selectionChanged.emit()
            return
        self.selection.clear()
        self.canvas.selectionChanged.emit()

    def set_hover_element(self, point):
        if self.selection.type:
            units_pos = self.viewportmapper.to_units_coords(point)
            rect = selection_rect(self.selection)
            if rect and rect.contains(units_pos):
                self.element_hover = self.selection
                return
        point = self.viewportmapper.to_units_coords(point)
        self.element_hover = self.layerstack.find_element_at(point)

    def mouseMoveEvent(self, event):
        if super().mouseMoveEvent(event):
            return
        if not self._mouse_ghost:
            self.set_hover_element(event.pos())
            return

        point = event.pos()
        x = self.viewportmapper.to_units(self._mouse_ghost.x() - point.x())
        y = self.viewportmapper.to_units(self._mouse_ghost.y() - point.y())
        offset = QtCore.QPoint(x, y)
        self._mouse_ghost = event.pos()
        if self.selection.type == Selection.SUBOBJECTS:
            shift_selection_content(self.selection, offset)
        elif self.selection.type == Selection.ELEMENT:
            shift_element(self.selection.element, offset)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        result = bool(self._mouse_ghost) and bool(self.selection.type)
        self._mouse_ghost = None
        return result

    def tabletMoveEvent(self, event):
        self.mouseMoveEvent(event)
        return True

    def window_cursor_override(self):
        cursor = super().window_cursor_override()
        if cursor:
            return cursor
        if self.layerstack.is_locked:
            return QtCore.Qt.ForbiddenCursor
        if self.element_hover:
            return QtCore.Qt.SizeAllCursor

    def draw(self, painter):
        if self.element_hover is None:
            return
        if self.selection.element == self.element_hover:
            return
        if isinstance(self.element_hover, (QtCore.QPoint, QtCore.QPointF)):
            color = QtGui.QColor(QtCore.Qt.yellow)
            color.setAlpha(75)
            painter.setBrush(color)
            painter.setPen(QtCore.Qt.NoPen)
            point = self.viewportmapper.to_viewport_coords(self.element_hover)
            painter.drawEllipse(point.x() - 20, point.y() - 20, 40, 40)
            return
        rect = get_shape_rect(self.element_hover, self.viewportmapper)
        old_opacity = painter.opacity()
        painter.setOpacity(.5)
        painter.setRenderHint(QtGui.QPainter.Antialiasing, False)
        painter.setBrush(QtCore.Qt.transparent)
        painter.setPen(QtCore.Qt.black)
        painter.drawRect(rect)
        pen = QtGui.QPen(QtCore.Qt.white)
        pen.setWidth(1)
        pen.setStyle(QtCore.Qt.DashLine)
        painter.setPen(pen)
        painter.drawRect(rect)
        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
        painter.setOpacity(old_opacity)


def shift_element(element, offset):
    if isinstance(element, (QtCore.QPoint, QtCore.QPointF)):
        element -= offset
    elif isinstance(element, Stroke):
        for point, _ in element.points:
            point -= offset
    elif isinstance(element, (Arrow, Rectangle, Circle, Text, Line)):
        element.start -= offset
        element.end -= offset
    elif isinstance(element, Bitmap):
        element.rect.moveCenter(element.rect.center() - offset)


def shift_selection_content(selection, offset):
    for element in selection:
        shift_element(element, offset)


class SelectionTool(NavigationTool):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start = None
        self.end = None

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        wrong_button = event.button() != QtCore.Qt.LeftButton
        if self.navigator.space_pressed or wrong_button:
            return
        if self.selection.type == Selection.ELEMENT:
            self.selection.clear()
            self.canvas.selectionChanged.emit()
        self.start = self.viewportmapper.to_units_coords(event.pos())

    def mouseMoveEvent(self, event):
        if super().mouseMoveEvent(event):
            return
        self.end = event.pos()

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        if self.end is None or not self.layerstack.current:
            self.selection.clear()
        else:
            end = self.viewportmapper.to_units_coords(self.end)
            rect = QtCore.QRectF(self.start, end)
            elements = layer_elements_in_rect(self.layerstack.current, rect)
            self.selection.set(elements)
        self.canvas.selectionChanged.emit()
        self.start = None
        self.end = None
        return False

    def tabletMoveEvent(self, event):
        self.mouseMoveEvent(event)

    def window_cursor_override(self):
        cursor = super().window_cursor_override()
        if cursor:
            return cursor
        if self.layerstack.is_locked:
            return QtCore.Qt.ForbiddenCursor
        return QtCore.Qt.CrossCursor

    def draw(self, painter):
        if self.navigator.space_pressed or not self.start or not self.end:
            return
        pen = QtGui.QPen(QtGui.QColor('blue'))
        pen.setWidth(1)
        painter.setPen(pen)
        color = QtGui.QColor('blue')
        color.setAlpha(33)
        painter.setBrush(color)
        start = self.viewportmapper.to_viewport_coords(self.start)
        painter.drawRect(QtCore.QRectF(start, self.end))


def layer_elements_in_rect(layer, rect):
    result = []
    for element in layer:
        if isinstance(element, Stroke):
            result.extend(p for p, _ in element if rect.contains(p))
        elif isinstance(element, (Arrow, Rectangle, Circle, Text, Line)):
            if rect.contains(element.start):
                result.append(element.start)
            if rect.contains(element.end):
                result.append(element.end)
    return result
