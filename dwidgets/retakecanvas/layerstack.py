
import math
from PySide2 import QtCore
from dwidgets.retakecanvas.shapes import (
    Stroke, Arrow, Rectangle, Circle, Bitmap)

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
        self.wash_color = '#FFFFFF'
        self.wash_opacity = 0
        self.undostack = []
        self.redostack = []
        self.add_undo_state()

    def add(self, undo=True, name=None):
        self.layers.append([])
        self.locks.append(False)
        self.opacities.append(255)
        self.names.append(name or f'Layer {len(self.layers)}')
        self.visibilities.append(True)
        self.current_index = len(self.layers) - 1
        if undo:
            self.add_undo_state()

    def set_current(self, index):
        self.current_index = index

    @property
    def current(self):
        if self.current_index is None:
            return
        return self.layers[self.current_index]

    def remove(self, element):
        if self.current:
            self.current.remove(element)
        self.add_undo_state()

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
            self.add_undo_state()
            return
        self.current_index = index - 1
        self.add_undo_state()

    def add_undo_state(self):
        self.redostack = []
        state = {
            'layers': [[elt.copy() for elt in layer] for layer in self.layers],
            'locks': self.locks.copy(),
            'opacities': self.opacities.copy(),
            'names': self.names.copy(),
            'visibilities': self.visibilities.copy(),
            'current': self.current_index,
            'wash_color': self.wash_color,
            'wash_opacity': self.wash_opacity
        }
        self.undostack.append(state)
        self.undostack = self.undostack[-UNDOLIMIT:]

    def restore_state(self, state):
        layers = [[elt.copy() for elt in layer] for layer in state['layers']]
        self.layers = layers
        self.locks = state['locks']
        self.opacities = state['opacities']
        self.names = state['names']
        self.visibilities = state['visibilities']

        self.current_index = state['current']
        self.wash_color = state['wash_color']
        self.wash_opacity = state['wash_opacity']

    def undo(self):
        if not self.undostack:
            return

        state = self.undostack.pop()
        self.redostack.append(state)
        if self.undostack:
            self.restore_state(self.undostack[-1])
        else:
            self.restore_state({
                'layers': [],
                'locks': [],
                'names': [],
                'opacities': [],
                'visibilities': [],
                'current': None,
                'wash_color': '#FFFFFF',
                'wash_opacity': 0})

    def redo(self):
        if not self.redostack:
            return
        state = self.redostack.pop()
        self.undostack.append(state)
        self.restore_state(state)

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
        distance = _distance_line_point(element.line, point)
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
        distance = _distance_line_point(line, point)
        start = stroke_point
        if distance <= size:
            return True
    return False


def _distance_line_point(line, point):
    return distance_point_segment(
        point.x(), point.y(),
        line.p1().x(), line.p1().y(),
        line.p2().x(), line.p2().y())


def line_magnitude(x1, y1, x2, y2):
    return math.sqrt(math.pow((x2 - x1), 2) + math.pow((y2 - y1), 2))


def distance_point_segment(px, py, x1, y1, x2, y2):
    """
    https://maprantala.com/
        2010/05/16/measuring-distance-from-a-point-to-a-line-segment-in-python
    http://local.wasp.uwa.edu.au/~pbourke/geometry/pointline/source.vba
    """
    line_mag = line_magnitude(x1, y1, x2, y2)

    if line_mag < 0.00000001:
        return 9999

    u1 = (((px - x1) * (x2 - x1)) + ((py - y1) * (y2 - y1)))
    u = u1 / (line_mag * line_mag)

    if (u < 0.00001) or (u > 1):
        # closest point does not fall within the line segment, take the
        # shorter distance to an endpoint.
        ix = line_magnitude(px, py, x1, y1)
        iy = line_magnitude(px, py, x2, y2)
        return iy if ix > iy else ix
    else:
        # Intersecting point is on the line, use the formula
        ix = x1 + u * (x2 - x1)
        iy = y1 + u * (y2 - y1)
        return line_magnitude(px, py, ix, iy)
