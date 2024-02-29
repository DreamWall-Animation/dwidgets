
from PySide2 import QtCore
from PySide2.QtGui import QPainter
from dwidgets.retakecanvas.shapes import (
    Stroke, Arrow, Rectangle, Circle, Bitmap, Text, Line)
from dwidgets.retakecanvas.mathutils import distance_qline_qpoint

UNDOLIMIT = 30
BLEND_MODE_NAMES = {
    QPainter.CompositionMode_Clear: 'Clear',
    QPainter.CompositionMode_ColorBurn: 'Colorburn',
    QPainter.CompositionMode_ColorDodge: 'Colordodge',
    QPainter.CompositionMode_Darken: 'Darken',
    QPainter.CompositionMode_Destination: 'Destination',
    QPainter.CompositionMode_DestinationAtop: 'Destination Atop',
    QPainter.CompositionMode_DestinationIn: 'Destination In',
    QPainter.CompositionMode_DestinationOut: 'Destination Out',
    QPainter.CompositionMode_DestinationOver: 'Destination Over',
    QPainter.CompositionMode_Difference: 'Difference',
    QPainter.CompositionMode_Exclusion: 'Exclusion',
    QPainter.CompositionMode_HardLight: 'Hardlight',
    QPainter.CompositionMode_Lighten: 'Lighten',
    QPainter.CompositionMode_Multiply: 'Multiply',
    QPainter.CompositionMode_Overlay: 'Overlay',
    QPainter.CompositionMode_Plus: 'Plus',
    QPainter.CompositionMode_Screen: 'Screen',
    QPainter.CompositionMode_SoftLight: 'Softlight',
    QPainter.CompositionMode_Source: 'Source',
    QPainter.CompositionMode_SourceAtop: 'Source Atop',
    QPainter.CompositionMode_SourceIn: 'Source In',
    QPainter.CompositionMode_SourceOut: 'Source Out',
    QPainter.CompositionMode_SourceOver: 'Source Over',
    QPainter.CompositionMode_Xor: 'Xor',
}
BLEND_MODE_FOR_NAMES = {v: k for k, v in BLEND_MODE_NAMES.items()}


