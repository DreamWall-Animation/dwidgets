from PySide2 import QtCore, QtWidgets, QtGui
from dwidgets.retakecanvas.selection import selection_rect, Selection
from dwidgets.retakecanvas.shapes import (
    Stroke, Arrow, Rectangle, Circle, Bitmap)


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

    def __init__(
            self,
            canvas=None,
            drawcontext=None,
            layerstack=None,
            navigator=None,
            selection=None,
            viewportmapper=None):
        self.canvas = canvas
        self.drawcontext = drawcontext
        self.layerstack = layerstack
        self.navigator = navigator
        self.selection = selection
        self.viewportmapper = viewportmapper

    def keyPressEvent(self, event):
        ...

    def keyReleaseEvent(self, event):
        ...

    def mousePressEvent(self, event):
        ...

    def mouseMoveEvent(self, event):
        ...

    def mouseReleaseEvent(self, event) -> bool:
        "Record an undo state if it returns True."
        ...

    def mouseWheelEvent(self, event):
        ...

    def tabletEvent(self, event):
        ...

    def wheelEvent(self, event):
        ...

    def draw(self, painter):
        ...

    def window_cursor_visible(self):
        return True

    def window_cursor_override(self):
        return


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

    def window_cursor_visible(self):
        return True

    def window_cursor_override(self):
        space = self.navigator.space_pressed
        left = self.navigator.left_pressed
        if space and not left:
            return QtCore.Qt.OpenHandCursor
        if space and left:
            return QtCore.Qt.ClosedHandCursor


class MoveTool(NavigationTool):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._mouse_ghost = None
        self.element_hover = None
        self.element = None

    def mousePressEvent(self, event):
        if self.navigator.space_pressed or self.layerstack.current is None:
            return
        self._mouse_ghost = event.pos()
        self.element = self.element_hover
        if self.selection and self.selection != self.element:
            self.selection.clear()

    def mouseMoveEvent(self, event):
        if super().mouseMoveEvent(event):
            return
        if not self._mouse_ghost:
            if self.selection:
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
        space = self.navigator.space_pressed
        left = self.navigator.left_pressed
        if space and not left:
            return QtCore.Qt.OpenHandCursor
        if space and left:
            return QtCore.Qt.ClosedHandCursor
        if self.element_hover:
            return QtCore.Qt.SizeAllCursor

    def draw(self, painter):
        if isinstance(self.element_hover, (QtCore.QPoint, QtCore.QPointF)):
            painter.setRenderHints(QtGui.QPainter.Antialiasing, False)
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
        if self.navigator.space_pressed or event.button() != QtCore.Qt.LeftButton:
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
        space = self.navigator.space_pressed
        left = self.navigator.left_pressed
        if space and not left:
            return QtCore.Qt.OpenHandCursor
        if space and left:
            return QtCore.Qt.ClosedHandCursor
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


class ShapeTool(NavigationTool):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.shape_cls = Arrow
        self.shape = None

    def mousePressEvent(self, event):
        if self.navigator.space_pressed or self.layerstack.current is None:
            return
        self.selection.clear()
        self.shape = self.shape_cls(
            start=self.viewportmapper.to_units_coords(event.pos()),
            color=self.drawcontext.color,
            linewidth=self.drawcontext.size)
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
        self.headsize = 10
        self.tailwidth = 10

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

    def window_cursor_visible(self):
        return self.navigator.space_pressed

    def window_cursor_override(self):
        space = self.navigator.space_pressed
        left = self.navigator.left_pressed
        if space and not left:
            return QtCore.Qt.OpenHandCursor
        if space and left:
            return QtCore.Qt.ClosedHandCursor

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
        if self.navigator.space_pressed or self.layerstack.current is None:
            return
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
        space = self.navigator.space_pressed
        left = self.navigator.left_pressed
        if space and not left:
            return QtCore.Qt.OpenHandCursor
        if space and left:
            return QtCore.Qt.ClosedHandCursor

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
        point = self.viewportmapper.to_viewport_coords(self.stroke.points[-1][0])
        painter.drawLine(pos, point)


def zoom(viewportmapper, factor, reference):
    abspoint = viewportmapper.to_units_coords(reference)
    if factor > 0:
        viewportmapper.zoomin(abs(factor))
    else:
        viewportmapper.zoomout(abs(factor))
    relcursor = viewportmapper.to_viewport_coords(abspoint)
    vector = relcursor - reference
    viewportmapper.origin = viewportmapper.origin + vector