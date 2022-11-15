from PySide2 import QtCore, QtGui
from dwidgets.retakecanvas.mathutils import distance_line_point
from dwidgets.retakecanvas.model import RetakeCanvasModel
from dwidgets.retakecanvas.qtutils import grow_rect
from dwidgets.retakecanvas.tools.basetool import NavigationTool


HANDLE_DISTANCE = 20


class WipesTool(NavigationTool):
    LEFT = 0
    TOP = 1
    RIGHT = 2
    BOTTOM = 3

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_index = None
        self.current_side = None
        self.handeling = False
        self.side = None

    @property
    def rects(self):
        rects = list(reversed(self.model.imagestack_wipes))
        return [self.model.baseimage_wipes] + rects

    def mousePressEvent(self, event):
        self.handeling = None not in (self.current_index, self.current_side)
        return super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if super().mouseMoveEvent(event):
            return
        if self.model.imagestack_layout != RetakeCanvasModel.STACKED:
            return
        cursor = self.viewportmapper.to_units_coords(event.pos()).toPoint()
        if not self.handeling:
            for i, rect in enumerate(self.rects):
                rect = grow_rect(rect, HANDLE_DISTANCE / 2)
                if rect.contains(cursor):
                    self.current_index = i
                    self.current_side = detect_edge(rect, cursor)
                    return
            self.current_index = None
            self.current_side = None
            return super().mouseMoveEvent(event)
        rect = self.rects[self.current_index]
        if self.current_side == WipesTool.LEFT:
            rect.setLeft(cursor.x())
        elif self.current_side == WipesTool.TOP:
            rect.setTop(cursor.y())
        elif self.current_side == WipesTool.RIGHT:
            rect.setRight(cursor.x())
        elif self.current_side == WipesTool.BOTTOM:
            rect.setBottom(cursor.y())

    def mouseReleaseEvent(self, event):
        self.handeling = False
        self.current_index = None
        self.current_side = None

    def draw(self, painter):
        if self.model.imagestack_layout != RetakeCanvasModel.STACKED:
            return
        if self.current_index is None:
            return

        painter.setRenderHints(QtGui.QPainter.Antialiasing, False)
        painter.setBrush(QtCore.Qt.NoBrush)
        if not self.handeling:
            color = QtGui.QColor(QtCore.Qt.yellow)
            color.setAlpha(125)
            painter.setPen(color)
            rect = self.rects[self.current_index]
            rect = self.viewportmapper.to_viewport_rect(rect)
            painter.drawRect(rect)
            if self.current_side is not None:
                line = side_line(rect, self.current_side)
                pen = QtGui.QPen(QtCore.Qt.red)
                pen.setWidth(2)
                painter.setPen(pen)
                painter.drawLine(line)
        painter.setRenderHints(QtGui.QPainter.Antialiasing, True)

    def window_cursor_override(self):
        cursor = super().window_cursor_override()
        if cursor:
            return cursor
        if self.current_side in [WipesTool.LEFT, WipesTool.RIGHT]:
            return QtCore.Qt.SplitHCursor
        if self.current_side in [WipesTool.TOP, WipesTool.BOTTOM]:
            return QtCore.Qt.SplitVCursor


def detect_edge(rect, point):
    sides = WipesTool.LEFT, WipesTool.TOP, WipesTool.RIGHT, WipesTool.BOTTOM
    for side in sides:
        if distance_line_point(side_line(rect, side), point) < 20:
            return side


def side_line(rect, side):
    if side == WipesTool.LEFT:
        return QtCore.QLineF(rect.topLeft(), rect.bottomLeft())
    if side == WipesTool.TOP:
        return QtCore.QLineF(rect.topLeft(), rect.topRight())
    if side == WipesTool.RIGHT:
        return QtCore.QLineF(rect.topRight(), rect.bottomRight())
    if side == WipesTool.BOTTOM:
        return QtCore.QLineF(rect.bottomLeft(), rect.bottomRight())
