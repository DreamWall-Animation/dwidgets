
import os
from functools import partial
from PySide2 import QtWidgets, QtCore, QtGui

from dwidgets.retakecanvas.canvas import Canvas
from dwidgets.retakecanvas.layerstack import LayerStack
from dwidgets.retakecanvas.layerstackview import LayerStackView
from dwidgets.retakecanvas.qtutils import icon, pixmap, set_shortcut
from dwidgets.retakecanvas.tools import (
    ArrowTool, CircleTool, DrawTool, MoveTool, Navigator, NavigationTool,
    RectangleTool, SelectionTool, SmoothDrawTool)
from dwidgets.retakecanvas.shapes import Bitmap
from dwidgets.retakecanvas.selection import Selection
from dwidgets.retakecanvas.viewport import ViewportMapper


COLORS = [
    'red', '#141923', '#414168', '#3a7fa7', '#35e3e3', '#8fd970',
    '#5ebb49', '#458352', '#dcd37b', '#fffee5', '#ffd035', '#cc9245',
    '#a15c3e', '#a42f3b', '#f45b7a', '#c24998', '#81588d', '#bcb0c2',
    '#ffffff', 'black']


class Garbage(QtWidgets.QAbstractButton):
    removeIndex = QtCore.Signal(int)

    def __init__(self, parent):
        super().__init__(parent)
        self.icon = pixmap('garbage.png')
        self.setFixedSize(parent.iconSize())
        self.setAcceptDrops(True)
        self.refuse = False
        self.hover = False

    def dragEnterEvent(self, event):
        mime = event.mimeData()
        if not isinstance(mime.parent(), ComparingMediaTable):
            self.refuse = True
            self.repaint()
            return
        self.hover = True
        self.repaint()
        return event.accept()

    def dragLeaveEvent(self, _):
        self.release()

    def leaveEvent(self, _):
        self.release()

    def dropEvent(self, event):
        index = event.mimeData().data('index').toInt()[0]
        self.removeIndex.emit(index)
        self.release()

    def release(self):
        self.hover = False
        self.refuse = False
        self.repaint()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.drawPixmap(self.rect(), self.icon)
        if self.hover:
            color = QtGui.QColor(QtCore.Qt.white)
            color.setAlpha(75)
        elif self.refuse:
            color = QtGui.QColor(QtCore.Qt.red)
            color.setAlpha(75)
        else:
            color = QtGui.QColor(QtCore.Qt.transparent)
        painter.setPen(QtCore.Qt.transparent)
        painter.setBrush(color)
        painter.drawRect(event.rect())
        painter.end()


class ComparingMediaTable(QtWidgets.QWidget):
    WIDTH = 50
    PADDING = 5

    def __init__(self, imagesstack, parent=None):
        super().__init__(parent=parent)
        self.imagesstack = imagesstack
        self.setMouseTracking(True)

    def rects(self):
        width = self.WIDTH + (2 * self.PADDING)
        left, top = 0, 0
        rects = []
        for _ in self.imagesstack:
            if left + width > self.width():
                left = 0
                top += width
            rect = QtCore.QRect(
                left + self.PADDING,
                top + self.PADDING,
                self.WIDTH,
                self.WIDTH)
            rects.append(rect)
            left += width
        return rects

    def updatesize(self):
        rects = self.rects()
        if not rects:
            self.setFixedHeight(8)
            return
        self.setFixedHeight(rects[-1].bottom() + self.PADDING)
        self.repaint()

    def resizeEvent(self, event):
        self.updatesize()

    def mousePressEvent(self, event):
        if event.button() != QtCore.Qt.LeftButton:
            return
        for i, rect in enumerate(self.rects()):
            if rect.contains(event.pos()):
                mime = QtCore.QMimeData()
                mime.setParent(self)
                data = QtCore.QByteArray()
                data.setNum(i)
                mime.setData('index', data)
                drag = QtGui.QDrag(self)
                drag.setMimeData(mime)
                drag.setHotSpot(event.pos())
                drag.exec_(QtCore.Qt.CopyAction)

    def mouseMoveEvent(self, _):
        self.repaint()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
        painter.setPen(QtCore.Qt.transparent)
        color = QtGui.QColor(QtCore.Qt.black)
        color.setAlpha(25)
        painter.setBrush(color)
        painter.drawRoundedRect(event.rect(), self.PADDING, self.PADDING)
        painter.setRenderHint(QtGui.QPainter.Antialiasing, False)
        for rect, image in zip(self.rects(), self.imagesstack):
            image = image.scaled(
                self.WIDTH,
                self.WIDTH,
                QtCore.Qt.KeepAspectRatio,
                QtCore.Qt.SmoothTransformation)
            image_rect = QtCore.QRect(
                0, 0, image.size().width(), image.size().height())
            image_rect.moveCenter(rect.center())
            painter.setPen(QtCore.Qt.transparent)
            painter.setBrush(QtCore.Qt.black)
            painter.drawRect(rect)
            painter.drawImage(image_rect, image)
            cursor = self.mapFromGlobal(QtGui.QCursor.pos())
            if rect.contains(cursor):
                painter.setPen(QtCore.Qt.yellow)
                color = QtGui.QColor(QtCore.Qt.white)
                color.setAlpha(50)
                painter.setBrush(color)
                painter.drawRect(rect)
                painter.setPen(QtCore.Qt.transparent)
        painter.end()


