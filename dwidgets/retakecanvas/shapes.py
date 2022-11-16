from copy import deepcopy
from PySide2 import QtGui, QtCore


class Bitmap:
    def __init__(self, image, rect):
        self.image = image
        self.rect = rect

    def offset(self, offset):
        self.rect.moveTopLeft(self.rect.topLef() + offset)

    def copy(self):
        return Bitmap(QtGui.QImage(self.image), QtCore.QRectF(self.rect))


class Rectangle:
    def __init__(self, start, color, linewidth):
        self.start = start
        self.end = None
        self.color = color
        self.linewidth = linewidth

    def handle(self, point):
        self.end = point

    @property
    def is_valid(self):
        return self.end is not None

    def copy(self):
        rect = Rectangle(self.start, self.color, self.linewidth)
        rect.end = self.end
        return rect


class Circle(Rectangle):

    def copy(self):
        rect = Circle(self.start, self.color, self.linewidth)
        rect.end = self.end
        return rect


class Arrow:
    def __init__(self, start, color, linewidth):
        self.start = start
        self.end = None
        self.color = color
        self.tailwidth = linewidth
        self.headsize = 10

    @property
    def line(self):
        return QtCore.QLineF(self.start, self.end)

    def handle(self, point):
        self.end = point

    @property
    def is_valid(self):
        return self.end is not None

    def copy(self):
        arrow = Arrow(self.start, self.color, self.tailwidth)
        arrow.end = self.end
        arrow.headsize = self.headsize
        return arrow


class Stroke:
    def __init__(self, start, color, size):
        self.points = [(start, size)]
        self.color = color

    def add_point(self, point, size):
        self.points.append((point, size))

    @property
    def is_valid(self):
        return len(self.points) > 1

    def __iter__(self):
        return self.points.__iter__()

    def __getitem__(self, index):
        return self.points[index]

    def __len__(self):
        return len(self.points)

    def copy(self):
        stroke = Stroke(None, None, None)
        stroke.points = deepcopy(self.points)
        stroke.color = self.color
        return stroke
