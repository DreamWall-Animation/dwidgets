
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from functools import partial
from PySide2 import QtWidgets, QtCore, QtGui
from dwidgets.retakecanvas.canvas import Canvas
from dwidgets.retakecanvas.tools import (
    Navigator, NavigationTool, ArrowTool, CircleTool, RectangleTool, DrawTool)
from dwidgets.retakecanvas.viewport import ViewportMapper


UNDOLIMIT = 50
COLORS = [
    'red', '#141923', '#414168', '#3a7fa7', '#35e3e3', '#8fd970',
    '#5ebb49', '#458352', '#dcd37b', '#fffee5', '#ffd035', '#cc9245',
    '#a15c3e', '#a42f3b', '#f45b7a', '#c24998', '#81588d', '#bcb0c2',
    '#ffffff', 'black']


def icon(filename):
    folder = os.path.dirname(__file__)
    return QtGui.QIcon(f'{folder}/../icons/{filename}')


def set_shortcut(keysequence, parent, method, context=None):
    shortcut = QtWidgets.QShortcut(QtGui.QKeySequence(keysequence), parent)
    shortcut.setContext(context or QtCore.Qt.WidgetWithChildrenShortcut)
    shortcut.activated.connect(method)
    return shortcut


class LayerStack:

    def __init__(self):
        super().__init__()
        self.layers = []
        self.visibilities = []
        self.opacities = []
        self.current_index = None
        self.wash_color = '#FFFFFF'
        self.wash_opacity = 0
        self.undostack = []
        self.redostack = []
        self.undo_index = 0
        self.add_undo_state()

    def add(self):
        self.layers.append([])
        self.visibilities.append(True)
        self.opacities.append(255)
        self.current_index = len(self.layers) - 1
        self.add_undo_state()

    def set_current(self, index):
        self.current_index = index

    @property
    def current(self):
        if self.current_index is None:
            return
        return self.layers[self.current_index]

    def remove(self, element):
        if self.current:
            self.current.remove(element)
        self.add_undo_state()

    def delete(self, index=None):
        if not index and self.current:
            index = self.layers.index(self.current)
        if not index:
            return
        if index != self.current_index:
            return
        self.layers.pop(index)
        self.visibilities.pop(index)
        self.opacities.pop(index)

        if not self.layers:
            self.current = None
            self.add_undo_state()
            return
        self.current = self.layers[index - 1]
        self.add_undo_state()

    def get_undo_index(self):
        self.undo_index += 1
        return self.undo_index

    def add_undo_state(self):
        self.redostack = []
        state = {
            'index': self.get_undo_index(),
            'layers': [[elt.copy() for elt in layer] for layer in self.layers],
            'opacities': self.opacities.copy(),
            'visibilities': self.visibilities.copy(),
            'current': self.current_index,
            'wash_color': self.wash_color,
            'wash_opacity': self.wash_opacity
        }
        self.undostack.append(state)
        self.undostack = self.undostack[-UNDOLIMIT:]

    def restore_state(self, state):
        layers = [[elt.copy() for elt in layer] for layer in state['layers']]
        self.layers = layers
        self.current_index = state['current']
        self.wash_color = state['wash_color']
        self.wash_opacity = state['wash_opacity']
        self.visibilities = state['visibilities']
        self.opacities = state['opacities']

    def undo(self):
        if not self.undostack:
            return

        state = self.undostack.pop()
        self.redostack.append(state)
        if self.undostack:
            self.restore_state(self.undostack[-1])
        else:
            self.restore_state({
                'layers': [],
                'opacities': [],
                'visibilities': [],
                'current': None,
                'wash_color': '#FFFFFF',
                'wash_opacity': 0})

    def redo(self):
        if not self.redostack:
            return
        state = self.redostack.pop()
        self.undostack.append(state)
        self.restore_state(state)

    def __iter__(self):
        return zip(self.layers, self.visibilities, self.opacities).__iter__()


class Switcher(QtWidgets.QAbstractButton):
    switched = QtCore.Signal(bool)
    on_char = '👁'
    off_char = '◎'

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(25, 25)
        self.setCheckable(True)
        self.setChecked(True)

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            state = not self.isChecked()
            self.setChecked(state)
            self.switched.emit(state)
            self.repaint()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setPen(QtGui.QColor('white' if self.isChecked() else 'grey'))
        char = self.on_char if self.isChecked() else self.off_char
        painter.drawText(event.rect(), char)
        painter.end()


class Eye(Switcher):
    on_char = '👁'
    off_char = '◯'


class Current(Switcher):
    on_char = '👁'
    off_char = '◯'

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            if not self.isChecked():
                self.setChecked(True)
                self.switched.emit(True)
                self.repaint()


