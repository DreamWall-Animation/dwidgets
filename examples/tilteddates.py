import os, sys
from datetime import date, timedelta
from PySide2 import QtWidgets, QtGui
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))


from dwidgets import TiltedDates


dates = list(reversed([
    d for d in [date.today() - timedelta(days=n) for n in range(10)]
    if d.weekday() < 5]))


class Window(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setMinimumSize(600, 400)
        self.dates1 = TiltedDates(dates)
        self.dates1.display_format = '%d/%m/%Y'
        self.dates1.angle = -90
        font = QtGui.QFont()
        font.setPixelSize(15)
        font.setBold(True)
        self.dates2 = TiltedDates(dates)
        self.dates2.font = font
        self.dates2.angle = -45
        self.dates2.spacing = 35

        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.addWidget(self.dates1)
        self.layout.addWidget(self.dates2)


app = QtWidgets.QApplication(sys.argv)
win = Window()
win.show()
app.exec()
