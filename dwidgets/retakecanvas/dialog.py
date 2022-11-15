from PySide2 import QtWidgets, QtCore, QtGui
from dwidgets.retakecanvas.qtutils import COLORS


class OpacityDialog(QtWidgets.QWidget):
    WIDTH = 150

    def __init__(self, layerstack, index, parent=None):
        super().__init__(parent)
        self.index = index
        self.layerstack = layerstack
        self.setWindowFlag(QtCore.Qt.FramelessWindowHint)
        self.setWindowFlag(QtCore.Qt.Popup)
        self.slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slider.setMinimum(0)
        self.slider.setMaximum(255)
        self.slider.setValue(layerstack.opacities[index])
        self.slider.valueChanged.connect(self.change_opacity)
        self.setFixedWidth(self.WIDTH)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.slider)

    def exec_(self, point, size):
        self.resize(size)
        point.setX(point.x() - (self.WIDTH / 2))
        point.setY(point.y() + (size.height() / 2))
        self.move(point)
        path = QtGui.QPainterPath()
        path.addRoundedRect(self.rect(), 10, 10)
        mask = QtGui.QRegion(path.toFillPolygon().toPolygon())
        self.setMask(mask)
        self.show()

    def change_opacity(self, value):
        self.layerstack.opacities[self.index] = value
        self.parent().repaint()


class RenameDialog(QtWidgets.QWidget):
    def __init__(self, layerstack, index, parent=None):
        super().__init__(parent)
        self.index = index
        self.layerstack = layerstack
        self.setWindowFlag(QtCore.Qt.FramelessWindowHint)
        self.setWindowFlag(QtCore.Qt.Popup)
        self.text = QtWidgets.QLineEdit(layerstack.names[index])
        self.text.focusOutEvent = self.focusOutEvent
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.text)
        self.text.returnPressed.connect(self.close)

    def closeEvent(self, _):
        if self.layerstack.names[self.index] != self.text.text():
            self.layerstack.names[self.index] = self.text.text()
            self.parent().repaint()

    def exec_(self, point, size):
        self.move(point)
        self.resize(size)
        self.show()
        self.text.setFocus(QtCore.Qt.MouseFocusReason)
        self.text.selectAll()


class ColorSelection(QtWidgets.QDialog):
    COLORSIZE = 50
    COLCOUNT = 5

    def __init__(self, color, parent=None):
        super().__init__(parent=parent)
        self.setMouseTracking(True)
        self.color = color
        self.setModal(True)
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
        width = self.COLORSIZE * self.COLCOUNT
        height = self.COLORSIZE * (len(COLORS) // self.COLCOUNT)
        self.resize(width, height)

    def mouseMoveEvent(self, _):
        self.repaint()

    def mouseReleaseEvent(self, event):
        if event.button() != QtCore.Qt.LeftButton:
            return
        row = event.pos().y() // self.COLORSIZE
        col = event.pos().x() // self.COLORSIZE
        index = (row * self.COLCOUNT) + col
        try:
            self.color = COLORS[index]
            self.accept()
        except IndexError:
            ...

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        left, top = 0, 0
        pen = QtGui.QPen()
        pen.setWidth(3)
        for color in COLORS:
            if left >= self.rect().width():
                left = 0
                top += self.COLORSIZE
            rect = QtCore.QRect(left, top, self.COLORSIZE, self.COLORSIZE)
            if color == self.color:
                pencolor = QtCore.Qt.red
            elif rect.contains(self.mapFromGlobal(QtGui.QCursor.pos())):
                pencolor = QtCore.Qt.white
            else:
                pencolor = QtCore.Qt.transparent
            pen.setColor(pencolor)
            painter.setPen(pen)
            painter.setBrush(QtGui.QColor(color))
            painter.drawRect(rect)
            left += self.COLORSIZE
