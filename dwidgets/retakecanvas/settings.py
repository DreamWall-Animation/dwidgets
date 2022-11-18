
from PySide2 import QtWidgets, QtCore
from dwidgets.retakecanvas.button import ColorAction
from dwidgets.retakecanvas.dialog import ColorSelection
from dwidgets.retakecanvas.shapes import Stroke, Arrow, Rectangle, Circle


class _Row(QtWidgets.QWidget):
    def __init__(self, text, textwidth, widget, parent=None):
        super().__init__(parent=parent)
        self.text = QtWidgets.QLabel(text)
        self.text.setFixedWidth(textwidth)
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.text)
        layout.addWidget(widget)


class ShapeSettings(QtWidgets.QWidget):
    def __init__(self, canvas, model, parent=None):
        super().__init__(parent=parent)
        size = 75
        self.model = model
        self.canvas = canvas
        self.main_color = ColorAction(self.model.drawcontext.color)
        self.main_color.released.connect(self.main_color_changed)
        self.main_color_row = _Row('Shape color: ', size, self.main_color)
        self.shape_width = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.shape_width.setMinimum(3)
        self.shape_width.setMaximum(25)
        self.shape_width.valueChanged.connect(self.size_changed)
        self.shape_width.sliderReleased.connect(self.model.add_undo_state)
        self.shape_width_row = _Row('Shape width: ', size, self.shape_width)
        self.tail_width = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.tail_width.setMinimum(3)
        self.tail_width.setMaximum(25)
        self.tail_width.valueChanged.connect(self.tail_width_changed)
        self.tail_width.sliderReleased.connect(self.model.add_undo_state)
        self.tail_width_row = _Row('Tail with: ', size, self.tail_width)
        self.head_size = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.head_size.setMinimum(3)
        self.head_size.setMaximum(25)
        self.head_size.valueChanged.connect(self.head_size_changed)
        self.head_size.sliderReleased.connect(self.model.add_undo_state)
        self.head_size_row = _Row('Head size: ', size, self.head_size)
        self.stroke_width = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.stroke_width.setMinimum(0)
        self.stroke_width.setMaximum(100)
        self.stroke_width.setValue(50)
        self.stroke_width.valueChanged.connect(self.multiply_stroke_width)
        self.stroke_width.sliderReleased.connect(self.model.add_undo_state)
        self.stroke_width_row = _Row('Stroke Size: ', size, self.stroke_width)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.main_color_row)
        layout.addWidget(self.shape_width_row)
        layout.addWidget(self.tail_width_row)
        layout.addWidget(self.head_size_row)
        layout.addWidget(self.stroke_width_row)

    def update(self):
        shape = self.element
        if not shape:
            return False
        methods = {
            Stroke: self.set_stroke,
            Arrow: self.set_arrow,
            Rectangle: self.set_shape,
            Circle: self.set_shape}
        method = methods.get(type(shape))
        if not method:
            return False
        method(shape)
        return True

    def main_color_changed(self):
        dialog = ColorSelection(self.main_color.color)
        dialog.move(self.mapToGlobal(self.main_color.pos()))
        result = dialog.exec_()
        if result != QtWidgets.QDialog.Accepted:
            return
        self.main_color.set_color(dialog.color)
        self.element.color = dialog.color
        self.canvas.repaint()
        self.add_undo_state()

    def size_changed(self, value):
        if not isinstance(self.element, (Rectangle, Circle)):
            return
        self.element.width = value
        self.repaint()

    def tail_width_changed(self, value):
        if not isinstance(self.element, Arrow):
            return
        self.element.tailwidth = value
        self.canvas.repaint()

    def head_size_changed(self, value):
        if not isinstance(self.element, Arrow):
            return
        self.element.headsize = value
        self.canvas.repaint()

    def multiply_stroke_width(self, value):
        if not isinstance(self.element, Stroke):
            return
        value /= 50
        for i, (point, size) in enumerate(self.element):
            self.element[i] = [point, min(max(3, size * value), 25)]
        self.canvas.repaint()

    def set_shape(self, shape):
        self.main_color.set_color(shape.color)
        self.shape_width.setValue(shape.width)
        self.shape_width_row.show()
        self.stroke_width_row.hide()
        self.tail_width_row.hide()
        self.head_size_row.hide()

    def set_arrow(self, arrow):
        self.main_color.set_color(arrow.color)
        self.tail_width.setValue(arrow.tailwidth)
        self.head_size.setValue(arrow.headsize)
        self.stroke_width_row.hide()
        self.shape_width_row.hide()
        self.tail_width_row.show()
        self.head_size_row.show()

    def set_stroke(self, stroke):
        self.main_color.set_color(stroke.color)
        self.stroke_width_row.show()
        self.shape_width_row.hide()
        self.tail_width_row.hide()
        self.head_size_row.hide()

    @property
    def element(self):
        return self.model.selection.element

    def set_model(self, model):
        self.model = model


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
        self.color.set_color(dialog.color)
        self.model.drawcontext.color = dialog.color

    def set_model(self, model):
        self.model = model
        self.color.set_color(model.drawcontext.color)
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
