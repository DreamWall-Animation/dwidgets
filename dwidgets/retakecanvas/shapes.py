from copy import deepcopy


class Rectangle:
    def __init__(self, start, color):
        self.start = start
        self.end = None
        self.color = color
        self.linewidth = 3

    def handle(self, point):
        self.end = point

    @property
    def is_valid(self):
        return self.end is not None

    def copy(self):
        rect = Rectangle(self.start, self.color)
        rect.end = self.end
        rect.linewidth = self.linewidth
        return rect


class Circle(Rectangle):

    def copy(self):
        rect = Circle(self.start, self.color)
        rect.end = self.end
        rect.linewidth = self.linewidth
        return rect


class Arrow:
    def __init__(self, start, color):
        self.start = start
        self.end = None
        self.color = color
        self.tailwidth = 3
        self.headsize = 10

    def handle(self, point):
        self.end = point

    @property
    def is_valid(self):
        return self.end is not None

    def copy(self):
        arrow = Arrow(self.start, self.color)
        arrow.end = self.end
        arrow.tailwidth = self.tailwidth
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

    def copy(self):
        stroke = Stroke(None, None, None)
        stroke.points = deepcopy(self.points)
        stroke.color = self.color
        return stroke