class LayerStack:
    def __init__(self):
        super().__init__()
        self.layers = []
        self.locks = []
        self.names = []
        self.opacities = []
        self.blend_modes = []
        self.visibilities = []

        self.current_index = None
        self.undostack = []
        self.redostack = []
        self._current_index = None

    @property
    def texts(self):
        return [
            shape.text for layer in self.layers for shape in layer
            if isinstance(shape, Text)]

    @property
    def current_index(self):
        return self._current_index

    @current_index.setter
    def current_index(self, value):
        self._current_index = value

    def add(self, name, blend_mode: QPainter.CompositionMode=None):
        blend_mode = blend_mode or QPainter.CompositionMode_SourceOver
        self.layers.append([])
        self.locks.append(False)
        self.opacities.append(255)
        self.blend_modes.append(blend_mode)
        self.names.append(name)
        self.visibilities.append(True)
        self.current_index = len(self.layers) - 1

    def duplicate_current(self):
        if self.current is None:
            return
        index = self.current_index
        new_layer = [shape.copy() for shape in self.current]
        self.layers.insert(index, new_layer)
        self.opacities.insert(index, self.opacities[index])
        self.blend_modes.insert(index, self.blend_modes[index])
        name = unique_layer_name(self.names[index], self.names)
        self.names.insert(index, name)
        self.visibilities.insert(index, self.visibilities[index])
        self.locks.insert(index, self.locks[index])

    @property
    def current_blend_mode_name(self):
        if self.current_index is None:
            return BLEND_MODE_NAMES[QPainter.CompositionMode_SourceOver]
        return BLEND_MODE_NAMES[self.blend_modes[self.current_index]]

    def set_current_blend_mode_name(self, name):
        if not self.current_index:
            return
        self.blend_modes[self.current_index] = BLEND_MODE_FOR_NAMES[name]

    @property
    def is_locked(self):
        if self.current_index is None:
            return False
        return self.locks[self.current_index]

    @property
    def current(self):
        if self.current_index is None:
            return
        return self.layers[self.current_index]

    def move_layer(self, old_index, new_index):
        if new_index > old_index:
            new_index -= 1
        self.layers.insert(new_index, self.layers.pop(old_index))
        self.locks.insert(new_index, self.locks.pop(old_index))
        self.names.insert(new_index, self.names.pop(old_index))
        self.blend_modes.insert(new_index, self.blend_modes.pop(old_index))
        self.opacities.insert(new_index, self.opacities.pop(old_index))
        self.visibilities.insert(new_index, self.visibilities.pop(old_index))
        self.current_index = new_index

    def remove(self, element):
        if self.current:
            self.current.remove(element)

    def delete(self, index=None):
        if not index and self.current:
            index = self.layers.index(self.current)
        if index is None:
            return
        if index != self.current_index:
            return
        self.layers.pop(index)
        self.visibilities.pop(index)
        self.opacities.pop(index)
        self.blend_modes.pop(index)
        self.locks.pop(index)
        self.names.pop(index)

        if not self.layers:
            self.current_index = None
            return
        self.current_index = index - 1

    def find_element_at(self, point):
        if not self.current:
            return
        for layer in reversed(self.layers):
            for element in reversed(layer):
                if isinstance(element, (Arrow, Rectangle, Text, Line)):
                    for p in (element.start, element.end):
                        if is_point_hover_element(p, point):
                            return p
                if is_point_hover_element(element, point):
                    return element

    def __iter__(self):
        return zip(
            self.layers,
            self.names,
            self.blend_modes,
            self.locks,
            self.visibilities,
            self.opacities).__iter__()

    def __len__(self):
        return len(self.layers)


def is_point_hover_element(element, point):
    if isinstance(point, QtCore.QPointF):
        point = point.toPoint()

    if isinstance(element, (QtCore.QPoint, QtCore.QPointF)):
        rect = QtCore.QRectF(element.x() - 10, element.y() - 10, 20, 20)
        return rect.contains(point)
    elif isinstance(element, Stroke):
        return is_point_hover_stroke(element, point)
    elif isinstance(element, Arrow):
        distance = distance_qline_qpoint(element.line, point)
        return distance <= element.tailwidth
    elif isinstance(element, Line):
        distance = distance_qline_qpoint(element.line, point)
        return distance <= element.linewidth
    elif isinstance(element, Text):
        rect = QtCore.QRectF(element.start, element.end)
        return rect.contains(point)
    elif isinstance(element, Rectangle):
        rect = QtCore.QRectF(element.start, element.end)
        if element.filled:
            return rect.contains(point)
        lines = (
            (rect.topLeft(), rect.bottomLeft()),
            (rect.topLeft(), rect.topRight()),
            (rect.topRight(), rect.bottomRight()),
            (rect.bottomLeft(), rect.bottomRight()))
        for line in lines:
            line = QtCore.QLineF(*line)
            if distance_qline_qpoint(line, point) <= element.linewidth:
                return True
        return False
    elif isinstance(element, Circle):
        # TODO
        return False
    elif isinstance(element, Bitmap):
        return element.rect.contains(point)


def is_point_hover_stroke(stroke, point):
    start = None
    for stroke_point, size in stroke:
        if start is None:
            start = stroke_point
            continue
        end = stroke_point
        line = QtCore.QLineF(start, end)
        distance = distance_qline_qpoint(line, point)
        start = stroke_point
        if distance <= size:
            return True
    return False


def unique_layer_name(name, names):
    if name not in names:
        return name

    template = '{name} ({n})'
    i = 1
    while template.format(name=name, n=i) in names:
        i += 1
        continue
    return template.format(name=name, n=i)
