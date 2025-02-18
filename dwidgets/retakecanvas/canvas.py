import os
import time
from PySide2 import QtCore, QtWidgets, QtGui
from dwidgets.retakecanvas.geometry import (
    combined_rect, get_global_rect, get_images_rects, get_shape_rect)
from dwidgets.retakecanvas.model import RetakeCanvasModel
from dwidgets.retakecanvas.tools import NavigationTool
from dwidgets.retakecanvas.selection import selection_rect, Selection
from dwidgets.retakecanvas.shapes import (
    Circle, Rectangle, Arrow, Stroke, Bitmap, Text, Line)
from dwidgets.retakecanvas.viewport import ViewportMapper, set_zoom


def disable_if_model_locked(method):
    def decorator(self, *args, **kwargs):
        if self.model.locked:
            return
        return method(self, *args, **kwargs)
    return decorator


class Canvas(QtWidgets.QWidget):
    isUpdated = QtCore.Signal()
    selectionChanged = QtCore.Signal()
    zoomChanged = QtCore.Signal()

    def __init__(self, model, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setAcceptDrops(True)
        self.is_using_tablet = False
        self.last_repaint_evaluation_time = 0
        self.last_repaint_call_time = time.time()
        self.captime = .1

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
            url.toLocalFile()
            for url in event.mimeData().urls()]
        if not paths:
            self.add_image_layer(paths)
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
        self.zoomChanged.emit()
        self.repaint()

    def enterEvent(self, _):
        self.update_cursor()

    def leaveEvent(self, _):
        QtWidgets.QApplication.restoreOverrideCursor()

    def mouseMoveEvent(self, event):
        if self.is_using_tablet:
            return
        self.tool.mouseMoveEvent(event)
        self.update_cursor()
        self.repaint()

    def mousePressEvent(self, event):
        self.setFocus(QtCore.Qt.MouseFocusReason)
        self.model.navigator.update(event, pressed=True)
        result = self.tool.mousePressEvent(event)
        self.update_cursor()
        if result:
            self.repaint()

    def mouseReleaseEvent(self, event):
        if self.is_using_tablet:
            return
        self.model.navigator.update(event, pressed=False)
        result = self.tool.mouseReleaseEvent(event)
        if result is True and self.model.layerstack.current is not None:
            self.model.add_undo_state()
            self.isUpdated.emit()
        self.last_repaint_evaluation_time = 0
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
        if event.type() == QtGui.QTabletEvent.TabletPress:
            self.is_using_tablet = True
            self.timer.setInterval(15)
            event.accept()
            return
        if event.type() == QtGui.QTabletEvent.TabletRelease:
            self.is_using_tablet = False
            self.timer.setInterval(300)
            event.accept()
            return
        self.tool.tabletMoveEvent(event)
        self.update_cursor()

    def cap_repaint(self):
        now = time.time()
        delta = now - self.last_repaint_call_time
        self.captime = max(0.02, delta)
        if delta < self.captime:
            return
        self.last_repaint_call_time = now
        start_time = time.time()
        self.repaint()
        self.last_repaint_evaluation_time = time.time() - start_time

    def wheelEvent(self, event):
        self.tool.wheelEvent(event)
        self.zoomChanged.emit()
        self.repaint()

    def set_zoom(self, factor):
        set_zoom(self.model.viewportmapper, factor, self.mapFromGlobal(QtGui.QCursor.pos()))

    @disable_if_model_locked
    def set_tool(self, tool):
        if self.tool.is_dirty:
            self.model.add_undo_state()
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

    def render(
            self,
            painter: QtGui.QPainter=None,
            model: RetakeCanvasModel=None,
            viewportmapper: ViewportMapper=None):
        model = model or self.model
        viewportmapper = viewportmapper or ViewportMapper()
        baseimage = model.baseimage

        if not baseimage:
            self.draw_empty(painter)
            return

        size = model.baseimage.size()
        baseimage_rect = QtCore.QRectF(0, 0, size.width(), size.height())
        rects = get_images_rects(
            model.baseimage,
            model.imagestack,
            layout=model.imagestack_layout) + [baseimage_rect]

        if not painter:
            layer_rects = [
                get_shape_rect(shape, viewportmapper)
                for layer in model.layerstack.layers for shape in layer]
            output_rect = combined_rect(rects + layer_rects)
            viewportmapper.origin = output_rect.topLeft()
            w, h = int(output_rect.width()), int(output_rect.height())
            image = QtGui.QImage(w, h, QtGui.QImage.Format_RGB32)
            painter = QtGui.QPainter(image)
        else:
            image = None

        self.draw_images(painter, rects, viewportmapper, model=model)

        if model.wash_opacity:
            painter.setPen(QtCore.Qt.transparent)
            color = QtGui.QColor(model.wash_color)
            color.setAlpha(model.wash_opacity)
            painter.setBrush(color)
            painter.drawRect(viewportmapper.to_viewport_rect(baseimage_rect))

        if model.layerstack.solo is not None:
            layer, _, blend_mode, _, visible, opacity = model.layerstack[
                model.layerstack.solo]
            draw_layer(painter, layer, blend_mode, opacity, viewportmapper)
            return image

        for layer, _, blend_mode, _, visible, opacity in model.layerstack:
            if not visible:
                continue
            draw_layer(painter, layer, blend_mode, opacity, viewportmapper)

        return image

    def paintEvent(self, event):
        if not self.model.baseimage:
            return
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        try:
            painter.setPen(QtCore.Qt.black)
            painter.drawRect(event.rect())
            painter.setBrush(QtCore.Qt.black)
            painter.setPen(QtCore.Qt.transparent)
            painter.drawRect(self.rect())
            painter.setBrush(QtCore.Qt.darkBlue)
            self.render(painter, self.model, self.model.viewportmapper)
            draw_selection(
                painter,
                self.model.selection,
                self.model.viewportmapper)
            self.tool.draw(painter)
        finally:
            painter.end()

    def draw_empty(self, painter):
        brush = QtGui.QBrush(QtCore.Qt.grey)
        brush.setStyle(QtCore.Qt.BDiagPattern)
        painter.setBursh(brush)
        pen = QtGui.QPen(QtCore.Qt.black)
        pen.setWidth(3)
        painter.setPen(pen)
        painter.drawRect(self.rect())

    def draw_images(
            self, painter, rects, viewportmapper, model=None):
        model = model or self.model
        if model.imagestack_layout != RetakeCanvasModel.STACKED:
            images = self.model.imagestack + [model.baseimage]
            for image, rect in zip(images, rects):
                rect = viewportmapper.to_viewport_rect(rect)
                image = image.scaled(
                    rect.size().toSize(),
                    QtCore.Qt.KeepAspectRatio,
                    QtCore.Qt.SmoothTransformation)
                painter.drawImage(rect, image)
        else:
            images = list(reversed(model.imagestack))
            images += [model.baseimage]
            wipes = model.imagestack_wipes[:]
            wipes.append(model.baseimage_wipes)
            for image, rect, wipe in zip(images, rects, wipes):
                mode = QtCore.Qt.KeepAspectRatio
                image = image.scaled(rect.size().toSize(), mode)
                image = image.copy(wipe)
                wipe = viewportmapper.to_viewport_rect(wipe)
                painter.drawImage(wipe, image)


