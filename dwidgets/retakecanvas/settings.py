
from PySide2 import QtWidgets, QtCore
from dwidgets.retakecanvas.button import ColorAction
from dwidgets.retakecanvas.dialog import ColorSelection
from dwidgets.retakecanvas.shapes import Stroke, Arrow, Rectangle, Circle, Text


ALIGNMENTS = [
    'Top left', 'Top right', 'Top center', 'Center left', 'Center',
    'Center right', 'Bottom left', 'Bottom center', 'Bottom right']


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
        size = 100
        self.model = model
        self.canvas = canvas
        self.main_color = ColorAction(self.model.drawcontext.color)
        self.main_color.released.connect(self.main_color_changed)
        self.main_color_row = _Row('Shape color: ', size, self.main_color)
        self.bgcolor = ColorAction(self.model.drawcontext.bgcolor)
        self.bgcolor.released.connect(self.bgcolor_changed)
        self.bgcolor_row = _Row('Background color: ', size, self.bgcolor)
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
        self.text_size = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.text_size.setMinimum(2)
        self.text_size.setMaximum(30)
        self.text_size.valueChanged.connect(self.text_size_changed)
        self.text_size.sliderReleased.connect(self.model.add_undo_state)
        self.text_size_row = _Row('Text size: ', size, self.text_size)
        self.text_content = QtWidgets.QTextEdit()
        self.text_content_row = _Row('Text: ', size, self.text_content)
        self.text_content.textChanged.connect(self.text_changed)
        self.text_alignment = QtWidgets.QComboBox()
        self.text_alignment.addItems(ALIGNMENTS)
        self.text_alignment.currentIndexChanged.connect(self.change_alignment)
        txt = 'Text alignment: '
        self.text_alignment_row = _Row(txt, size, self.text_alignment)
        self.filled = QtWidgets.QCheckBox('Filled')
        self.filled.toggled.connect(self.filled_toggled)
        self.filled_row = _Row('', size, self.filled)
        self.bgopacity = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.bgopacity.setMinimum(0)
        self.bgopacity.setMaximum(255)
        self.bgopacity.setValue(255)
        self.bgopacity.valueChanged.connect(self.bgopacity_changed)
        self.bgopacity.sliderReleased.connect(self.model.add_undo_state)
        self.bgopacity_row = _Row('Background Opacity: ', size, self.bgopacity)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.main_color_row)
        layout.addWidget(self.filled_row)
        layout.addWidget(self.bgcolor_row)
        layout.addWidget(self.bgopacity_row)
        layout.addWidget(self.shape_width_row)
        layout.addWidget(self.tail_width_row)
        layout.addWidget(self.head_size_row)
        layout.addWidget(self.stroke_width_row)
        layout.addWidget(self.text_size_row)
        layout.addWidget(self.text_content_row)
        layout.addWidget(self.text_alignment_row)

    def update(self):
        shape = self.element
        if not shape:
            return False
        methods = {
            Stroke: self.set_stroke,
            Arrow: self.set_arrow,
            Rectangle: self.set_shape,
            Circle: self.set_shape,
            Text: self.set_text}
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
        if not self.element:
            return
        self.element.color = dialog.color
        self.canvas.repaint()
        self.model.add_undo_state()

    def bgcolor_changed(self):
        dialog = ColorSelection(self.bgcolor.color)
        dialog.move(self.mapToGlobal(self.bgcolor.pos()))
        result = dialog.exec_()
        if result != QtWidgets.QDialog.Accepted:
            return
        self.bgcolor.set_color(dialog.color)
        if not self.element:
            return
        self.element.bgcolor = dialog.color
        self.canvas.repaint()
        self.model.add_undo_state()

    def bgopacity_changed(self, value):
        if not isinstance(self.element, (Rectangle, Circle, Text)):
            return
        self.element.bgopacity = value
        self.canvas.repaint()

    def filled_toggled(self, state):
        self.bgcolor.setEnabled(state)
        self.bgopacity.setEnabled(state)
        if not isinstance(self.element, (Rectangle, Circle, Text)):
            return
        self.element.filled = state
        self.model.add_undo_state()
        self.canvas.repaint()

    def text_size_changed(self, value):
        if not isinstance(self.element, Text):
            return
        self.element.text_size = value
        self.model.drawcontext.text_size = value
        self.canvas.repaint()

    def change_alignment(self, index):
        if self.element is None:
            return
        self.element.alignment = index
        self.canvas.repaint()

    def text_changed(self):
        if not isinstance(self.element, Text):
            return
        self.element.text = self.text_content.toPlainText()
        self.canvas.tool.is_dirty = True
        self.canvas.repaint()

    def size_changed(self, value):
        if not isinstance(self.element, (Rectangle, Circle)):
            return
        self.element.linewidth = value
        self.canvas.repaint()

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
        self.bgcolor.set_color(shape.bgcolor)
        self.shape_width.setValue(shape.linewidth)
        self.filled.setChecked(shape.filled)
        self.bgcolor.setEnabled(shape.filled)
        self.bgopacity.setEnabled(shape.filled)
        self.bgopacity.setValue(shape.bgopacity)
        self.shape_width_row.show()
        self.bgcolor_row.show()
        self.filled_row.show()
        self.bgopacity_row.show()
        self.stroke_width_row.hide()
        self.tail_width_row.hide()
        self.head_size_row.hide()
        self.text_size_row.hide()
        self.text_content_row.hide()
        self.text_alignment_row.hide()

    def set_arrow(self, arrow):
        self.main_color.set_color(arrow.color)
        self.tail_width.setValue(arrow.tailwidth)
        self.head_size.setValue(arrow.headsize)
        self.bgcolor_row.hide()
        self.bgopacity_row.hide()
        self.filled_row.hide()
        self.stroke_width_row.hide()
        self.shape_width_row.hide()
        self.tail_width_row.show()
        self.head_size_row.show()
        self.text_size_row.hide()
        self.text_content_row.hide()
        self.text_alignment_row.hide()

    def set_stroke(self, stroke):
        self.main_color.set_color(stroke.color)
        self.stroke_width_row.show()
        self.bgcolor_row.hide()
        self.bgopacity_row.hide()
        self.filled_row.hide()
        self.shape_width_row.hide()
        self.tail_width_row.hide()
        self.head_size_row.hide()
        self.text_size_row.hide()
        self.text_content_row.hide()
        self.text_alignment_row.hide()

    def set_text(self, text):
        self.main_color.set_color(text.color)
        self.bgcolor.set_color(text.bgcolor)
        self.bgopacity.setValue(text.bgopacity)
        self.bgcolor.setEnabled(text.filled)
        self.bgopacity.setEnabled(text.filled)
        self.filled.setChecked(text.filled)
        self.text_size.setValue(text.text_size)
        self.text_alignment.setCurrentText(ALIGNMENTS[text.alignment])
        self.text_content.setText(text.text)
        self.text_content.setFocus(QtCore.Qt.MouseFocusReason)
        self.stroke_width_row.hide()
        self.shape_width_row.hide()
        self.tail_width_row.hide()
        self.head_size_row.hide()
        self.bgopacity_row.show()
        self.text_size_row.show()
        self.text_content_row.show()
        self.text_alignment_row.show()
        self.bgcolor_row.show()
        self.filled_row.show()

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


