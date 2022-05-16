import os, sys, random
from PySide6 import QtWidgets, QtCore
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))


from dwidgets import WeightSlider


WEIGHTS = [
    [0.2, 0.3, 0.5],
    [0.1, 0.6, 0.1, 0.2],
    [.1, .1, .1, .2, .1, .1, .2, .1],
    [0.2, 0.3, 0.5],
]
COLORS = [
    ['#00FF00', 'blue', 'red'],
    ['orange', 'lightorange', 'darkorange', 'red'],
    ['#666666', '#12be56', 'black', 'yellow', 'pink', 'blue', 'purple', 'red'],
    ['#333333', '#555555', '#888888'],
]
TEXTS = [
    ['Pizza', 'Durum', 'Pasta'],
    ['Gym', 'Foot', 'Tennis', 'Badminton'],
    ['Maud', 'Johnny', 'Fred', 'Virginie', 'Esteban', 'Catherine', 'Yo', 'Su'],
    ['Fork', 'Spoon', 'Moon']
]


class Window(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        horizontals = [
            WeightSlider(
                weights=w, colors=c, texts=t,
                graduation=10)
            for (w, c, t) in zip(WEIGHTS, COLORS, TEXTS)]
        for slider in horizontals:
            slider.setFixedHeight(30)

        verticals1 = [
            WeightSlider(
                weights=w, colors=c, texts=t,
                orientation=QtCore.Qt.Vertical,
                graduation=10)
            for (w, c, t) in zip(WEIGHTS, COLORS, TEXTS)]
        for slider in verticals1:
            slider.setFixedWidth(30)

        verticals2 = [
            WeightSlider(
                weights=w, colors=c, texts=t,
                orientation=QtCore.Qt.Vertical,
                graduation=10)
            for (w, c, t) in zip(WEIGHTS, COLORS, TEXTS)]
        for slider in verticals2:
            slider.display_texts = True
            slider.setFixedWidth(120)

        self.vlayout = QtWidgets.QVBoxLayout()
        for slider in horizontals:
            self.vlayout.addWidget(slider)

        self.hlayout = QtWidgets.QHBoxLayout()
        for slider in verticals1 + verticals2:
            self.hlayout.addWidget(slider)

        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.addLayout(self.vlayout)
        self.layout.addLayout(self.hlayout)


app = QtWidgets.QApplication(sys.argv)
win = Window()
win.show()
app.exec()
