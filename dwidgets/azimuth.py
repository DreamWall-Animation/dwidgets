import math
from PySide2 import QtWidgets, QtCore, QtGui


DEFAULT_COLORS = {
    'background': '#333333',
    'border': '#666666',
    'pie': '#000000'
}


def angle(p1, p2):
    x1, y1 = p1
    x2, y2 = p2
    angle = math.atan2(y2 - y1, x2 - x1)
    return math.degrees(angle)


class AzimuthWidget(QtWidgets.QWidget):
    angle_changed = QtCore.Signal(float)

    def __init__(self, height=300, colors=None, parent=None):
        super().__init__(parent=parent)
        size = height, height * 2
        self.angle = 0
        self.colors = colors or DEFAULT_COLORS.copy()
        self.setFixedSize(QtCore.QSize(*size))

    def mousePressEvent(self, event):
        self.set_angle_from_event(event)

    def mouseMoveEvent(self, event):
        self.set_angle_from_event(event)

    def set_angle_from_event(self, event):
        p1 = event.pos()
        p2 = QtCore.QPoint(self.rect().right(), self.rect().center().y())
        self.angle = -angle((p1.x(), p1.y()), (p2.x(), p2.y()))
        self.angle = round(min(max(self.angle, -90), 90), 3)
        self.angle_changed.emit(self.angle)
        self.repaint()

    def set_angle(self, angle):
        self.angle = round(angle, 3)
        self.repaint()

    def paintEvent(self, _):
        rect = QtCore.QRect(
            self.rect().left() + 3, self.rect().top() + 6,
            self.rect().width() - 6, self.rect().height() - 6)
        rect.setWidth(rect.width() * 2)
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setBrush(QtGui.QColor(self.colors['background']))
        painter.setPen(QtCore.Qt.NoPen)
        pencolor = QtGui.QColor(self.colors['border'])
        pen = QtGui.QPen(pencolor)
        pen.setStyle(QtCore.Qt.DotLine)
        pen.setWidth(5)
        painter.setPen(pen)
        painter.drawPie(rect, 90 * 16, 180 * 16)
        painter.setBrush(QtCore.Qt.NoBrush)
        pencolor.setAlpha(100)
        pen.setColor(pencolor)
        pen.setWidth(3)
        painter.setPen(pen)
        painter.drawPie(rect, 135 * 16, 90 * 16)
        if self.angle:
            color = QtGui.QColor(QtGui.QColor(self.colors['pie']))
            color.setAlpha(75)
            painter.setBrush(color)
            painter.setPen(QtCore.Qt.NoPen)
            painter.drawPie(rect, 180 * 16, self.angle * 16)
        else:
            pencolor = QtGui.QColor(self.colors['pie'])
            painter.setPen(pencolor)
            p1 = QtCore.QPoint(self.rect().right(), self.rect().center().y())
            p2 = QtCore.QPoint(self.rect().left(), self.rect().center().y())
            painter.drawLine(p1, p2)
        pencolor = QtGui.QColor(self.colors['border'])
        pen = QtGui.QPen(pencolor)
        pen.setStyle(QtCore.Qt.DotLine)
        pen.setWidth(5)
        painter.setPen(pen)
        painter.setBrush(QtCore.Qt.NoBrush)
        painter.drawPie(rect, 90 * 16, 180 * 16)
        painter.end()


if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    azimuth = AzimuthWidget(90)
    azimuth.show()
    app.exec_()
