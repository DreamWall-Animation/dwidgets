import os
from functools import partial
from PySide2 import QtWidgets, QtCore, QtGui
from dwidgets.retakecanvas.button import (
    ColorAction, ComparingMediaTable, Garbage, ToolNameLabel)
from dwidgets.retakecanvas import tools
from dwidgets.retakecanvas.canvas import Canvas
from dwidgets.retakecanvas.dialog import ColorSelection
from dwidgets.retakecanvas.layerstack import BLEND_MODE_NAMES
from dwidgets.retakecanvas.layerstackview import LayerStackView
from dwidgets.retakecanvas.model import RetakeCanvasModel
from dwidgets.retakecanvas.qtutils import icon, set_shortcut
from dwidgets.retakecanvas.settings import (
    GeneralSettings, ArrowSettings, FillableShapeSettings, SmoothDrawSettings,
    ShapeSettings)
from dwidgets.retakecanvas.selection import Selection
from dwidgets.retakecanvas.shapes import Bitmap
from dwidgets.retakecanvas.tools.erasertool import (
    erase_on_layer, get_point_to_erase)


class LayerView(QtWidgets.QWidget):
    edited = QtCore.Signal()
    layoutChanged = QtCore.Signal()
    comparingRemoved = QtCore.Signal(int)

    def __init__(self, model, parent=None):
        super().__init__(parent=parent)
        self.model = model
        self.model.imagestack = model.imagestack
        self.layerstackview = LayerStackView(self.model)
        self.layerstackview.current_changed.connect(self.sync_view)
        # Washed out
        self._wash_color = ColorAction()
        self._wash_color.color = self.model.wash_color
        self._wash_color.released.connect(self.change_wash_color)
        self._wash_opacity = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self._wash_opacity.valueChanged.connect(self._wash_changed)
        self._wash_opacity.sliderPressed.connect(self.start_slide)
        self._wash_opacity.sliderReleased.connect(self.end_slide)
        self._wash_opacity_ghost = None
        self._wash_opacity.setMinimum(0)
        self._wash_opacity.setValue(0)
        self._wash_opacity.setMaximum(255)
        self.washer_label = ToolNameLabel('Washer Options')
        self.washer = QtWidgets.QWidget()
        washer_layout = QtWidgets.QHBoxLayout(self.washer)
        washer_layout.setContentsMargins(0, 0, 0, 0)
        washer_layout.addWidget(self._wash_color)
        washer_layout.addWidget(self._wash_opacity)
        # Toolbar
        self.plus = QtWidgets.QAction(u'\u2795', self)
        self.plus.triggered.connect(self.layer_added)
        self.minus = QtWidgets.QAction('➖', self)
        self.minus.triggered.connect(self.remove_current_layer)
        self.duplicate = QtWidgets.QAction('⧉', self)
        self.duplicate.triggered.connect(self.duplicate_layer)
        self.blend_modes = QtWidgets.QComboBox()
        self.blend_modes.currentIndexChanged.connect(self.change_blend_mode)
        self.blend_modes.addItems(sorted(list(BLEND_MODE_NAMES.values())))
        spacer = QtWidgets.QWidget()
        spacer.setSizePolicy(*[QtWidgets.QSizePolicy.Expanding] * 2)
        self.toolbar = QtWidgets.QToolBar()
        self.toolbar.addAction(self.plus)
        self.toolbar.addAction(self.minus)
        self.toolbar.addAction(self.duplicate)
        self.toolbar.addWidget(spacer)
        self.toolbar.addWidget(self.blend_modes)
        # StackLayout
        self.tabled = QtWidgets.QAction(icon('table.png'), None, self)
        self.tabled.setCheckable(True)
        method = partial(self.change_layout, RetakeCanvasModel.GRID)
        self.tabled.triggered.connect(method)
        self.overlap = QtWidgets.QAction(icon('overlap.png'), None, self)
        self.overlap.setCheckable(True)
        method = partial(self.change_layout, RetakeCanvasModel.STACKED)
        self.overlap.triggered.connect(method)
        self.horizontal = QtWidgets.QAction(icon('horizontal.png'), None, self)
        self.horizontal.setCheckable(True)
        self.horizontal.setChecked(True)
        method = partial(self.change_layout, RetakeCanvasModel.HORIZONTAL)
        self.horizontal.triggered.connect(method)
        self.vertical = QtWidgets.QAction(icon('vertical.png'), None, self)
        self.vertical.setCheckable(True)
        method = partial(self.change_layout, RetakeCanvasModel.VERTICAL)
        self.vertical.triggered.connect(method)
        spacer = QtWidgets.QWidget()
        spacer.setSizePolicy(*[QtWidgets.QSizePolicy.Expanding] * 2)
        self.layouts = QtWidgets.QActionGroup(self)
        self.layouts.addAction(self.tabled)
        self.layouts.addAction(self.overlap)
        self.layouts.addAction(self.horizontal)
        self.layouts.addAction(self.vertical)
        self.layout_types = QtWidgets.QToolBar()
        self.layout_types.addActions(self.layouts.actions())
        action = self.layout_types.actions()[self.model.imagestack_layout]
        action.setChecked(True)
        self.layout_types.addWidget(spacer)

        self.delete_comparing = Garbage(self.layout_types)
        self.delete_comparing.removeIndex.connect(self.comparingRemoved.emit)
        self.layout_types.addWidget(self.delete_comparing)

        self.comparing_media_label = ToolNameLabel('Comparing Media')
        self.comparing_media = ComparingMediaTable(self.model)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(ToolNameLabel('Layers'))
        layout.addWidget(self.layerstackview)
        layout.addWidget(self.toolbar)
        layout.addWidget(self.washer_label)
        layout.addWidget(self.washer)
        layout.addWidget(self.comparing_media_label)
        layout.addWidget(self.comparing_media)
        layout.addWidget(self.layout_types)
        self.sync_view()

    def start_slide(self):
        self._wash_opacity_ghost = self._wash_opacity.value()

    def end_slide(self):
        if self._wash_opacity_ghost == self._wash_opacity.value():
            return
        self._wash_opacity_ghost = None
        self.model.add_undo_state()

    def _wash_changed(self, *_):
        self.model.wash_opacity = self._wash_opacity.value()
        self.edited.emit()

    def sync_view(self):
        self.comparing_media.updatesize()
        self.layerstackview.update_size()
        self.layerstackview.repaint()
        self._wash_color.color = self.model.wash_color
        self._wash_opacity.blockSignals(True)
        self._wash_opacity.setValue(self.model.wash_opacity)
        self._wash_opacity.blockSignals(False)
        self.blend_modes.blockSignals(True)
        self.blend_modes.setCurrentText(
            self.model.layerstack.current_blend_mode_name)
        self.blend_modes.blockSignals(False)

    def set_model(self, model):
        self.model = model
        self.comparing_media.set_model(model)
        self.layerstackview.set_model(model)
        self.layerstackview.update_size()
        self.layerstackview.repaint()
        action = self.layout_types.actions()[self.model.imagestack_layout]
        action.setChecked(True)

    def layer_added(self):
        self.model.add_layer()
        self.layerstackview.update_size()
        self.layerstackview.repaint()

    def duplicate_layer(self):
        self.model.duplicate_layer()
        self.layerstackview.update_size()
        self.layerstackview.repaint()

    def call_edited(self):
        self.layerstackview.repaint()
        self.edited.emit()

    def change_blend_mode(self):
        blend_mode = self.blend_modes.currentText()
        self.model.set_current_blend_mode_name(blend_mode)
        self.edited.emit()

    def remove_current_layer(self):
        index = self.model.layerstack.current_index
        self.model.layerstack.delete(index)
        self.model.add_undo_state()
        self.layerstackview.update_size()
        self.layerstackview.repaint()
        self.edited.emit()

    def change_layout(self, layout):
        self.model.imagestack_layout = layout
        self.layoutChanged.emit()

    def change_wash_color(self):
        dialog = ColorSelection(self._wash_color.color)
        dialog.move(self.mapToGlobal(self._wash_color.pos()))
        result = dialog.exec_()
        if result != QtWidgets.QDialog.Accepted:
            return
        self._wash_color.color = dialog.color
        self.model.wash_color = dialog.color
        self.model.add_undo_state()
        self.edited.emit()

    @property
    def washer_color(self):
        return self._wash_color.color

    @property
    def washer_opacity(self):
        return self._washer_opacity.value()