class ToolNameLabel(QtWidgets.QWidget):
    def __init__(self, text, parent=None):
        super().__init__(parent=parent)
        option = QtGui.QTextOption()
        option.setWrapMode(QtGui.QTextOption.NoWrap)
        self.text = QtGui.QStaticText(text)
        self.text.setTextOption(option)

    def sizeHint(self):
        return self.text.size().toSize()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        color = QtGui.QColor('black')
        color.setAlpha(50)
        painter.setBrush(color)
        pen = painter.pen()
        painter.setPen(QtCore.Qt.transparent)
        painter.drawRect(event.rect())
        painter.setPen(pen)
        painter.drawStaticText(10, 0, self.text)


class LayerView(QtWidgets.QWidget):
    edited = QtCore.Signal()
    layoutChanged = QtCore.Signal(int)
    comparingRemoved = QtCore.Signal(int)

    def __init__(self, layerstack, imagestack, parent=None):
        super().__init__(parent=parent)
        self.layerstack = layerstack
        self.imagestack = imagestack
        self.layerstackview = LayerStackView(self.layerstack)
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
        # StackLayout
        self.horizontal = QtWidgets.QAction(icon('horizontal.png'), None, self)
        self.horizontal.setCheckable(True)
        self.horizontal.setChecked(True)
        method = partial(self.layoutChanged.emit, 0)
        self.horizontal.triggered.connect(method)
        self.vertical = QtWidgets.QAction(icon('vertical.png'), None, self)
        self.vertical.setCheckable(True)
        method = partial(self.layoutChanged.emit, 1)
        self.vertical.triggered.connect(method)
        self.tabled = QtWidgets.QAction(icon('table.png'), None, self)
        self.tabled.setCheckable(True)
        method = partial(self.layoutChanged.emit, 2)
        self.tabled.triggered.connect(method)
        self.overlap = QtWidgets.QAction(icon('overlap.png'), None, self)
        self.overlap.setCheckable(True)
        method = partial(self.layoutChanged.emit, 3)
        self.overlap.triggered.connect(method)
        spacer = QtWidgets.QWidget()
        spacer.setSizePolicy(*[QtWidgets.QSizePolicy.Expanding] * 2)
        self.layouts = QtWidgets.QActionGroup(self)
        self.layouts.addAction(self.horizontal)
        self.layouts.addAction(self.vertical)
        self.layouts.addAction(self.tabled)
        self.layouts.addAction(self.overlap)
        self.layout_types = QtWidgets.QToolBar()
        self.layout_types.addActions(self.layouts.actions())
        self.layout_types.addWidget(spacer)

        self.delete_comparing = Garbage(self.layout_types)
        self.delete_comparing.removeIndex.connect(self.comparingRemoved.emit)
        self.layout_types.addWidget(self.delete_comparing)

        self.comparing_media = ComparingMediaTable(self.imagestack)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(ToolNameLabel('Layers'))
        layout.addWidget(self.layerstackview)
        layout.addWidget(self.toolbar)
        layout.addWidget(ToolNameLabel('Washer Options'))
        layout.addLayout(self.washer)
        layout.addWidget(ToolNameLabel('Comparing Media'))
        layout.addWidget(self.comparing_media)
        layout.addWidget(self.layout_types)

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
        self.comparing_media.updatesize()
        self.layerstackview.repaint()
        self._wash_color.color = self.layerstack.wash_color
        self._wash_opacity.blockSignals(True)
        self._wash_opacity.setValue(self.layerstack.wash_opacity)
        self._wash_opacity.blockSignals(False)

    def set_layerstack(self, layerstack):
        self.layerstack = layerstack
        self.layerstackview.set_layerstack(layerstack)
        self.layerstackview.update_size()
        self.layerstackview.repaint()

    def layer_added(self):
        self.layerstack.add()
        self.layerstackview.update_size()
        self.layerstackview.repaint()

    def call_edited(self):
        self.layerstackview.repaint()
        self.edited.emit()

    def remove_current_layer(self):
        index = self.layerstack.current_index
        self.layerstack.delete(index)
        self.layerstackview.repaint()
        self.edited.emit()

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
        self.imagesstack = []
        self.layerstack = LayerStack()
        self.navigator = Navigator()
        self.viewportmapper = ViewportMapper()
        self.selection = Selection()

        self.layerview = LayerView(self.layerstack, self.imagesstack)
        self.layerview.edited.connect(self.repaint)
        self.layerview.layoutChanged.connect(self.change_layout)
        self.layerview.comparingRemoved.connect(self.remove_comparing)
        self.canvas = Canvas(
            drawcontext=self.drawcontext,
            imagesstack=self.imagesstack,
            layerstack=self.layerstack,
            navigator=self.navigator,
            selection=self.selection,
            viewportmapper=self.viewportmapper)
        self.canvas.imageDropped.connect(self.layerview.sync_layers)

        self.navigation = QtWidgets.QAction(icon('hand.png'), '', self)
        self.navigation.setCheckable(True)
        self.navigation.setChecked(True)
        self.navigation.triggered.connect(self.set_tool)
        self.navigation.tool = NavigationTool
        self.move_a = QtWidgets.QAction(icon('move.png'), '', self)
        self.move_a.setCheckable(True)
        self.move_a.tool = MoveTool
        self.move_a.triggered.connect(self.set_tool)
        self.selection_a = QtWidgets.QAction(icon('selection.png'), '', self)
        self.selection_a.setCheckable(True)
        self.selection_a.tool = SelectionTool
        self.selection_a.triggered.connect(self.set_tool)
        self.freedraw = QtWidgets.QAction(icon('freehand.png'), '', self)
        self.freedraw.setCheckable(True)
        self.freedraw.tool = DrawTool
        self.freedraw.triggered.connect(self.set_tool)
        self.smoothdraw = QtWidgets.QAction(icon('smoothdraw.png'), '', self)
        self.smoothdraw.setCheckable(True)
        self.smoothdraw.tool = SmoothDrawTool
        self.smoothdraw.triggered.connect(self.set_tool)
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

        set_shortcut('CTRL+Z', self, self.undo)
        set_shortcut('CTRL+Y', self, self.redo)
        set_shortcut('F', self, self.canvas.reset)
        set_shortcut('CTRL+V', self, self.paste)
        set_shortcut('CTRL+D', self, self.selection.clear)
        set_shortcut('M', self, self.move_a.trigger)
        set_shortcut('B', self, self.freedraw.trigger)
        set_shortcut('s', self, self.selection_a.trigger)
        set_shortcut('R', self, self.rectangle.trigger)
        set_shortcut('C', self, self.circle.trigger)
        set_shortcut('A', self, self.arrow.trigger)

        kwargs = dict(
            canvas=self.canvas,
            drawcontext=self.drawcontext,
            layerstack=self.layerstack,
            navigator=self.navigator,
            selection=self.selection,
            viewportmapper=self.viewportmapper)

        self.tools = {
            self.navigation: NavigationTool(**kwargs),
            self.move_a: MoveTool(**kwargs),
            self.selection_a: SelectionTool(**kwargs),
            self.freedraw: DrawTool(**kwargs),
            self.smoothdraw: SmoothDrawTool(**kwargs),
            self.rectangle: RectangleTool(**kwargs),
            self.circle: CircleTool(**kwargs),
            self.arrow: ArrowTool(**kwargs)}

        self.tools_group = QtWidgets.QActionGroup(self)
        self.tools_group.addAction(self.navigation)
        self.tools_group.addAction(self.move_a)
        self.tools_group.addAction(self.selection_a)
        self.tools_group.addAction(self.freedraw)
        self.tools_group.addAction(self.smoothdraw)
        self.tools_group.addAction(self.rectangle)
        self.tools_group.addAction(self.circle)
        self.tools_group.addAction(self.arrow)
        self.tools_group.setExclusive(True)

        self.main_settings = GeneralSettings(self.drawcontext)
        self.setting_widgets = {
            self.arrow: ArrowSettings(self.tools[self.arrow]),
            self.smoothdraw: SmoothDrawSettings(self.tools[self.smoothdraw])}

        self.tools_bar = QtWidgets.QToolBar()
        self.tools_bar.addActions(self.tools_group.actions())

        settings_layout = QtWidgets.QVBoxLayout()
        default_spacing = settings_layout.spacing()
        settings_layout.setContentsMargins(0, 0, 0, 0)
        settings_layout.setSpacing(0)
        settings_layout.addWidget(self.main_settings)
        settings_layout.addSpacing(default_spacing)
        settings_layout.addWidget(self.setting_widgets[self.arrow])
        settings_layout.addWidget(self.setting_widgets[self.smoothdraw])

        self.left_widget = QtWidgets.QWidget()
        left_layout = QtWidgets.QVBoxLayout(self.left_widget)
        left_layout.addWidget(ToolNameLabel('Tool Options'))
        left_layout.addLayout(settings_layout)
        left_layout.addWidget(self.layerview)
        left_layout.addStretch(1)

        splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        splitter.addWidget(self.left_widget)
        splitter.addWidget(self.canvas)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.tools_bar)
        layout.addWidget(splitter)
        self.navigation.trigger()

    def remove_comparing(self, index):
        del self.imagesstack[index]
        self.canvas.repaint()
        self.layerview.sync_layers()

    def change_layout(self, layout):
        self.canvas.layout_type = layout
        self.canvas.repaint()

    def render(self, layerstack=None, baseimage=None):
        return self.canvas.render(layerstack, baseimage)

    def undo(self):
        self.layerstack.undo()
        self.selection.clear()
        self.layerview.sync_layers()
        self.canvas.repaint()

    def redo(self):
        self.layerstack.redo()
        self.selection.clear()
        self.layerview.sync_layers()
        self.canvas.repaint()

    def paste(self):
        image = QtWidgets.QApplication.clipboard().image()
        if not image:
            return
        self.selection.clear()
        self.layerstack.add(undo=False)
        self.layerview.sync_layers()
        rect = QtCore.QRectF(0, 0, image.size().width(), image.size().height())
        center = self.canvas.rect().center()
        rect.moveCenter(self.viewportmapper.to_units_coords(center))
        self.move_a.trigger()
        self.layerstack.current.append(Bitmap(image, rect))
        self.layerstack.add_undo_state()
        self.canvas.repaint()

    def showEvent(self, event):
        self.canvas.reset()
        super().showEvent(event)

    def keyPressEvent(self, event):
        self.canvas.keyPressEvent(event)

    def enable_retake_mode(self):
        self.left_widget.show()
        self.layerview.show()
        self.tools_bar.show()
        self.navigation.trigger()

    def disable_retake_mode(self):
        self.left_widget.hide()
        self.navigation.trigger()
        self.layerview.hide()
        self.tools_bar.hide()

    def keyReleaseEvent(self, event):
        return self.canvas.keyReleaseEvent(event)

    def set_baseimage(self, image):
        self.canvas.set_baseimage(image)
        self.canvas.repaint()

    def set_tool(self):
        action = self.tools_group.checkedAction()
        tool = self.tools[action]
        self.canvas.set_tool(tool)
        for widget in self.setting_widgets.values():
            widget.setVisible(widget == self.setting_widgets.get(action))

    def set_layerstack(self, layerstack):
        self.selection.clear()
        self.layerstack = layerstack
        self.layerview.set_layerstack(layerstack)
        self.canvas.layerstack = layerstack
        for widget in self.tools.values():
            widget.layerstack = layerstack
        self.layerview.sync_layers()
        self.canvas.repaint()


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
