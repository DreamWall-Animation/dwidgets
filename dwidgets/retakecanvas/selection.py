from PySide2 import QtCore
from dwidgets.retakecanvas.qtutils import points_rect
from dwidgets.retakecanvas.shapes import (
    Arrow, Rectangle, Circle, Stroke, Bitmap)


class Selection:
    NO = 0
    SUBOBJECTS = 1
    ELEMENT = 2

    def __init__(self):
        self.sub_elements = []
        self.element = None
        self.mode = 'replace'

    def set(self, elements):
        if isinstance(elements, (QtCore.QPoint, QtCore.QPointF, Arrow, Rectangle, Circle, Stroke, Bitmap)):
            self.elements = []
            self.element = elements
            return
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
                if element in self.sub_elements:
                    self.remove(element)

    @property
    def type(self):
        if self.element is not None:
            return self.ELEMENT
        if self.sub_elements:
            return self.SUBOBJECTS
        return self.NO

    def replace(self, elements):
        self.sub_elements = elements

    def add(self, elements):
        self.sub_elements.extend([s for s in elements if s not in self])

    def remove(self, shape):
        self.sub_elements.remove(shape)

    def invert(self, elements):
        for element in elements:
            if element not in self.sub_elements:
                self.add([element])
            else:
                self.remove(element)

    def clear(self):
        self.sub_elements = []
        self.element = None

    def __bool__(self):
        return bool(self.sub_elements) or bool(self.element)

    __nonzero__ = __bool__

    def __len__(self):
        return len(self.sub_elements)

    def __getitem__(self, i):
        return self.sub_elements[i]

    def __iter__(self):
        return self.sub_elements.__iter__()


def selection_rect(selection):
    if selection.type != selection.SUBOBJECTS:
        return
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


