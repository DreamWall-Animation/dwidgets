
from PySide2 import QtWidgets, QtCore
from dwidgets.retakecanvas.button import ColorAction
from dwidgets.retakecanvas.dialog import ColorSelection


class GeneralSettings(QtWidgets.QWidget):
    def __init__(self, model, parent=None):
        super().__init__(parent=parent)
        self.model = model
        self.color = ColorAction(self.model.drawcontext.color)
        self.color.released.connect(self.select_color)
        self.linewidth = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.linewidth.setMinimum(0)
        self.linewidth.setMaximum(60)
        self.linewidth.setValue(self.model.drawcontext.size)
        self.linewidth.valueChanged.connect(self.set_linewidth)
        layout = QtWidgets.QFormLayout(self)
        layout.addRow('Main color:', self.color)
        layout.addRow('Linewidth:', self.linewidth)

    def set_linewidth(self, value):
        self.model.drawcontext.size = value

    def select_color(self):
        dialog = ColorSelection(self.color.color)
        dialog.move(self.mapToGlobal(self.color.pos()))
        result = dialog.exec_()
        if result != QtWidgets.QDialog.Accepted:
            return
        self.color.color = dialog.color
        self.model.drawcontext.color = dialog.color

    def set_model(self, model):
        self.model = model
        self.color.color = model.drawcontext.color
        self.linewidth.blockSignals(True)
        self.linewidth.setValue(model.drawcontext.size)
        self.linewidth.blockSignals(False)
        self.repaint()


class SmoothDrawSettings(QtWidgets.QWidget):
    def __init__(self, tool, parent=None):
        super().__init__(parent=parent)
        self.tool = tool
        self.slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slider.setMinimum(5)
        self.slider.setMaximum(100)
        self.slider.setValue(tool.buffer_lenght)
        self.slider.valueChanged.connect(self.buffer_changed)
        form = QtWidgets.QFormLayout(self)
        form.addRow('Buffer lenght', self.slider)

    def buffer_changed(self, value):
        self.tool.buffer_lenght = value


class ArrowSettings(QtWidgets.QWidget):
    def __init__(self, tool, parent=None):
        super().__init__(parent=parent)
        self.tool = tool
        self.slider1 = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slider1.setMinimum(3)
        self.slider1.setMaximum(25)
        self.slider1.setValue(tool.headsize)
        self.slider1.valueChanged.connect(self.change_head)
        self.slider2 = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slider2.setMinimum(3)
        self.slider2.setMaximum(25)
        self.slider2.setValue(tool.tailwidth)
        self.slider2.valueChanged.connect(self.change_tail)

        form = QtWidgets.QFormLayout(self)
        form.addRow('Head size', self.slider1)
        form.addRow('Tail width', self.slider2)

    def change_tail(self, value):
        self.tool.tailwidth = value

    def change_head(self, value):
        self.tool.headsize = value
