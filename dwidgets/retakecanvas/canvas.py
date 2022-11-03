from PySide2 import QtCore, QtWidgets, QtGui
from dwidgets.retakecanvas.tools import NavigationTool
from dwidgets.retakecanvas.shapes import Circle, Rectangle, Arrow, Stroke
from dwidgets.retakecanvas.viewport import ViewportMapper


class Canvas(QtWidgets.QWidget):
    def __init__(
            self,
            drawcontext,
            layerstack,
            navigator,
            viewportmapper,
            parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.baseimage = None
        self.drawcontext = drawcontext
        self.layerstack = layerstack
        self.navigator = navigator
        self.viewportmapper = viewportmapper
        self.tool = NavigationTool(
            drawcontext=self.drawcontext,
            layerstack=self.layerstack,
            navigator=self.navigator,
            viewportmapper=self.viewportmapper)

    def sizeHint(self):
        if not self.baseimage:
            return QtCore.QSize(300, 300)
        return self.baseimage.size()

    def resizeEvent(self, event):
        self.viewportmapper.viewsize = event.size()

    def reset(self):
        if not self.baseimage:
            return
        rect = QtCore.QRect(
            0, 0, self.baseimage.width(), self.baseimage.height())
        self.viewportmapper.focus(rect)
        self.repaint()

    def set_baseimage(self, image):
        self.baseimage = image
        self.viewportmapper.viewsize = QtCore.QSize(image.size())
        self.repaint()

    def mouseMoveEvent(self, event):
        self.tool.mouseMoveEvent(event)
        self.repaint()

    def mousePressEvent(self, event):
        self.setFocus(QtCore.Qt.MouseFocusReason)
        self.navigator.update(event, pressed=True)
        self.tool.mousePressEvent(event)
        self.repaint()

    def mouseReleaseEvent(self, event):
        self.navigator.update(event, pressed=False)
        result = self.tool.mouseReleaseEvent(event)
        if result is True and self.layerstack.current is not None:
            self.layerstack.add_undo_state()
        self.repaint()

    def keyPressEvent(self, event):
        self.navigator.update(event, pressed=True)
        self.tool.keyPressEvent(event)
        self.repaint()

    def keyReleaseEvent(self, event):
        self.navigator.update(event, pressed=False)
        self.tool.keyReleaseEvent(event)
        self.repaint()

    def tabletEvent(self, event):
        self.tool.tabletEvent(event)
        self.repaint()

    def wheelEvent(self, event):
        self.tool.wheelEvent(event)
        self.repaint()

    def set_tool(self, tool):
        self.tool = tool
        self.repaint()

    def render(self):
        if not self.baseimage:
            return
        image = QtGui.QImage(self.baseimage)
        rect = QtCore.QRect(0, 0, image.width(), image.height())
        painter = QtGui.QPainter(image)
        if self.layerstack.wash_opacity:
            painter.setPen(QtCore.Qt.transparent)
            color = QtGui.QColor(self.layerstack.wash_color)
            color.setAlpha(self.layerstack.wash_opacity)
            painter.setBrush(color)
            painter.drawRect(rect)

        for layer, visible, opacity in self.layerstack:
            if not visible:
                continue
            draw_layer(painter, layer, opacity, ViewportMapper())
        return image

    def paintEvent(self, event):
        if not self.baseimage:
            return

        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        try:
            painter.setBrush(QtCore.Qt.black)
            painter.setPen(QtCore.Qt.transparent)
            painter.drawRect(self.rect())
            painter.setBrush(QtCore.Qt.darkBlue)

            size = self.baseimage.size()
            rect = QtCore.QRectF(0, 0, size.width(), size.height())
            rect = self.viewportmapper.to_viewport_rect(rect)
            painter.drawRect(rect)
            painter.drawImage(rect, self.baseimage)

            if self.layerstack.wash_opacity:
                painter.setPen(QtCore.Qt.transparent)
                color = QtGui.QColor(self.layerstack.wash_color)
                color.setAlpha(self.layerstack.wash_opacity)
                painter.setBrush(color)
                painter.drawRect(rect)

            for layer, visible, opacity in self.layerstack:
                if not visible:
                    continue
                draw_layer(painter, layer, opacity, self.viewportmapper)
        finally:
            painter.end()


def draw_layer(painter, layer, opacity, viewportmapper):
    painter.setOpacity(opacity / 255)
    for element in layer:
        if isinstance(element, Stroke):
            draw_stroke(painter, element, viewportmapper)
        elif isinstance(element, Arrow):
            draw_arrow(painter, element, viewportmapper)
        elif isinstance(element, Circle):
            draw_shape(painter, element, painter.drawEllipse, viewportmapper)
        elif isinstance(element, Rectangle):
            draw_shape(painter, element, painter.drawRect, viewportmapper)
    painter.setOpacity(1)


def draw_shape(painter, shape, drawer, viewportmapper):
    if not shape.is_valid:
        return
    color = QtGui.QColor(shape.color)
    pen = QtGui.QPen(color)
    pen.setCapStyle(QtCore.Qt.RoundCap)
    pen.setJoinStyle(QtCore.Qt.MiterJoin)
    pen.setWidthF(viewportmapper.to_viewport(shape.linewidth))
    painter.setPen(pen)
    painter.setBrush(QtCore.Qt.transparent)
    rect = QtCore.QRectF(
        viewportmapper.to_viewport_coords(shape.start),
        viewportmapper.to_viewport_coords(shape.end))
    drawer(rect)


def draw_arrow(painter, arrow, viewportmapper):
    if not arrow.is_valid:
        return
    line = QtCore.QLineF(
        viewportmapper.to_viewport_coords(arrow.start),
        viewportmapper.to_viewport_coords(arrow.end))
    center = line.p2()
    degrees = line.angle()

    offset = viewportmapper.to_viewport(arrow.headsize)
    triangle = QtGui.QPolygonF([
        QtCore.QPoint(center.x() - offset, center.y() - offset),
        QtCore.QPoint(center.x() + offset, center.y()),
        QtCore.QPoint(center.x() - offset, center.y() + offset),
        QtCore.QPoint(center.x() - offset, center.y() - offset)])

    transform = QtGui.QTransform()
    transform.translate(center.x(), center.y())
    transform.rotate(-degrees)
    transform.translate(-center.x(), -center.y())
    triangle = transform.map(triangle)
    path = QtGui.QPainterPath()
    path.setFillRule(QtCore.Qt.WindingFill)
    path.addPolygon(triangle)

    color = QtGui.QColor(arrow.color)
    pen = QtGui.QPen(color)
    pen.setCapStyle(QtCore.Qt.RoundCap)
    pen.setJoinStyle(QtCore.Qt.MiterJoin)
    pen.setWidthF(viewportmapper.to_viewport(arrow.tailwidth))
    painter.setPen(pen)
    painter.setBrush(color)
    painter.drawLine(line)
    painter.drawPath(path)


def draw_stroke(painter, stroke, viewportmapper):
    pen = QtGui.QPen(QtGui.QColor(stroke.color))
    pen.setCapStyle(QtCore.Qt.RoundCap)
    start = None
    for point, size in stroke:
        if start is None:
            start = viewportmapper.to_viewport_coords(point)
            continue
        pen.setWidthF(viewportmapper.to_viewport(size))
        painter.setPen(pen)
        end = viewportmapper.to_viewport_coords(point)
        painter.drawLine(start, end)
        start = end
