
from PySide2 import QtCore
from dwidgets.retakecanvas.shapes import (
    Stroke, Arrow, Rectangle, Circle, Bitmap)
from dwidgets.retakecanvas.mathutils import distance_line_point

UNDOLIMIT = 50


class LayerStack:

    def __init__(self):
        super().__init__()
        self.layers = []
        self.locks = []
        self.names = []
        self.opacities = []
        self.visibilities = []

        self.current_index = None
        self.undostack = []
        self.redostack = []
        self._current_index = None

    @property
    def current_index(self):
        return self._current_index

    @current_index.setter
    def current_index(self, value):
        self._current_index = value

    def add(self, name):
        self.layers.append([])
        self.locks.append(False)
        self.opacities.append(255)
        self.names.append(name)
        self.visibilities.append(True)
        self.current_index = len(self.layers) - 1

    def set_current(self, index):
        self.current_index = index

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
                if isinstance(element, Arrow):
                    if is_point_hover_element(element.start, point):
                        return element.start
                    elif is_point_hover_element(element.end, point):
                        return element.end
                if is_point_hover_element(element, point):
                    return element

    def __iter__(self):
        return zip(
            self.layers,
            self.names,
            self.locks,
            self.visibilities,
            self.opacities).__iter__()

    def __len__(self):
        return len(self.layers)


def is_point_hover_element(element, point):
    if isinstance(element, (QtCore.QPoint, QtCore.QPointF)):
        rect = QtCore.QRectF(element.x() - 5, element.y() - 5, 10, 10)
        return rect.contains(point)
    elif isinstance(element, Stroke):
        return is_point_hover_stroke(element, point)
    elif isinstance(element, Arrow):
        distance = distance_line_point(element.line, point)
        return distance <= element.tailwidth
    elif isinstance(element, (Rectangle, Circle)):
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
        distance = distance_line_point(line, point)
        start = stroke_point
        if distance <= size:
            return True
    return False