class LayerLine(QtWidgets.QWidget):
    undoRecordRequest = QtCore.Signal()
    edited = QtCore.Signal()
    selected = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self._current = Current()
        self._current.switched.connect(self.call_selected)
        self._switch = Eye()
        self._switch.switched.connect(self.call_edit)
        self._opacity = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self._opacity.valueChanged.connect(self.call_edit)
        self._opacity.sliderPressed.connect(self.slider_pressed)
        self._opacity.sliderReleased.connect(self.slider_released)
        self._opacity.setMinimum(0)
        self._opacity.setMaximum(255)
        self._opacity.setValue(255)
        self._opacity_ghost_value = None
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._current)
        layout.addWidget(self._switch)
        layout.addWidget(self._opacity)

    def slider_pressed(self):
        self._opacity_ghost_value = self._opacity.value()

    def slider_released(self):
        if self._opacity_ghost_value != self._opacity.value():
            self.undoRecordRequest.emit()
        self._opacity_ghost_value = None

    def set_selected_color(self):
        self.setStyleSheet('background-color: rgba(255, 255, 0, 50)')

    def select(self):
        self.set_selected_color()
        self._current.setChecked(True)

    def deselect(self):
        self.setStyleSheet('')
        self._current.setChecked(False)

    def call_selected(self, *_):
        self.set_selected_color()
        self.selected.emit()

    def call_edit(self, *_):
        self.edited.emit()

    @property
    def visible(self):
        return self._switch.isChecked()

    @visible.setter
    def visible(self, state):
        self._switch.setChecked(state)

    @property
    def opacity(self):
        return self._opacity.value()

    @opacity.setter
    def opacity(self, value):
        self._opacity.blockSignals(True)
        self._opacity.setValue(value)
        self._opacity.blockSignals(False)


class LayerView(QtWidgets.QWidget):
    edited = QtCore.Signal()

    def __init__(self, layerstack, parent=None):
        super().__init__(parent=parent)
        self.layerstack = layerstack
        self.layerstackview = QtWidgets.QListWidget()
        mode = QtWidgets.QAbstractItemView.NoSelection
        self.layerstackview.setSelectionMode(mode)
        # Washed out
        self._wash_color = ColorAction()
        self._wash_color.color = self.layerstack.wash_color
        self._wash_color.released.connect(self.change_wash_color)
        self._wash_opacity = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self._wash_opacity.valueChanged.connect(self._wash_changed)
        self._wash_opacity.sliderPressed.connect(self.start_slide)
        self._wash_opacity.sliderReleased.connect(self.end_slide)
        self._wash_opacity_ghost = None
        self._wash_opacity.setMinimum(0)
        self._wash_opacity.setValue(0)
        self._wash_opacity.setMaximum(255)
        self.washer = QtWidgets.QHBoxLayout()
        self.washer.setContentsMargins(0, 0, 0, 0)
        self.washer.addWidget(self._wash_color)
        self.washer.addWidget(self._wash_opacity)
        # Toolbar
        self.plus = QtWidgets.QAction(u'\u2795', self)
        self.plus.triggered.connect(self.layer_added)
        self.minus = QtWidgets.QAction('➖', self)
        self.minus.triggered.connect(self.remove_current_layer)
        self.toolbar = QtWidgets.QToolBar()
        self.toolbar.addAction(self.plus)
        self.toolbar.addAction(self.minus)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.layerstackview)
        layout.addLayout(self.washer)
        layout.addWidget(self.toolbar)

    def start_slide(self):
        self._wash_opacity_ghost = self._wash_opacity.value()

    def end_slide(self):
        if self._wash_opacity_ghost == self._wash_opacity.value():
            return
        self._wash_opacity_ghost = None
        self.layerstack.add_undo_state()

    def _wash_changed(self, *_):
        self.layerstack.wash_opacity = self._wash_opacity.value()
        self.edited.emit()

    def sync_layers(self):
        self.layerstackview.clear()
        for i, (_, visibility, opacity) in enumerate(self.layerstack):
            line = LayerLine()
            line.edited.connect(self.call_edited)
            line.selected.connect(partial(self.line_selected, line))
            line.undoRecordRequest.connect(self.layerstack.add_undo_state)
            line.visible = visibility
            line.opacity = opacity
            item = QtWidgets.QListWidgetItem(self.layerstackview)
            item.setSizeHint(line.sizeHint())
            self.layerstackview.insertItem(0, item)
            self.layerstackview.setItemWidget(item, line)
            if i == self.layerstack.current_index:
                line.select()
            else:
                line.deselect()
        self._wash_color.color = self.layerstack.wash_color
        self._wash_opacity.blockSignals(True)
        self._wash_opacity.setValue(self.layerstack.wash_opacity)
        self._wash_opacity.blockSignals(False)

    def layer_added(self):
        self.layerstack.add()
        line = LayerLine()
        line.edited.connect(self.call_edited)
        line.selected.connect(partial(self.line_selected, line))
        line.undoRecordRequest.connect(self.layerstack.add_undo_state)
        item = QtWidgets.QListWidgetItem(self.layerstackview)
        item.setSizeHint(line.sizeHint())
        self.layerstackview.insertItem(0, item)
        self.layerstackview.setItemWidget(item, line)
        line.select()
        self.line_selected(line)

    def call_edited(self):
        for i in range(self.layerstackview.count()):
            item = self.layerstackview.item(i)
            line = self.layerstackview.itemWidget(item)
            self.layerstack.visibilities[i] = line.visible
            self.layerstack.opacities[i] = line.opacity
        self.edited.emit()

    def remove_current_layer(self):
        index = self.layerstack.current_index
        self.layerstack.delete(index)
        self.layerstackview.takeItem(index)
        self.edited.emit()

    def line_selected(self, line):
        for i in range(self.layerstackview.count()):
            item = self.layerstackview.item(i)
            line2 = self.layerstackview.itemWidget(item)
            if line2 != line:
                line2.deselect()
            else:
                self.layerstack.set_current(i)

    def change_wash_color(self):
        dialog = ColorSelection(self._wash_color.color)
        dialog.move(self.mapToGlobal(self._wash_color.pos()))
        result = dialog.exec_()
        if result != QtWidgets.QDialog.Accepted:
            return
        self._wash_color.color = dialog.color
        self.layerstack.wash_color = dialog.color
        self.layerstack.add_undo_state()
        self.edited.emit()

    @property
    def layers(self):
        for i, (layer, *_) in enumerate(self.layerstack):
            item = self.layerstackview.item(i)
            line = item.widget()
            yield layer, line.is_visible, line.opacity

    @property
    def washer_color(self):
        return self._wash_color.color

    @property
    def washer_opacity(self):
        return self._washer_opacity.value()