class ZoomLabel(QtWidgets.QWidget):
    def __init__(self, canvas, model, parent=None):
        super().__init__(parent)
        self.setFixedSize(75, 25)
        self.model = model
        self.canvas = canvas
        self.clicked = False
        self.hovered = False
        self.setMouseTracking(True)

    def show_menu(self):
        menu = QtWidgets.QMenu()
        for size in (0.25, 0.5, 1, 1.5, 2, 3):
            action = QtWidgets.QAction(f'{round(size * 100)}%', self)
            action.size = size
            menu.addAction(action)
        action = menu.exec_(self.mapToGlobal(self.rect().bottomLeft()))
        if action:
            self.canvas.set_zoom(action.size)

    def enterEvent(self, event):
        self.hovered = True
        self.repaint()

    def mouseMoveEvent(self, event):
        self.hovered = self.rect().contains(event.pos())
        self.repaint()

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.clicked = True
            self.repaint()

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.show_menu()
            self.clicked = False
            self.repaint()

    def leaveEvent(self, event):
        self.hovered = False
        self.repaint()

    def set_model(self, model):
        self.model = model
        self.repaint()

    def paintEvent(self, _):
        painter = QtGui.QPainter(self)

        options = QtWidgets.QStyleOptionToolButton()
        options.initFrom(self)
        options.rect = self.rect()
        options.text = f'{round(self.model.viewportmapper.zoom * 100)}%'
        options.features = (
            QtWidgets.QStyleOptionToolButton.HasMenu)
        options.arrowType = QtCore.Qt.DownArrow

        if self.clicked:
            options.state = QtWidgets.QStyle.State_Sunken
        elif self.hovered:
            options.state = QtWidgets.QStyle.State_MouseOver
            rect = self.rect()
            rect.setWidth(rect.width() - 1)
            rect.setHeight(rect.height() - 1)
            painter.drawRect(rect)
        try:
            QtWidgets.QApplication.style().drawComplexControl(
                QtWidgets.QStyle.CC_ToolButton,
                options, painter, self)
        except RuntimeError:
            # Embed in some application, the style() is deleted and try to
            # reach it crash the entire app.
            pass
        finally:
            painter.drawText(self.rect(), QtCore.Qt.AlignCenter, options.text)
            painter.end()


