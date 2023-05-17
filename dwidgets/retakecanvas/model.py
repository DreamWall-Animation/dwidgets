from PySide2 import QtGui, QtCore

from dwidgets.retakecanvas.layerstack import LayerStack, unique_layer_name
from dwidgets.retakecanvas.qtutils import COLORS
from dwidgets.retakecanvas.selection import Selection
from dwidgets.retakecanvas.navigator import Navigator
from dwidgets.retakecanvas.viewport import ViewportMapper


UNDOLIMIT = 50


class DrawContext:
    def __init__(self):
        self.color = COLORS[0]
        self.bgcolor = COLORS[0]
        self.bgopacity = 255
        self.filled = False
        self.size = 10
        self.text_size = 5


class RetakeCanvasModel:
    GRID = 0
    STACKED = 1
    HORIZONTAL = 2
    VERTICAL = 3

    def __init__(self, baseimage=None):
        self.locked = False

        self.baseimage = baseimage or QtGui.QImage()
        size = self.baseimage.size()
        self.baseimage_wipes = QtCore.QRect(0, 0, size.width(), size.height())
        self.imagestack = []
        self.imagestack_wipes = []
        self.imagestack_layout = self.GRID

        self.drawcontext = DrawContext()
        self.layerstack = LayerStack()
        self.navigator = Navigator()
        self.viewportmapper = ViewportMapper()
        self.selection = Selection()

        self.wash_color = '#FFFFFF'
        self.wash_opacity = 0

        self.undostack = []
        self.redostack = []
        self.add_undo_state()

    @property
    def texts(self):
        return self.layerstack.texts

    def append_image(self, image):
        self.imagestack.append(image)
        width, height = image.size().width(), image.size().height()
        self.imagestack_wipes.append(QtCore.QRect(0, 0, width, height))
        self.add_undo_state()

    def delete_image(self, index):
        del self.imagestack[index]
        del self.imagestack_wipes[index]
        self.add_undo_state()

    def duplicate_layer(self):
        if not self.layerstack.current:
            return
        self.layerstack.duplicate_current()
        self.add_undo_state()

    def set_baseimage(self, image):
        self.baseimage = image
        width, height = image.size().width(), image.size().height()
        self.baseimage_wipes = QtCore.QRect(0, 0, width, height)

    def add_layer(self, undo=True, name=None):
        name = name or 'Layer'
        name = unique_layer_name(name, self.layerstack.names)
        self.layerstack.add(name)
        if undo:
            self.add_undo_state()

    def move_layer(self, old_index, new_index):
        self.layerstack.move_layer(old_index, new_index)
        self.add_undo_state()

    def add_shape(self, shape):
        self.layerstack.current.append(shape)
        self.add_undo_state()

    def add_undo_state(self):
        self.redostack = []
        wipes = [QtCore.QRectF(w) for w in self.imagestack_wipes]
        layers = self.layerstack.layers
        state = {
            'baseimage_wipes': QtCore.QRectF(self.baseimage_wipes),
            'imagestack': [QtGui.QImage(img) for img in self.imagestack],
            'imagestack_wipes': wipes,
            'layers': [[elt.copy() for elt in layer] for layer in layers],
            'locks': self.layerstack.locks.copy(),
            'opacities': self.layerstack.opacities.copy(),
            'names': self.layerstack.names.copy(),
            'visibilities': self.layerstack.visibilities.copy(),
            'current': self.layerstack.current_index,
            'wash_color': self.wash_color,
            'wash_opacity': self.wash_opacity
        }
        self.undostack.append(state)
        self.undostack = self.undostack[-UNDOLIMIT:]

    def restore_state(self, state):
        layers = [[elt.copy() for elt in layer] for layer in state['layers']]
        self.baseimage_wipes = state['baseimage_wipes']
        self.imagestack = state['imagestack']
        self.imagestack_wipes = state['imagestack_wipes']
        self.layerstack.layers = layers
        self.layerstack.locks = state['locks']
        self.layerstack.opacities = state['opacities']
        self.layerstack.names = state['names']
        self.layerstack.visibilities = state['visibilities']
        self.layerstack.current_index = state['current']
        self.wash_color = state['wash_color']
        self.wash_opacity = state['wash_opacity']

    def undo(self):
        if not self.undostack:
            return
        state = self.undostack.pop()
        self.redostack.append(state)
        state = self.undostack[-1] if self.undostack else self.default_state()
        self.restore_state(state)

    def redo(self):
        if not self.redostack:
            return
        state = self.redostack.pop()
        self.undostack.append(state)
        self.restore_state(state)

    def default_state(self):
        wipes = QtCore.QRectF(
            0, 0, self.baseimage.size().width(),
            self.baseimage.size().height())

        return {
            'baseimage_wipes': wipes,
            'imagestack': [],
            'imagestack_wipes': [],
            'layers': [],
            'locks': [],
            'names': [],
            'opacities': [],
            'visibilities': [],
            'current': None,
            'wash_color': '#FFFFFF',
            'wash_opacity': 0,
        }
