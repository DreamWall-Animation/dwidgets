from PySide2 import QtCore
from dwidgets.retakecanvas.qtutils import points_rect
from dwidgets.retakecanvas.shapes import Arrow, Rectangle, Circle, Stroke


class Selection:
    def __init__(self):
        self.elements = []
        self.mode = 'replace'

    def set(self, elements):
        if self.mode == 'add':
            if elements is None:
                return
            return self.add(elements)
        elif self.mode == 'replace':
            if elements is None:
                return self.clear()
            return self.replace(elements)
        elif self.mode == 'invert':
            if elements is None:
                return
            return self.invert(elements)
        elif self.mode == 'remove':
            if elements is None:
                return
            for element in elements:
                if element in self.elements:
                    self.remove(element)

    def replace(self, elements):
        self.elements = elements

    def add(self, elements):
        self.elements.extend([s for s in elements if s not in self])

    def remove(self, shape):
        self.elements.remove(shape)

    def invert(self, elements):
        for element in elements:
            if element not in self.elements:
                self.add([element])
            else:
                self.remove(element)

    def clear(self):
        self.elements = []

    def __len__(self):
        return len(self.elements)

    def __bool__(self):
        return bool(self.elements)

    __nonzero__ = __bool__

    def __getitem__(self, i):
        return self.elements[i]

    def __iter__(self):
        return self.elements.__iter__()


def selection_rect(selection):
    points = []
    for element in selection:
        if isinstance(element, (QtCore.QPoint, QtCore.QPointF)):
            points.append(element)
        elif isinstance(element, Stroke):
            points.extend(point for point, _ in element)
        elif isinstance(element, (Arrow, Rectangle, Circle)):
            points.extend((element.start, element.end))
        # elif isinstance(element, Bitmap):
        # TODO:
        #     points.extend((element.rect.topLeft(), element.bottomRight()))
        #     draw_bitmap(painter, element, viewportmapper)
    return points_rect(points)