class LeftScrollView(QtWidgets.QScrollArea):
    def __init__(self, child):
        super().__init__()
        self.child = child
        self.setWidget(self.child)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setMinimumWidth(self.child.minimumWidth())
        self.setWidgetResizable(True)


class RetakeCanvas(QtWidgets.QWidget):
    def __init__(self, model=None, parent=None):
        super().__init__(parent=parent)
        self.model = model or RetakeCanvasModel()
        self.central_widget = QtWidgets.QWidget()

        self.fullscreen_window = None

        self.layerview = LayerView(self.model, parent=self)
        self.layerview.edited.connect(self.repaint)
        self.layerview.layoutChanged.connect(self.layout_changed)
        self.layerview.comparingRemoved.connect(self.remove_comparing)

        self.canvas = Canvas(self.model)
        self.canvas.selectionChanged.connect(self.update_shape_settings_view)
        self.canvas.isUpdated.connect(self.layerview.sync_view)
        self.canvas.zoomChanged.connect(self.zoom_changed)

        self.undo_action = QtWidgets.QAction(icon('undo.png'), '', self)
        self.undo_action.triggered.connect(self.undo)
        self.redo_action = QtWidgets.QAction(icon('redo.png'), '', self)
        self.redo_action.triggered.connect(self.redo)
        self.navigation = QtWidgets.QAction(icon('hand.png'), '', self)
        self.navigation.setCheckable(True)
        self.navigation.setChecked(True)
        self.navigation.triggered.connect(self.set_tool)
        self.navigation.tool = tools.NavigationTool
        self.move_a = QtWidgets.QAction(icon('move.png'), '', self)
        self.move_a.setCheckable(True)
        self.move_a.tool = tools.MoveTool
        self.move_a.triggered.connect(self.set_tool)
        self.transform = QtWidgets.QAction(icon('transform.png'), '', self)
        self.transform.setCheckable(True)
        self.transform.tool = tools.TransformTool
        self.transform.triggered.connect(self.set_tool)
        self.selection_a = QtWidgets.QAction(icon('selection.png'), '', self)
        self.selection_a.setCheckable(True)
        self.selection_a.tool = tools.SelectionTool
        self.selection_a.triggered.connect(self.set_tool)
        self.freedraw = QtWidgets.QAction(icon('freehand.png'), '', self)
        self.freedraw.setCheckable(True)
        self.freedraw.tool = tools.DrawTool
        self.freedraw.triggered.connect(self.set_tool)
        self.smoothdraw = QtWidgets.QAction(icon('smoothdraw.png'), '', self)
        self.smoothdraw.setCheckable(True)
        self.smoothdraw.tool = tools.SmoothDrawTool
        self.smoothdraw.triggered.connect(self.set_tool)
        self.eraser = QtWidgets.QAction(icon('eraser.png'), '', self)
        self.eraser.setCheckable(True)
        self.eraser.tool = tools.EraserTool
        self.eraser.triggered.connect(self.set_tool)
        self.line = QtWidgets.QAction(icon('line.png'), '', self)
        self.line.setCheckable(True)
        self.line.triggered.connect(self.set_tool)
        self.line.tool = tools.LineTool
        self.rectangle = QtWidgets.QAction(icon('rectangle.png'), '', self)
        self.rectangle.setCheckable(True)
        self.rectangle.triggered.connect(self.set_tool)
        self.rectangle.tool = tools.RectangleTool
        self.circle = QtWidgets.QAction(icon('circle.png'), '', self)
        self.circle.setCheckable(True)
        self.circle.triggered.connect(self.set_tool)
        self.circle.tool = tools.CircleTool
        self.arrow = QtWidgets.QAction(icon('arrow.png'), '', self)
        self.arrow.setCheckable(True)
        self.arrow.triggered.connect(self.set_tool)
        self.arrow.tool = tools.ArrowTool
        self.text = QtWidgets.QAction(icon('text.png'), '', self)
        self.text.setCheckable(True)
        self.text.triggered.connect(self.set_tool)
        self.text.tool = tools.TextTool
        self.wipes = QtWidgets.QAction(icon('wipes.png'), '', self)
        self.wipes.setCheckable(True)
        self.wipes.setEnabled(False)
        self.wipes.triggered.connect(self.set_tool)
        self.wipes.tool = tools.ArrowTool
        self.zoom = ZoomLabel(self.canvas, self.model)
        self.open = QtWidgets.QAction(icon('open.png'), '', self)
        self.open.triggered.connect(self.call_open)

        set_shortcut('CTRL+Z', self.central_widget, self.undo)
        set_shortcut('CTRL+Y', self.central_widget, self.redo)
        set_shortcut('F', self.central_widget, self.canvas.reset)
        set_shortcut('CTRL+V', self.central_widget, self.paste)
        set_shortcut('CTRL+D', self.central_widget, self.model.selection.clear)
        set_shortcut('DEL', self.central_widget, self.do_delete)
        set_shortcut('M', self.central_widget, self.move_a.trigger)
        set_shortcut('B', self.central_widget, self.freedraw.trigger)
        set_shortcut('E', self.central_widget, self.eraser.trigger)
        set_shortcut('S', self.central_widget, self.selection_a.trigger)
        set_shortcut('L', self.central_widget, self.line.trigger)
        set_shortcut('R', self.central_widget, self.rectangle.trigger)
        set_shortcut('C', self.central_widget, self.circle.trigger)
        set_shortcut('T', self.central_widget, self.text.trigger)
        set_shortcut('A', self.central_widget, self.arrow.trigger)
        set_shortcut('Tab', self.central_widget, self.toggle_panel)
        set_shortcut('F11', self.central_widget, self.switch_fullscreen)
        set_shortcut(
            QtCore.Qt.Key_Period | QtCore.Qt.KeypadModifier,
            self.central_widget,
            partial(self.canvas.set_zoom, 0.25))
        set_shortcut(
            QtCore.Qt.Key_0 | QtCore.Qt.KeypadModifier,
            self.central_widget,
            partial(self.canvas.set_zoom, 0.5))
        set_shortcut(
            QtCore.Qt.Key_1 | QtCore.Qt.KeypadModifier,
            self.central_widget,
            partial(self.canvas.set_zoom, 1))
        set_shortcut(
            QtCore.Qt.Key_2 | QtCore.Qt.KeypadModifier,
            self.central_widget,
            partial(self.canvas.set_zoom, 1.5))
        set_shortcut(
            QtCore.Qt.Key_3 | QtCore.Qt.KeypadModifier,
            self.central_widget,
            partial(self.canvas.set_zoom, 2))

        kwargs = dict(canvas=self.canvas, model=self.model)
        self.tools = {
            self.navigation: tools.NavigationTool(**kwargs),
            self.move_a: tools.MoveTool(**kwargs),
            self.selection_a: tools.SelectionTool(**kwargs),
            self.freedraw: tools.DrawTool(**kwargs),
            self.eraser: tools.EraserTool(**kwargs),
            self.smoothdraw: tools.SmoothDrawTool(**kwargs),
            self.line: tools.LineTool(**kwargs),
            self.transform: tools.TransformTool(**kwargs),
            self.rectangle: tools.RectangleTool(**kwargs),
            self.circle: tools.CircleTool(**kwargs),
            self.arrow: tools.ArrowTool(**kwargs),
            self.text: tools.TextTool(**kwargs),
            self.wipes: tools.WipesTool(**kwargs)}

        self.tools_group = QtWidgets.QActionGroup(self)
        self.tools_group.addAction(self.navigation)
        self.tools_group.addAction(self.move_a)
        self.tools_group.addAction(self.transform)
        self.tools_group.addAction(self.selection_a)
        self.tools_group.addAction(self.freedraw)
        self.tools_group.addAction(self.smoothdraw)
        self.tools_group.addAction(self.eraser)
        self.tools_group.addAction(self.line)
        self.tools_group.addAction(self.rectangle)
        self.tools_group.addAction(self.circle)
        self.tools_group.addAction(self.arrow)
        self.tools_group.addAction(self.text)
        self.tools_group.addAction(self.wipes)
        self.tools_group.setExclusive(True)

        self.main_settings = GeneralSettings(self.model)
        self.fillable_shape_settings = FillableShapeSettings(self.model)
        self.setting_widgets = {
            self.text: self.fillable_shape_settings,
            self.rectangle: self.fillable_shape_settings,
            self.circle: self.fillable_shape_settings,
            self.arrow: ArrowSettings(self.tools[self.arrow]),
            self.smoothdraw: SmoothDrawSettings(self.tools[self.smoothdraw])}

        spacer = QtWidgets.QWidget()
        spacer.setSizePolicy(*[QtWidgets.QSizePolicy.Expanding] * 2)

        self.tools_bar = QtWidgets.QToolBar()
        self.tools_bar.addAction(self.undo_action)
        self.tools_bar.addAction(self.redo_action)
        self.tools_bar.addSeparator()
        self.tools_bar.addActions(self.tools_group.actions())
        self.tools_bar.addWidget(spacer)
        self.tools_bar.addWidget(self.zoom)
        self.tools_bar.addAction(self.open)

        self.settings_widget_label = ToolNameLabel('Tool Options')
        self.settings_widget = QtWidgets.QWidget()
        settings_layout = QtWidgets.QVBoxLayout(self.settings_widget)
        default_spacing = settings_layout.spacing()
        settings_layout.setContentsMargins(0, 0, 0, 0)
        settings_layout.setSpacing(0)
        settings_layout.addWidget(self.main_settings)
        settings_layout.addSpacing(default_spacing)
        settings_layout.addWidget(self.setting_widgets[self.arrow])
        settings_layout.addWidget(self.setting_widgets[self.smoothdraw])
        settings_layout.addWidget(self.fillable_shape_settings)

        self.shape_settings_label = ToolNameLabel('Shape Options')
        self.shape_settings = ShapeSettings(self.canvas, self.model)

        self.left_widget = QtWidgets.QWidget()
        left_layout = QtWidgets.QVBoxLayout(self.left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(self.settings_widget_label)
        left_layout.addWidget(self.settings_widget)
        left_layout.addWidget(self.shape_settings_label)
        left_layout.addWidget(self.shape_settings)
        left_layout.addWidget(self.layerview)
        left_layout.addStretch(1)

        self.left_scroll = LeftScrollView(self.left_widget)
        self.left_scroll.setMinimumWidth(250)

        self.right_widget = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(self.right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        right_layout.addWidget(self.tools_bar)
        right_layout.addWidget(self.canvas)

        self.splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        self.splitter.addWidget(self.left_scroll)
        self.splitter.addWidget(self.right_widget)
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 2)

        layout = QtWidgets.QVBoxLayout(self.central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.splitter)

        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.central_widget)
        self.navigation.trigger()

    def zoom_changed(self):
        self.zoom.repaint()

    def do_delete(self):
        if self.model.layerstack.is_locked:
            return
        if self.model.selection.type == Selection.NO:
            return
        if self.model.selection.type == Selection.ELEMENT:
            self.model.layerstack.remove(self.model.selection.element)
            self.model.selection.clear()
            self.model.add_undo_state()
            return
        layer = self.model.layerstack.current
        classes = QtCore.QPoint, QtCore.QPointF
        points = [p for p in self.model.selection if isinstance(p, classes)]
        points_to_erase = get_point_to_erase(points, layer)
        erase_on_layer(points_to_erase, layer)
        self.model.selection.clear()
        self.model.add_undo_state()
        self.update_shape_settings_view()
        self.repaint()

    def call_open(self):
        paths, result = QtWidgets.QFileDialog.getOpenFileNames(
            self, 'Select Image', os.path.expanduser('~'),
            "Images (*.png *.xpm *.jpg *.webp)")
        if not result:
            return
        self.layerview.layerstackview.add_layers_from_paths(paths)

    def update_shape_settings_view(self):
        state = self.shape_settings.update()
        self.shape_settings.setVisible(state)
        self.shape_settings_label.setVisible(state)

    def remove_comparing(self, index):
        self.model.delete_image(index)
        self.canvas.repaint()
        self.layerview.sync_view()

    def layer_names(self, include_hidden=True):
        if include_hidden:
            return self.model.layerstack.names
        layerstack = self.model.layerstack
        return [
            name for name, visible in
            zip(layerstack.names, layerstack.visibilities)
            if visible]

    def render(self, model):
        return self.canvas.render(model=model)

    def undo(self):
        self.model.undo()
        self.model.selection.clear()
        self.layerview.sync_view()
        self.canvas.repaint()

    def redo(self):
        self.model.redo()
        self.model.selection.clear()
        self.layerview.sync_view()
        self.canvas.repaint()

    def paste(self):
        if self.model.locked:
            return
        image = QtWidgets.QApplication.clipboard().image()
        if not image:
            return
        return self.add_layer_image(
            name="Pasted image", image=image, center_on_canvas=True)

    def current_index(self):
        if not self.model:
            return
        return self.model.layerstack.current_index

    def add_layer_image(
            self, name, image, locked=False,
            index=None, blend_mode=None, center_on_canvas=False):
        """
        Import a qimage as new layer
        name: str layer name
        image: qimage
        """
        if not self.model:
            return
        if self.model.baseimage is None or self.model.baseimage.isNull():
            baseimage = QtGui.QImage(QtCore.QSize(
                image.size()), QtGui.QImage.Format_Alpha8)
            baseimage.fill(QtCore.Qt.transparent)
            self.model.set_baseimage(baseimage)
        self.model.selection.clear()
        self.model.add_layer(
            undo=False, name=name, locked=locked,
            blend_mode=blend_mode, index=index)
        self.layerview.sync_view()
        rect = QtCore.QRectF(0, 0, image.size().width(), image.size().height())
        if center_on_canvas:
            center = self.canvas.rect().center()
            rect.moveCenter(self.model.viewportmapper.to_units_coords(center))
        self.move_a.trigger()
        self.model.add_shape(Bitmap(image, rect))
        self.canvas.repaint()
        self.model.add_undo_state()

    def remove_layer(self, index):
        if not self.model:
            return
        self.model.layerstack.delete(index)
        self.model.add_undo_state()
        self.layerview.layerstackview.update_size()
        self.layerview.layerstackview.repaint()

    def clear(self):
        """
        Clear current document.
        """
        self.set_model(RetakeCanvasModel())

    def layout_changed(self):
        state = self.model.imagestack_layout == RetakeCanvasModel.STACKED
        self.wipes.setEnabled(state)
        if not state and self.tools_group.checkedAction() == self.wipes:
            self.navigation.trigger()
        self.canvas.repaint()

    def showEvent(self, event):
        self.canvas.reset()
        super().showEvent(event)

    def reset(self):
        self.canvas.reset()
        self.repaint()

    def keyPressEvent(self, event):
        self.canvas.keyPressEvent(event)

    def enable_retake_mode(self):
        self.model.locked = False
        self.left_scroll.show()
        self.layerview.show()
        self.tools_bar.show()
        self.navigation.trigger()
        self.shape_settings_label.show()
        self.shape_settings.show()
        self.settings_widget_label.show()
        self.settings_widget.show()

    def disable_retake_mode(self, keep_layer_view=False):
        self.canvas.set_tool(self.tools[self.navigation])
        self.model.locked = True
        self.navigation.trigger()
        self.tools_bar.hide()
        if not keep_layer_view:
            self.left_scroll.hide()
        else:
            self.settings_widget_label.hide()
            self.settings_widget.hide()
            self.shape_settings_label.hide()
            self.shape_settings.hide()

    def keyReleaseEvent(self, event):
        return self.canvas.keyReleaseEvent(event)

    def set_baseimage(self, image: QtGui.QImage):
        self.model.set_baseimage(image)
        self.canvas.repaint()

    def set_tool(self):
        action = self.tools_group.checkedAction()
        tool = self.tools[action]
        self.canvas.set_tool(tool)
        for widget in self.setting_widgets.values():
            widget.setVisible(widget == self.setting_widgets.get(action))

    def set_model(self, model):
        model = model or RetakeCanvasModel()
        self.model = model
        self.zoom.set_model(model)
        self.layerview.set_model(model)
        self.canvas.set_model(model)
        self.main_settings.set_model(model)
        self.shape_settings.set_model(model)
        self.fillable_shape_settings.set_model(model)
        self.update_shape_settings_view()
        for widget in self.tools.values():
            widget.set_model(model)
        self.layerview.sync_view()
        self.canvas.repaint()

    def toggle_panel(self):
        self.left_scroll.setVisible(not self.left_scroll.isVisible())

    def switch_fullscreen(self):
        if self.fullscreen_window is None:
            self.central_widget.setParent(None)
            self.layout.removeWidget(self.central_widget)
            self.fullscreen_window = FullscreenWindow(self)
            self.fullscreen_window.setCentralWidget(self.central_widget)
            self.fullscreen_window.showFullScreen()
            self.central_widget.setFocus(QtCore.Qt.MouseFocusReason)
        else:
            self.exit_fullscreen()

    def exit_fullscreen(self):
        self.central_widget.setParent(None)
        self.fullscreen_window.takeCentralWidget()
        self.layout.addWidget(self.central_widget)
        self.fullscreen_window.close()
        self.fullscreen_window = None
        self.canvas.setFocus()


class FullscreenWindow(QtWidgets.QMainWindow):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent

    def closeEvent(self, event):
        self.parent.exit_fullscreen()
        super().closeEvent(event)