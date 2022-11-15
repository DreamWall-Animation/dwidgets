import os
import sys
import math
import time
from PySide2 import QtCore, QtWidgets, QtGui
from dwidgets.retakecanvas.model import RetakeCanvasModel
from dwidgets.retakecanvas.tools import NavigationTool
from dwidgets.retakecanvas.selection import selection_rect
from dwidgets.retakecanvas.shapes import (
    Circle, Rectangle, Arrow, Stroke, Bitmap)
from dwidgets.retakecanvas.viewport import ViewportMapper


def disable_if_model_locked(method):
    def decorator(self, *args, **kwargs):
        if self.model.locked:
            return
        return method(self, *args, **kwargs)
    return decorator


class Canvas(QtWidgets.QWidget):
    isUpdated = QtCore.Signal()

    def __init__(self, model, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setAcceptDrops(True)

        self.model = model
        self.selection = model.selection
        self.tool = NavigationTool(canvas=self, model=self.model)
        self.timer = QtCore.QTimer(self)
        self.timer.start(300)
        self.timer.timeout.connect(self.repaint)

    def set_model(self, model):
        self.model = model
        size = model.baseimage.size()
        self.model.viewportmapper.viewsize = QtCore.QSize(size)
        self.repaint()

    @disable_if_model_locked
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            return event.accept()

    @disable_if_model_locked
    def dropEvent(self, event):
        paths = [
            os.path.expandvars(url.path())
            for url in event.mimeData().urls()]
        images = [QtGui.QImage(p) for p in paths]
        images = [image for image in images if not image.isNull()]
        for image in images:
            self.model.append_image(image)
        self.model.add_undo_state()
        self.repaint()
        self.isUpdated.emit()

    def sizeHint(self):
        if not self.model.baseimage:
            return QtCore.QSize(300, 300)
        return self.model.baseimage.size()

    def resizeEvent(self, event):
        self.model.viewportmapper.viewsize = event.size()
        size = (event.size() - event.oldSize()) / 2
        offset = QtCore.QPointF(size.width(), size.height())
        self.model.viewportmapper.origin -= offset
        self.repaint()

    def reset(self):
        if not self.model.baseimage:
            return
        self.model.viewportmapper.viewsize = self.size()
        rect = get_global_rect(
            self.model.baseimage,
            self.model.imagestack,
            self.model.imagestack_layout)
        self.model.viewportmapper.focus(rect)
        self.repaint()

    def enterEvent(self, _):
        self.update_cursor()

    def leaveEvent(self, _):
        QtWidgets.QApplication.restoreOverrideCursor()

    def mouseMoveEvent(self, event):
        self.tool.mouseMoveEvent(event)
        self.update_cursor()
        self.repaint()

    def mousePressEvent(self, event):
        self.setFocus(QtCore.Qt.MouseFocusReason)
        self.model.navigator.update(event, pressed=True)
        self.tool.mousePressEvent(event)
        self.update_cursor()
        self.repaint()

    def mouseReleaseEvent(self, event):
        self.model.navigator.update(event, pressed=False)
        result = self.tool.mouseReleaseEvent(event)
        if result is True and self.model.layerstack.current is not None:
            self.model.add_undo_state()
            self.isUpdated.emit()
        self.update_cursor()
        self.repaint()

    def keyPressEvent(self, event):
        if event.isAutoRepeat():
            return
        self.model.navigator.update(event, pressed=True)
        self.tool.keyPressEvent(event)
        self.update_cursor()
        self.repaint()

    def keyReleaseEvent(self, event):
        if event.isAutoRepeat():
            return
        self.model.navigator.update(event, pressed=False)
        self.tool.keyReleaseEvent(event)
        self.update_cursor()
        self.repaint()

    def tabletEvent(self, event):
        self.tool.tabletEvent(event)
        self.repaint()

    def wheelEvent(self, event):
        self.tool.wheelEvent(event)
        self.repaint()

    @disable_if_model_locked
    def set_tool(self, tool):
        self.tool = tool
        self.update_cursor()
        self.repaint()

    def update_cursor(self):
        if not self.tool.window_cursor_visible():
            override = QtCore.Qt.BlankCursor
        else:
            override = self.tool.window_cursor_override()

        override = override or QtCore.Qt.ArrowCursor
        current_override = QtWidgets.QApplication.overrideCursor()

        if not current_override:
            QtWidgets.QApplication.setOverrideCursor(override)
            return

        if current_override and current_override.shape() != override:
            # Need to restore override because overrides can be nested.
            QtWidgets.QApplication.restoreOverrideCursor()
            QtWidgets.QApplication.setOverrideCursor(override)

    def render(self, layerstack=None, baseimage=None):
        layerstack = layerstack or self.model.layerstack
        baseimage = baseimage or self.model.baseimage
        if not baseimage:
            return

        image = QtGui.QImage(baseimage)
        rect = QtCore.QRect(0, 0, image.width(), image.height())
        painter = QtGui.QPainter(image)
        if layerstack.wash_opacity:
            painter.setPen(QtCore.Qt.transparent)
            color = QtGui.QColor(layerstack.wash_color)
            color.setAlpha(layerstack.wash_opacity)
            painter.setBrush(color)
            painter.drawRect(rect)

        for layer, _, _, visible, opacity in layerstack:
            if not visible:
                continue
            draw_layer(painter, layer, opacity, ViewportMapper())

        return image

    def paintEvent(self, _):
        if not self.model.baseimage:
            return

        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        try:
            painter.setBrush(QtCore.Qt.black)
            painter.setPen(QtCore.Qt.transparent)
            painter.drawRect(self.rect())
            painter.setBrush(QtCore.Qt.darkBlue)

            size = self.model.baseimage.size()
            rect = QtCore.QRectF(0, 0, size.width(), size.height())
            rects = get_images_rects(
                self.model.baseimage,
                self.model.imagestack,
                layout=self.model.imagestack_layout) + [rect]

            if self.model.imagestack_layout != RetakeCanvasModel.STACKED:
                images = self.model.imagestack + [self.model.baseimage]
                for image, rect in zip(images, rects):
                    rect = self.model.viewportmapper.to_viewport_rect(rect)
                    painter.drawImage(rect, image)
            else:
                images = list(reversed(self.model.imagestack))
                images += [self.model.baseimage]
                wipes = self.model.imagestack_wipes[:]
                wipes.append(self.model.baseimage_wipes)
                for image, rect, wipe in zip(images, rects, wipes):
                    mode = QtCore.Qt.KeepAspectRatio
                    image = image.scaled(rect.size().toSize(), mode)
                    image = image.copy(wipe)
                    wipe = self.model.viewportmapper.to_viewport_rect(wipe)
                    painter.drawImage(wipe, image)

            if self.model.wash_opacity:
                painter.setPen(QtCore.Qt.transparent)
                color = QtGui.QColor(self.model.wash_color)
                color.setAlpha(self.model.wash_opacity)
                painter.setBrush(color)
                painter.drawRect(rect)

            for layer, _, _, visible, opacity in self.model.layerstack:
                if not visible:
                    continue
                draw_layer(painter, layer, opacity, self.model.viewportmapper)

            draw_selection(
                painter,
                self.model.selection,
                self.model.viewportmapper)
            self.tool.draw(painter)
        finally:
            painter.end()


def get_images_rects(baseimage, stackimages, layout=0):
    """
    layout: RetakeCanvasModel.GRID | STACKED | HORIZONTAL | VERTICAL
    """
    images = [baseimage] + stackimages
    rects = [
        QtCore.QRectF(0, 0, image.size().width(), image.size().height())
        for image in images]
    last_rect = None
    if layout == RetakeCanvasModel.HORIZONTAL:
        for rect in rects:
            if not last_rect:
                last_rect = rect
                continue
            rect.moveTopLeft(last_rect.topRight())
            last_rect = rect
    elif layout == RetakeCanvasModel.VERTICAL:
        for rect in rects:
            if not last_rect:
                last_rect = rect
                continue
            rect.moveTopLeft(last_rect.bottomLeft())
            last_rect = rect
    elif layout == RetakeCanvasModel.GRID:
        set_grid_layout(rects)
    return rects[1:]


def get_global_rect(baseimage, stackimages, layout=0):
    image_rect = QtCore.QRectF(0, 0, baseimage.width(), baseimage.height())
    rects = get_images_rects(baseimage, stackimages, layout)
    rects.append(image_rect)
    left, top = sys.maxsize, sys.maxsize
    right, bottom = -sys.maxsize, -sys.maxsize
    for rect in rects:
        left = min((rect.left(), left))
        top = min((rect.top(), top))
        right = max((rect.right(), right))
        bottom = max((rect.bottom(), bottom))
    return QtCore.QRectF(left, top, right - left, bottom - top)


def set_grid_layout(viewport_rects):
    colcount = math.ceil(math.sqrt(len(viewport_rects)))
    width = max(rect.width() for rect in viewport_rects)
    height = max(rect.height() for rect in viewport_rects)
    top, left = viewport_rects[0].top(), viewport_rects[0].left()
    for i, rect in enumerate(viewport_rects):
        if not i:
            left += width
            continue
        if i % colcount == 0:
            left = viewport_rects[0].left()
            top += height
        rect.moveTopLeft(QtCore.QPointF(left, top))
        left += width
    return


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
        elif isinstance(element, Bitmap):
            draw_bitmap(painter, element, viewportmapper)
    painter.setOpacity(1)


def draw_bitmap(painter, bitmap, viewportmapper):
    painter.setBrush(QtCore.Qt.transparent)
    painter.setPen(QtCore.Qt.transparent)
    rect = viewportmapper.to_viewport_rect(bitmap.rect)
    painter.drawImage(rect, bitmap.image)


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


def draw_selection(painter, selection, viewportmapper):
    if not selection:
        return
    painter.setRenderHint(QtGui.QPainter.Antialiasing, False)
    painter.setBrush(QtCore.Qt.yellow)
    painter.setPen(QtCore.Qt.black)
    for element in selection:
        if isinstance(element, (QtCore.QPoint, QtCore.QPointF)):
            point = viewportmapper.to_viewport_coords(element)
            painter.drawRect(point.x() - 2, point.y() - 2, 4, 4)

    rect = viewportmapper.to_viewport_rect(selection_rect(selection))
    painter.setBrush(QtCore.Qt.transparent)
    painter.setPen(QtCore.Qt.black)
    painter.drawRect(rect)
    pen = QtGui.QPen(QtCore.Qt.white)
    pen.setWidth(1)
    pen.setStyle(QtCore.Qt.DashLine)
    offset = round((time.time() * 10) % 10, 3)
    pen.setDashOffset(offset)
    painter.setPen(pen)
    painter.drawRect(rect)
    painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
