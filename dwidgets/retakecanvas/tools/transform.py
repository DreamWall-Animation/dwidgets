from PySide2 import QtCore, QtGui
from dwidgets.retakecanvas.geometry import get_shape_rect
from dwidgets.retakecanvas.tools.basetool import NavigationTool
from dwidgets.retakecanvas.tools.movetool import shift_element, shift_selection_content
from dwidgets.retakecanvas.selection import selection_rect, Selection
from dwidgets.retakecanvas.viewport import ViewportMapper
from dwidgets.retakecanvas.shapes import (
    Arrow, Rectangle, Circle, Bitmap, Stroke, Text, Line)


class TransformTool(NavigationTool):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.element_hover = None
        self.action = None
        self._mouse_ghost = None
        self.current_cusor_pos = None
        self.reference_rect = None

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        return_condition = (
            self.navigator.space_pressed or
            self.layerstack.current is None or
            self.layerstack.is_locked)
        if return_condition:
            return

        self._mouse_ghost = event.pos()

        if not self.current_cusor_pos:
            return

        rects = self.corner_rects()
        if rects:
            self.reference_rect = self.selection_rect()
            if rects[0].contains(event.pos()):
                self.action = 'topleft'
                return

            if rects[2].contains(event.pos()):
                self.action = 'bottomleft'
                return

            if rects[1].contains(event.pos()):
                self.action = 'topright'
                return

            if rects[3].contains(event.pos()):
                self.action = 'bottomright'
                return

        rect = self.selection_rect()
        if rect and self.viewportmapper.to_viewport_rect(rect).contains(event.pos()):
            self.action = 'move'
            self.canvas.selectionChanged.emit()
            return

        if self.element_hover:
            self.selection.set(self.element_hover)
            self.action = 'move'
            self.canvas.selectionChanged.emit()
            return

        self.selection.clear()
        self.canvas.selectionChanged.emit()

    def mouseMoveEvent(self, event):
        if super().mouseMoveEvent(event):
            return

        self.current_cusor_pos = event.pos()
        if not self._mouse_ghost:
            self.set_hover_element(event.pos())
            return

        if self.action in ('topleft', 'topright', 'bottomleft', 'bottomright'):
            rect = QtCore.QRectF(self.reference_rect)
            point = self.viewportmapper.to_units_coords(event.pos())
            set_corner(rect, point, corner=self.action)
            resize_selection(self.selection, self.reference_rect, rect)
            self.reference_rect = rect

        if self.action == 'move':
            point = event.pos()
            x = self.viewportmapper.to_units(self._mouse_ghost.x() - point.x())
            y = self.viewportmapper.to_units(self._mouse_ghost.y() - point.y())
            offset = QtCore.QPoint(x, y)
            self._mouse_ghost = event.pos()
            if self.selection.type == Selection.SUBOBJECTS:
                shift_selection_content(self.selection, offset)
            elif self.selection.type == Selection.ELEMENT:
                shift_element(self.selection.element, offset)

    def set_hover_element(self, point):
        if self.selection.type:
            units_pos = self.viewportmapper.to_units_coords(point)
            rect = selection_rect(self.selection)
            if rect and rect.contains(units_pos):
                self.element_hover = self.selection
                return
        point = self.viewportmapper.to_units_coords(point)
        self.element_hover = self.layerstack.find_element_at(point)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        result = bool(self._mouse_ghost) and bool(self.selection.type)
        self._mouse_ghost = None
        self.action = None
        self.reference_rect = None
        return result

    def window_cursor_override(self):
        cursor = super().window_cursor_override()
        if cursor:
            return cursor
        if self.layerstack.is_locked:
            return QtCore.Qt.ForbiddenCursor
        if not self.current_cusor_pos:
            return

        if self.action == 'topleft':
            return QtCore.Qt.SizeFDiagCursor
        if self.action == 'bottomleft':
            return QtCore.Qt.SizeBDiagCursor
        if self.action == 'topright':
            return QtCore.Qt.SizeBDiagCursor
        if self.action == 'bottomright':
            return QtCore.Qt.SizeFDiagCursor
        if self.action == 'move':
            return QtCore.Qt.SizeAllCursor

        rects = self.corner_rects()
        if rects:
            if rects[0].contains(self.current_cusor_pos):
                return QtCore.Qt.SizeFDiagCursor
            if rects[2].contains(self.current_cusor_pos):
                return QtCore.Qt.SizeBDiagCursor
            if rects[1].contains(self.current_cusor_pos):
                return QtCore.Qt.SizeBDiagCursor
            if rects[3].contains(self.current_cusor_pos):
                return QtCore.Qt.SizeFDiagCursor

        if self.element_hover:
            return QtCore.Qt.SizeAllCursor

    def selection_rect(self):
        rect = selection_rect(self.selection)
        if not rect:
            rect = get_shape_rect(self.selection.element, ViewportMapper())
        return rect

    def corner_rects(self):
        rect = self.selection_rect()
        if not rect:
            return
        rect = self.viewportmapper.to_viewport_rect(rect)
        return (
            get_rect_from_point(rect.topLeft(), 4),
            get_rect_from_point(rect.topRight(), 4),
            get_rect_from_point(rect.bottomLeft(), 4),
            get_rect_from_point(rect.bottomRight(), 4))

    def draw(self, painter):
        if not self.selection:
            return

        painter.setRenderHint(QtGui.QPainter.Antialiasing, False)
        painter.setPen(QtCore.Qt.black)
        painter.setBrush(QtCore.Qt.white)
        for rect in self.corner_rects() or []:
            painter.drawRect(rect)
        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)


