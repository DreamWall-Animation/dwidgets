

UNDOLIMIT = 50


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

    def add_undo_state(self):
        self.redostack = []
        state = {
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
