
import math
from PySide2 import QtWidgets, QtCore, QtGui


class CornerEditor(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.corners = {
            QtCore.Qt.TopLeftCorner: QtCore.Qt.LeftDockWidgetArea,
            QtCore.Qt.TopRightCorner: QtCore.Qt.RightDockWidgetArea,
            QtCore.Qt.BottomLeftCorner: QtCore.Qt.BottomDockWidgetArea,
            QtCore.Qt.BottomRightCorner : QtCore.Qt.BottomDockWidgetArea
        }
        self.setMouseTracking(True)

    def mouseMoveEvent(self, event):
        self.repaint()
        return super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        corners = (
            QtCore.Qt.TopLeftCorner,
            QtCore.Qt.TopRightCorner,
            QtCore.Qt.BottomLeftCorner,
            QtCore.Qt.BottomRightCorner)
        pos = self.mapFromGlobal(QtGui.QCursor.pos())

        central_rect = self.central_rect()

        areas = {
            QtCore.Qt.TopLeftCorner: (
                QtCore.Qt.LeftDockWidgetArea,
                QtCore.Qt.TopDockWidgetArea),
            QtCore.Qt.TopRightCorner: (
                QtCore.Qt.TopDockWidgetArea,
                QtCore.Qt.RightDockWidgetArea),
            QtCore.Qt.BottomLeftCorner: (
                QtCore.Qt.BottomDockWidgetArea,
                QtCore.Qt.LeftDockWidgetArea),
            QtCore.Qt.BottomRightCorner : (
                QtCore.Qt.RightDockWidgetArea,
                QtCore.Qt.BottomDockWidgetArea),
        }
        for corner in corners:
            lines = self.get_corner_lines(corner, central_rect)
            for i, (line, _) in enumerate(lines):
                if is_point_on_line(pos, line, 15):
                    self.corners[corner] = areas[corner][i]
                    print(areas[corner][i])
                    break
            else:
                continue
            break
        self.repaint()


    def get_corner_lines(self, corner, central_rect):
        if corner == QtCore.Qt.TopLeftCorner:
            line1 = QtCore.QLine(
                central_rect.topLeft(),
                QtCore.QPoint(self.rect().left(), central_rect.top()))
            line2 = QtCore.QLine(
                central_rect.topLeft(),
                QtCore.QPoint(central_rect.left(), self.rect().top()))
            if self.corners[corner] == QtCore.Qt.TopDockWidgetArea:
                return (line1, True), (line2, False)
            return (line1, False), (line2, True)

        if corner == QtCore.Qt.TopRightCorner:
            line1 = QtCore.QLine(
                central_rect.topRight(),
                QtCore.QPoint(central_rect.right(), self.rect().top()))
            line2 = QtCore.QLine(
                central_rect.topRight(),
                QtCore.QPoint(self.rect().right(), central_rect.top()))
            if self.corners[corner] == QtCore.Qt.RightDockWidgetArea:
                return (line1, True), (line2, False)
            return (line1, False), (line2, True)

        if corner == QtCore.Qt.BottomLeftCorner:
            line1 = QtCore.QLine(
                central_rect.bottomLeft(),
                QtCore.QPoint(central_rect.left(), self.rect().bottom()))
            line2 = QtCore.QLine(
                central_rect.bottomLeft(),
                QtCore.QPoint(self.rect().left(), central_rect.bottom()))
            if self.corners[corner] == QtCore.Qt.LeftDockWidgetArea:
                return (line1, True), (line2, False)
            return (line1, False), (line2, True)

        if corner == QtCore.Qt.BottomRightCorner:
            line1 = QtCore.QLine(
                central_rect.bottomRight(),
                QtCore.QPoint(self.rect().right(), central_rect.bottom()))
            line2 = QtCore.QLine(
                central_rect.bottomRight(),
                QtCore.QPoint(central_rect.right(), self.rect().bottom()))
            if self.corners[corner] == QtCore.Qt.BottomDockWidgetArea:
                return (line1, True), (line2, False)
            return (line1, False), (line2, True)

    def central_rect(self):
        return QtCore.QRect(
            int(self.rect().left() + (self.rect().width() / 5)),
            int(self.rect().top() + (self.rect().height() / 5)),
            int(self.rect().width() - (self.rect().width() / 2.5)),
            int(self.rect().height() - (self.rect().height() / 2.5))
        )

    def paintEvent(self, _):
        painter = QtGui.QPainter(self)
        pen = QtGui.QPen(QtGui.QColor('#000000'))
        pen.setWidth(4)
        painter.setPen(pen)
        central_rect = self.central_rect()
        painter.drawRect(central_rect)

        corners = (
            QtCore.Qt.TopLeftCorner,
            QtCore.Qt.TopRightCorner,
            QtCore.Qt.BottomLeftCorner,
            QtCore.Qt.BottomRightCorner)
        pos = self.mapFromGlobal(QtGui.QCursor.pos())

        for corner in corners:
            lines = self.get_corner_lines(corner, central_rect)
            for line, state in lines:
                pen.setColor(get_line_color(line, pos))
                pen.setWidth(2 if state else 4)
                style = QtCore.Qt.DotLine if state else QtCore.Qt.SolidLine
                pen.setStyle(style)
                painter.setPen(pen)
                painter.drawLine(line)

        painter.end()


def get_line_color(line, pos):
    if is_point_on_line(pos, line, 15):
        return QtGui.QColor('yellow')
    return QtGui.QColor()


def is_point_on_line(point, line, margin: float = 1.0):
    x1, y1 = line.p1().x(), line.p1().y()
    x2, y2 = line.p2().x(), line.p2().y()
    px, py = point.x(), point.y()

    A = y2 - y1
    B = -(x2 - x1)
    C = x2 * y1 - y2 * x1

    distance = abs(A * px + B * py + C) / math.sqrt(A**2 + B**2)
    if distance > margin:
        return False

    within_x_bounds = min(x1, x2) - margin <= px <= max(x1, x2) + margin
    within_y_bounds = min(y1, y2) - margin <= py <= max(y1, y2) + margin

    return within_x_bounds and within_y_bounds
