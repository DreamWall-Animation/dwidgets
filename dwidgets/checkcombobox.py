from PySide2 import QtWidgets, QtCore


class CheckComboBox(QtWidgets.QComboBox):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._changed = False
        self.view().pressed.connect(self.handleItemPressed)
        self.setEditable(True)
        self.lineEdit().installEventFilter(self)
        self.lineEdit().cursorPositionChanged.connect(self.showPopup)

    def eventFilter(self, watched, event):
        items = [self.model().item(i) for i in range(self.count())]
        checked_items_texts = [i.text() for i in items if i.checkState()]
        if not checked_items_texts:
            label = ' '
        elif len(checked_items_texts) == 1:
            label = checked_items_texts[0]
        else:
            label = f'({len(checked_items_texts)})'
        self.lineEdit().setText(label)
        return super().eventFilter(watched, event)

    def setItemChecked(self, index, checked=False):
        item = self.model().item(index, self.modelColumn())
        if checked:
            item.setCheckState(QtCore.Qt.Checked)
        else:
            item.setCheckState(QtCore.Qt.Unchecked)

    def handleItemPressed(self, index):
        item = self.model().itemFromIndex(index)
        if item.checkState() == QtCore.Qt.Checked:
            item.setCheckState(QtCore.Qt.Unchecked)
        else:
            item.setCheckState(QtCore.Qt.Checked)
        self._changed = True

    def hidePopup(self):
        if not self._changed:
            super().hidePopup()
        self._changed = False

    def itemChecked(self, index):
        item = self.model().item(index, self.modelColumn())
        return item.checkState() == QtCore.Qt.Checked