def draw_layer(
        painter: QtGui.QPainter, layer, blend_mode, opacity, viewportmapper):
    painter.setOpacity(opacity / 255)
    painter.setCompositionMode(blend_mode)
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
        elif isinstance(element, Text):
            draw_text(painter, element, viewportmapper)
        elif isinstance(element, Line):
            draw_line(painter, element, viewportmapper)
    painter.setOpacity(1)
    painter.setCompositionMode(QtGui.QPainter.CompositionMode_SourceOver)


def _get_text_alignment_flags(alignment):
    return [
        (QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop),
        (QtCore.Qt.AlignRight | QtCore.Qt.AlignTop),
        (QtCore.Qt.AlignHCenter | QtCore.Qt.AlignTop),
        (QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter),
        (QtCore.Qt.AlignCenter),
        (QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter),
        (QtCore.Qt.AlignLeft | QtCore.Qt.AlignBottom),
        (QtCore.Qt.AlignHCenter | QtCore.Qt.AlignBottom),
        (QtCore.Qt.AlignRight | QtCore.Qt.AlignBottom)][alignment]


def draw_text(painter, text, viewportmapper):
    if not text.is_valid:
        return
    rect = get_shape_rect(text, viewportmapper)
    if text.filled:
        color = text.bgcolor if text.filled else QtCore.Qt.transparent
        color = QtGui.QColor(color)
        if text.bgopacity != 255:
            color.setAlpha(text.bgopacity)
        painter.setPen(QtCore.Qt.transparent)
        painter.setBrush(color)
        painter.drawRect(rect)

    painter.setBrush(QtCore.Qt.transparent)
    painter.setPen(QtGui.QColor(text.color))
    font = QtGui.QFont()
    font.setPointSizeF(viewportmapper.to_viewport(text.text_size) * 10)
    painter.setFont(font)
    alignment = _get_text_alignment_flags(text.alignment)
    option = QtGui.QTextOption()
    option.setWrapMode(QtGui.QTextOption.WrapAtWordBoundaryOrAnywhere)
    option.setAlignment(alignment)
    painter.drawText(rect, text.text, option)


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
    state = shape.filled
    color = shape.bgcolor if state else QtCore.Qt.transparent
    color = QtGui.QColor(color)
    if shape.bgopacity != 255:
        color.setAlpha(shape.bgopacity)
    painter.setBrush(color)
    rect = QtCore.QRectF(
        viewportmapper.to_viewport_coords(shape.start),
        viewportmapper.to_viewport_coords(shape.end))
    drawer(rect)


def draw_line(painter, line, viewportmapper):
    if not line.is_valid:
        return
    color = QtGui.QColor(line.color)
    pen = QtGui.QPen(color)
    pen.setCapStyle(QtCore.Qt.RoundCap)
    pen.setJoinStyle(QtCore.Qt.MiterJoin)
    pen.setWidthF(viewportmapper.to_viewport(line.linewidth))
    painter.setPen(pen)
    painter.setBrush(color)
    qline = QtCore.QLineF(
        viewportmapper.to_viewport_coords(line.start),
        viewportmapper.to_viewport_coords(line.end))
    painter.drawLine(qline)


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
    if selection.type == Selection.SUBOBJECTS:
        draw_subobjects_selection(painter, selection, viewportmapper)
    elif selection.type == Selection.ELEMENT:
        draw_element_selection(painter, selection, viewportmapper)


def draw_element_selection(painter, selection, viewportmapper):
    rect = get_shape_rect(selection.element, viewportmapper)
    if rect is None:
        return
    painter.setRenderHint(QtGui.QPainter.Antialiasing, False)
    painter.setPen(QtCore.Qt.yellow)
    painter.setBrush(QtCore.Qt.NoBrush)
    painter.drawRect(rect)
    painter.setRenderHint(QtGui.QPainter.Antialiasing, True)


def draw_subobjects_selection(painter, selection, viewportmapper):
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