class DrawContext:
    def __init__(self):
        self.color = COLORS[0]
        self.size = 10


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


class ColorAction(QtWidgets.QAbstractButton):
    def __init__(self, color=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setFocusPolicy(QtCore.Qt.NoFocus)
        self.setMouseTracking(True)
        self.color = color or COLORS[0]

    def mouseMouseEvent(self, _):
        self.repaint()

    def set_color(self, color):
        self.color = color
        self.repaint()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        cursor = self.mapFromGlobal(QtGui.QCursor.pos())
        hovered = event.rect().contains(cursor)
        color = QtCore.Qt.transparent if hovered else QtCore.Qt.black
        painter.setPen(color)
        painter.setBrush(QtGui.QColor(self.color))
        painter.drawRect(self.rect())

    def sizeHint(self):
        return QtCore.QSize(25, 25)


class RetakeCanvas(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.drawcontext = DrawContext()
        self.layerstack = LayerStack()
        self.navigator = Navigator()
        self.viewportmapper = ViewportMapper()

        self.layerview = LayerView(self.layerstack)
        self.layerview.edited.connect(self.repaint)
        self.canvas = Canvas(
            drawcontext=self.drawcontext,
            layerstack=self.layerstack,
            navigator=self.navigator,
            viewportmapper=self.viewportmapper)

        set_shortcut('CTRL+Z', self, self.undo)
        set_shortcut('CTRL+Y', self, self.redo)
        set_shortcut('F', self, self.canvas.reset)

        self.navigation = QtWidgets.QAction(icon('hand.png'), '', self)
        self.navigation.setCheckable(True)
        self.navigation.setChecked(True)
        self.navigation.triggered.connect(self.set_tool)
        self.navigation.tool = NavigationTool
        self.freedraw = QtWidgets.QAction(icon('freehand.png'), '', self)
        self.freedraw.setCheckable(True)
        self.freedraw.tool = DrawTool
        self.freedraw.triggered.connect(self.set_tool)
        self.rectangle = QtWidgets.QAction(icon('rectangle.png'), '', self)
        self.rectangle.setCheckable(True)
        self.rectangle.triggered.connect(self.set_tool)
        self.rectangle.tool = RectangleTool
        self.circle = QtWidgets.QAction(icon('circle.png'), '', self)
        self.circle.setCheckable(True)
        self.circle.triggered.connect(self.set_tool)
        self.circle.tool = CircleTool
        self.arrow = QtWidgets.QAction(icon('arrow.png'), '', self)
        self.arrow.setCheckable(True)
        self.arrow.triggered.connect(self.set_tool)
        self.arrow.tool = ArrowTool

        kwargs = dict(
            drawcontext=self.drawcontext,
            layerstack=self.layerstack,
            navigator=self.navigator,
            viewportmapper=self.viewportmapper)

        self.tools = {
            self.navigation: NavigationTool(**kwargs),
            self.freedraw: DrawTool(**kwargs),
            self.rectangle: RectangleTool(**kwargs),
            self.circle: CircleTool(**kwargs),
            self.arrow: ArrowTool(**kwargs)}

        self.tools_group = QtWidgets.QActionGroup(self)
        self.tools_group.addAction(self.navigation)
        self.tools_group.addAction(self.freedraw)
        self.tools_group.addAction(self.rectangle)
        self.tools_group.addAction(self.circle)
        self.tools_group.addAction(self.arrow)
        self.tools_group.setExclusive(True)

        self.main_settings = GeneralSettings(self.drawcontext)
        self.setting_widgets = {
            self.arrow: ArrowSettings(self.tools[self.arrow])}

        self.tools_bar = QtWidgets.QToolBar()
        self.tools_bar.addAction(self.navigation)
        self.tools_bar.addAction(self.freedraw)
        self.tools_bar.addAction(self.rectangle)
        self.tools_bar.addAction(self.circle)
        self.tools_bar.addAction(self.arrow)

        settings_layout = QtWidgets.QVBoxLayout()
        default_spacing = settings_layout.spacing()
        settings_layout.setContentsMargins(0, 0, 0, 0)
        settings_layout.setSpacing(0)
        settings_layout.addWidget(self.main_settings)
        settings_layout.addSpacing(default_spacing)
        settings_layout.addWidget(self.setting_widgets[self.arrow])

        left_widget = QtWidgets.QWidget()
        left_layout = QtWidgets.QVBoxLayout(left_widget)
        left_layout.addLayout(settings_layout)
        left_layout.addWidget(self.layerview)

        splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        splitter.addWidget(self.canvas)
        splitter.addWidget(left_widget)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.tools_bar)
        layout.addWidget(splitter)
        self.navigation.trigger()

    def render(self):
        return self.canvas.render()

    def undo(self):
        self.layerstack.undo()
        self.layerview.sync_layers()
        self.canvas.repaint()

    def redo(self):
        self.layerstack.redo()
        self.layerview.sync_layers()
        self.canvas.repaint()

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_1:
            self.navigation.trigger()
        elif event.key() == QtCore.Qt.Key_2:
            self.freedraw.trigger()
        elif event.key() == QtCore.Qt.Key_3:
            self.rectangle.trigger()
        elif event.key() == QtCore.Qt.Key_4:
            self.circle.trigger()
        elif event.key() == QtCore.Qt.Key_5:
            self.arrow.trigger()
        elif event.key() == QtCore.Qt.Key_F:
            self.canvas.reset()
        else:
            self.canvas.keyPressEvent(event)

    def enable_retake(self):
        self.layerview.show()
        self.tools_bar.show()

    def disable_retake(self):
        self.layerview.hide()
        self.tools_bar.hide()
        self.navigation.trigger()

    def keyReleaseEvent(self, event):
        return self.canvas.keyReleaseEvent(event)

    def set_baseimage(self, image):
        self.canvas.set_baseimage(image)

    def set_tool(self):
        action = self.tools_group.checkedAction()
        tool = self.tools[action]
        self.canvas.set_tool(tool)
        for widget in self.setting_widgets.values():
            widget.setVisible(widget == self.setting_widgets.get(action))

    def set_layerstack(self, layerstack):
        self.layerstack = layerstack
        self.layerview.sync_layers()


class GeneralSettings(QtWidgets.QWidget):
    def __init__(self, drawcontext, parent=None):
        super().__init__(parent=parent)
        self.drawcontext = drawcontext
        self.color = ColorAction(self.drawcontext.color)
        self.color.released.connect(self.select_color)
        self.linewidth = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.linewidth.setMinimum(0)
        self.linewidth.setMaximum(60)
        self.linewidth.setValue(self.drawcontext.size)
        self.linewidth.valueChanged.connect(self.set_linewidth)
        layout = QtWidgets.QFormLayout(self)
        layout.addRow('Main color:', self.color)
        layout.addRow('Linewidth:', self.linewidth)

    def set_linewidth(self, value):
        self.drawcontext.size = value

    def select_color(self):
        dialog = ColorSelection(self.color.color)
        dialog.move(self.mapToGlobal(self.color.pos()))
        result = dialog.exec_()
        if result != QtWidgets.QDialog.Accepted:
            return
        self.color.color = dialog.color
        self.drawcontext.color = dialog.color


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


if __name__ == "__main__":
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    app = QtWidgets.QApplication([])
    wid = RetakeCanvas()
    wid.canvas.set_baseimage(QtGui.QImage(r"C:\Users\Lionel\Desktop\gabaris_01.png"))
    # wid.disable_retake()
    # wid.layerstack.add()
    wid.show()
    app.exec_()