class FillableShapeSettings(QtWidgets.QWidget):
    def __init__(self, model, parent=None):
        super().__init__(parent=parent)
        self.model = model
        state = self.model.drawcontext.filled
        self.filled = QtWidgets.QCheckBox('Filled', checked=state)
        self.filled.toggled.connect(self.change_filled)
        self.bgcolor = ColorAction(self.model.drawcontext.bgcolor)
        self.bgcolor.setEnabled(state)
        self.bgcolor.released.connect(self.select_color)
        self.bgopacity = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.bgopacity.setMinimum(0)
        self.bgopacity.setMaximum(255)
        self.bgopacity.setValue(self.model.drawcontext.bgopacity)
        self.bgopacity.valueChanged.connect(self.bgopacity_changed)
        self.bgopacity.sliderReleased.connect(self.model.add_undo_state)
        self.bgopacity.setEnabled(state)

        form = QtWidgets.QFormLayout(self)
        form.addRow('', self.filled)
        form.addRow('Background color', self.bgcolor)
        form.addRow('Background opacity', self.bgopacity)

    def select_color(self):
        dialog = ColorSelection(self.bgcolor.color)
        dialog.move(self.mapToGlobal(self.bgcolor.pos()))
        result = dialog.exec_()
        if result != QtWidgets.QDialog.Accepted:
            return
        self.bgcolor.set_color(dialog.color)
        self.model.drawcontext.bgcolor = dialog.color

    def change_filled(self, state):
        self.model.drawcontext.filled = state
        self.bgcolor.setEnabled(state)
        self.bgopacity.setEnabled(state)

    def bgopacity_changed(self, value):
        self.model.drawcontext.bgopacity = value

    def set_model(self, model):
        self.model = model
        self.blockSignals(True)
        self.bgcolor.set_color(model.drawcontext.color)
        self.filled.setChecked(model.drawcontext.filled)
        self.bgopacity.setValue(model.drawcontext.bgopacity)
        self.blockSignals(False)
        self.repaint()