def get_rect_from_point(point, size):
    return QtCore.QRect(
        point.x() - size, point.y() - size, size * 2, size * 2)


def resize_selection(selection, reference_rect, rect):
    if selection.type == Selection.ELEMENT:
        element = selection.element
        if isinstance(element, Bitmap):
            element.rect = rect
            return
        if isinstance(element, (Arrow, Rectangle, Circle, Bitmap, Text, Line)):
            points = (element.start, element.end)
        elif isinstance(element, Stroke):
            points = [p[0] for p in element.points]
    elif selection.type == Selection.SUBOBJECTS:
        points = selection

    for point in points:
        x = relative(
            point.x(),
            in_min=reference_rect.left(),
            in_max=reference_rect.right(),
            out_min=rect.left(),
            out_max=rect.right())
        point.setX(x)
        y = relative(
            point.y(),
            in_min=reference_rect.top(),
            in_max=reference_rect.bottom(),
            out_min=rect.top(),
            out_max=rect.bottom())
        point.setY(y)


def set_corner(rect, point, corner):
    if corner == 'topleft':
        x = min((rect.right() - 0.5, point.x()))
        y = min((rect.bottom() - 0.5, point.y()))
        rect.setTopLeft(QtCore.QPointF(x, y))
    if corner == 'topright':
        x = max((rect.left() + 0.5, point.x()))
        y = min((rect.bottom() - 0.5, point.y()))
        rect.setTopRight(QtCore.QPointF(x, y))
    if corner == 'bottomleft':
        x = min((rect.right() - 0.5, point.x()))
        y = max((rect.top() + 0.5, point.y()))
        rect.setBottomLeft(QtCore.QPointF(x, y))
    if corner == 'bottomright':
        x = max((rect.left() + 0.5, point.x()))
        y = max((rect.top() + 0.5, point.y()))
        rect.setBottomRight(QtCore.QPointF(x, y))


def relative(value, in_min, in_max, out_min, out_max):
    """
    this function resolve simple equation and return the unknown value
    in between two values.
    a, a" = in_min, out_min
    b, b " = out_max, out_max
    c = value
    ? is the unknown processed by function.
    a --------- c --------- b
    a" --------------- ? ---------------- b"
    """
    factor = float((value - in_min)) / (in_max - in_min)
    width = out_max - out_min
    return out_min + (width * (factor))
