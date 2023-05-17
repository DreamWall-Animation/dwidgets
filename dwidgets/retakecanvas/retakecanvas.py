import os
from functools import partial
from PySide2 import QtWidgets, QtCore
from dwidgets.retakecanvas.button import (
    ColorAction, ComparingMediaTable, Garbage, ToolNameLabel)
from dwidgets.retakecanvas import tools
from dwidgets.retakecanvas.canvas import Canvas
from dwidgets.retakecanvas.dialog import ColorSelection
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
        self.washer = QtWidgets.QHBoxLayout()
        self.washer.setContentsMargins(0, 0, 0, 0)
        self.washer.addWidget(self._wash_color)
        self.washer.addWidget(self._wash_opacity)
        # Toolbar
        self.plus = QtWidgets.QAction(u'\u2795', self)
        self.plus.triggered.connect(self.layer_added)
        self.minus = QtWidgets.QAction('➖', self)
        self.minus.triggered.connect(self.remove_current_layer)
        self.duplicate = QtWidgets.QAction('⧉', self)
        self.duplicate.triggered.connect(self.duplicate_layer)
        self.toolbar = QtWidgets.QToolBar()
        self.toolbar.addAction(self.plus)
        self.toolbar.addAction(self.minus)
        self.toolbar.addAction(self.duplicate)
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

        self.comparing_media = ComparingMediaTable(self.model)

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


class LeftScrollView(QtWidgets.QScrollArea):
    def __init__(self, child):
        super().__init__()
        self.child = child
        self.setWidget(self.child)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setMinimumWidth(self.child.minimumWidth())
        self.setWidgetResizable(True)


class RetakeCanvas(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.model = RetakeCanvasModel()

        self.layerview = LayerView(self.model)
        self.layerview.edited.connect(self.repaint)
        self.layerview.layoutChanged.connect(self.layout_changed)
        self.layerview.comparingRemoved.connect(self.remove_comparing)
        self.canvas = Canvas(self.model)
        self.canvas.selectionChanged.connect(self.update_shape_settings_view)
        self.canvas.isUpdated.connect(self.layerview.sync_view)

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
        self.open = QtWidgets.QAction(icon('open.png'), '', self)
        self.open.triggered.connect(self.call_open)

        set_shortcut('CTRL+Z', self, self.undo)
        set_shortcut('CTRL+Y', self, self.redo)
        set_shortcut('F', self, self.canvas.reset)
        set_shortcut('CTRL+V', self, self.paste)
        set_shortcut('CTRL+D', self, self.model.selection.clear)
        set_shortcut('DEL', self, self.do_delete)
        set_shortcut('M', self, self.move_a.trigger)
        set_shortcut('B', self, self.freedraw.trigger)
        set_shortcut('E', self, self.eraser.trigger)
        set_shortcut('S', self, self.selection_a.trigger)
        set_shortcut('R', self, self.rectangle.trigger)
        set_shortcut('C', self, self.circle.trigger)
        set_shortcut('A', self, self.arrow.trigger)

        kwargs = dict(canvas=self.canvas, model=self.model)
        self.tools = {
            self.navigation: tools.NavigationTool(**kwargs),
            self.move_a: tools.MoveTool(**kwargs),
            self.selection_a: tools.SelectionTool(**kwargs),
            self.freedraw: tools.DrawTool(**kwargs),
            self.eraser: tools.EraserTool(**kwargs),
            self.smoothdraw: tools.SmoothDrawTool(**kwargs),
            self.rectangle: tools.RectangleTool(**kwargs),
            self.circle: tools.CircleTool(**kwargs),
            self.arrow: tools.ArrowTool(**kwargs),
            self.text: tools.TextTool(**kwargs),
            self.wipes: tools.WipesTool(**kwargs)}

        self.tools_group = QtWidgets.QActionGroup(self)
        self.tools_group.addAction(self.navigation)
        self.tools_group.addAction(self.move_a)
        self.tools_group.addAction(self.selection_a)
        self.tools_group.addAction(self.freedraw)
        self.tools_group.addAction(self.smoothdraw)
        self.tools_group.addAction(self.eraser)
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
        self.tools_bar.addAction(self.open)

        settings_layout = QtWidgets.QVBoxLayout()
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
        left_layout.addWidget(ToolNameLabel('Tool Options'))
        left_layout.addLayout(settings_layout)
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
        self.splitter.setStretchFactor(1, 1)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.splitter)
        self.navigation.trigger()

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
        self.model.selection.clear()
        self.model.add_layer(undo=False, name="Pasted image")
        self.layerview.sync_view()
        rect = QtCore.QRectF(0, 0, image.size().width(), image.size().height())
        center = self.canvas.rect().center()
        rect.moveCenter(self.model.viewportmapper.to_units_coords(center))
        self.move_a.trigger()
        self.model.add_shape(Bitmap(image, rect))
        self.canvas.repaint()
        self.model.add_undo_state()

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

    def disable_retake_mode(self):
        self.canvas.set_tool(self.tools[self.navigation])
        self.model.locked = True
        self.left_scroll.hide()
        self.navigation.trigger()
        self.layerview.hide()
        self.tools_bar.hide()

    def keyReleaseEvent(self, event):
        return self.canvas.keyReleaseEvent(event)

    def set_baseimage(self, image):
        self.model.set_baseimage(image)
        self.canvas.repaint()

    def set_tool(self):
        action = self.tools_group.checkedAction()
        tool = self.tools[action]
        self.canvas.set_tool(tool)
        for widget in self.setting_widgets.values():
            widget.setVisible(widget == self.setting_widgets.get(action))

    def set_model(self, model):
        self.model = model
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
