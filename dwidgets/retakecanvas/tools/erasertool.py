import itertools
from PySide2 import QtCore, QtGui
from dwidgets.retakecanvas.shapes import Stroke
from dwidgets.retakecanvas.mathutils import distance_qline_qpoint
from dwidgets.retakecanvas.tools.basetool import NavigationTool


class EraserTool(NavigationTool):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pressure = 1
        self._mouse_buffer = None

    def mousePressEvent(self, event):
        if not self.layerstack.current:
            return
        self._mouse_buffer = event.pos()

    def mouseMoveEvent(self, event):
        if super().mouseMoveEvent(event) or not self._mouse_buffer:
            return
        p1 = self.viewportmapper.to_units_coords(self._mouse_buffer)
        p2 = self.viewportmapper.to_units_coords(event.pos())
        line = QtCore.QLineF(p1, p2)
        width = (self.drawcontext.size * self.pressure) / 2
        layer = self.layerstack.current
        points_to_erase = filter_point_to_erase_from_line(line, width, layer)
        erase_on_layer(points_to_erase, self.layerstack.current)
        self._mouse_buffer = event.pos()

    def mouseReleaseEvent(self, _):
        result = bool(self._mouse_buffer)
        self._mouse_buffer = None
        return result

    def tabletMoveEvent(self, event):
        self.pressure = event.pressure()
        self.mouseMoveEvent(event)

    def window_cursor_visible(self):
        return False

    def draw(self, painter):
        if self.navigator.space_pressed:
            return
        radius = self.viewportmapper.to_viewport(self.drawcontext.size)
        painter.setCompositionMode(QtGui.QPainter.CompositionMode_Difference)
        painter.setPen(QtCore.Qt.white)
        painter.setBrush(QtCore.Qt.transparent)
        pos = self.canvas.mapFromGlobal(QtGui.QCursor.pos())
        painter.drawEllipse(pos, radius / 2, radius / 2)


def split_stroke_data(stroke, points):
    all_points = [p for p, _ in stroke]
    indexes = [
        i for (i, p1), p2 in itertools.product(enumerate(all_points), points)
        if p1 is p2]
    indexes = [i for i in range(len(stroke)) if i not in indexes]
    if not indexes:
        return []
    groups = []
    buff_index = None
    for index in indexes:
        if buff_index is None:
            group = [stroke[index]]
            buff_index = index
            continue
        if index - buff_index == 1:
            group.append(stroke[index])
            buff_index = index
            continue
        groups.append(group)
        group = []
        buff_index = index
    groups.append(group)
    return [group for group in groups if len(group) > 1]


def filter_point_to_erase_from_line(line, width, layer):
    result = [
        (s, i, [p for p, _ in s if distance_qline_qpoint(line, p) < width])
        for i, s in enumerate(layer) if isinstance(s, Stroke)]
    return [data for data in result if data[2]]


def get_point_to_erase(points, layer):
    result = [
        (s, i, [p for p, _ in s if p in points])
        for i, s in enumerate(layer) if isinstance(s, Stroke)]
    return [data for data in result if data[2]]


def erase_on_layer(points_to_erase, layer):
    stroke_actions = []
    for stroke, index, points in points_to_erase:
        data = split_stroke_data(stroke, points)
        if not data:
            stroke_actions.append(('delete', index, stroke))
            continue
        stroke.points = data[0]
        if len(data) > 1:
            for group in data[1:]:
                if not group:
                    continue
                stroke = stroke.copy()
                stroke.points = group
                stroke_actions.append(('new', index, stroke))

    if not stroke_actions:
        return

    for action, i, stroke in reversed(stroke_actions):
        if action == 'new':
            layer.insert(i, stroke)
        elif action == 'delete':
            del layer[i]
