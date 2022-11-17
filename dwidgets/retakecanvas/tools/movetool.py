from PySide2 import QtCore, QtGui
from dwidgets.retakecanvas.tools.basetool import NavigationTool
from dwidgets.retakecanvas.selection import selection_rect, Selection
from dwidgets.retakecanvas.shapes import (
    Arrow, Rectangle, Circle, Bitmap, Stroke)


class MoveTool(NavigationTool):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._mouse_ghost = None
        self.element_hover = None

    def mousePressEvent(self, event):
        return_condition = (
            self.navigator.space_pressed or
            self.layerstack.current is None or
            self.layerstack.is_locked)
        if return_condition:
            return
        self._mouse_ghost = event.pos()
        if self.element_hover and self.selection.type != Selection.SUBOBJECTS:
            self.selection.set(self.element_hover)

    def mouseMoveEvent(self, event):
        if super().mouseMoveEvent(event):
            return
        if not self._mouse_ghost:
            if self.selection.type:
                units_pos = self.viewportmapper.to_units_coords(event.pos())
                if selection_rect(self.selection).contains(units_pos):
                    self.element_hover = self.selection
                    return
            point = self.viewportmapper.to_units_coords(event.pos())
            self.element_hover = self.layerstack.find_element_at(point)
            return
        point = event.pos()
        x = self.viewportmapper.to_units(self._mouse_ghost.x() - point.x())
        y = self.viewportmapper.to_units(self._mouse_ghost.y() - point.y())
        offset = QtCore.QPoint(x, y)
        self._mouse_ghost = event.pos()
        if not self.element:
            return
        if isinstance(self.element, Selection):
            shift_selection_content(self.selection, offset)
        shift_element(self.element, offset)

    def mouseReleaseEvent(self, event):
        result = bool(self._mouse_ghost)
        result = result and bool(self.selection or self.element)
        self.element = None
        self._mouse_ghost = None
        return result

    def window_cursor_override(self):
        cursor = super().window_cursor_override()
        if cursor:
            return cursor
        if self.layerstack.is_locked:
            return QtCore.Qt.ForbiddenCursor
        if self.element_hover:
            return QtCore.Qt.SizeAllCursor

    def draw(self, painter):
        if not isinstance(self.element_hover, (QtCore.QPoint, QtCore.QPointF)):
            return
        painter.setBrush(QtCore.Qt.yellow)
        painter.setPen(QtCore.Qt.black)
        point = self.viewportmapper.to_viewport_coords(self.element_hover)
        painter.drawRect(point.x() - 5, point.y() - 5, 10, 10)


def shift_element(element, offset):
    if isinstance(element, (QtCore.QPoint, QtCore.QPointF)):
        element -= offset
    elif isinstance(element, Stroke):
        for point, _ in element.points:
            point -= offset
    elif isinstance(element, (Arrow, Rectangle, Circle)):
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
        wrong_button = event.button() != QtCore.Qt.LeftButton
        if self.navigator.space_pressed or wrong_button:
            return
        self.start = self.viewportmapper.to_units_coords(event.pos())

    def mouseMoveEvent(self, event):
        if super().mouseMoveEvent(event):
            return
        self.end = event.pos()

    def mouseReleaseEvent(self, event):
        if self.end is None or not self.layerstack.current:
            self.selection.clear()
        else:
            end = self.viewportmapper.to_units_coords(self.end)
            rect = QtCore.QRectF(self.start, end)
            elements = layer_elements_in_rect(self.layerstack.current, rect)
            self.selection.set(elements)
        self.start = None
        self.end = None
        return False

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
        elif isinstance(element, (Arrow, Rectangle, Circle)):
            if rect.contains(element.start):
                result.append(element.start)
            if rect.contains(element.end):
                result.append(element.end)
    return result
