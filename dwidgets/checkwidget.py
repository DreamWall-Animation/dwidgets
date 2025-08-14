from PySide2 import QtWidgets, QtCore, QtGui
from dwidgets.qtutils import grow_rect


class CheckWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.state = False

    def mouseReleaseEvent(self, event):
        if event.button() != QtCore.Qt.LeftButton:
            return
        self.state = not self.state
        self.repaint()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        center = self.rect().center()
        rect = QtCore.QRect(center.x() - 15, center.y() - 15, 30, 30)
        if self.state:
            font = QtGui.QFont()
            font.setPixelSize(20)
            option = QtGui.QTextOption()
            option.setAlignment(QtCore.Qt.AlignCenter)
            painter.drawText(rect, '✔', option)
        color = painter.pen().color()
        color.setAlpha(150)
        painter.setPen(QtGui.QPen(color))
        painter.drawRect(grow_rect(rect, -5))
        painter.end()
