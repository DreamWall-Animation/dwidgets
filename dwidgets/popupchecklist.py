from PySide2 import QtWidgets, QtCore


class PopupCheckList(QtWidgets.QPushButton):
    checked_items_changed = QtCore.Signal(list)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.checkboxes = []
        self.menu = QtWidgets.QMenu()
        self.clicked.connect(self.popup)

    def _set_text(self):
        labels = self.checked_items_labels()
        if not labels:
            text = ' '
        elif len(labels) == 1 or len(labels) == len(self.checkboxes):
            text = labels[0]
        else:
            text = f'({len(labels)}/{len(self.checkboxes)})'
        self.setText(text)

    def set_items(self, labels):
        self.menu = QtWidgets.QMenu()
        menu_layout = QtWidgets.QVBoxLayout()
        menu_layout.setContentsMargins(2, 2, 2, 2)
        menu_layout.setSpacing(0)
        self.menu.setLayout(menu_layout)

        self.checkboxes.clear()
        for label in labels:
            cb = QtWidgets.QCheckBox(label)
            cb.stateChanged.connect(self._set_text)
            cb.stateChanged.connect(self._send_signal)
            menu_layout.addWidget(cb)
            self.checkboxes.append(cb)

        clear_btn = QtWidgets.QPushButton(
            'clear', clicked=self.uncheck_all, maximumHeight=30)
        menu_layout.addWidget(clear_btn)
        all_btn = QtWidgets.QPushButton(
            'all', clicked=self.check_all, maximumHeight=30)
        menu_layout.addWidget(all_btn)

    def _send_signal(self):
        self.checked_items_changed.emit(self.checked_items_labels())

    def checked_items_labels(self):
        return [cb.text() for cb in self.checkboxes if cb.isChecked()]

    def check_all(self):
        [cb.setChecked(True) for cb in self.checkboxes]

    def uncheck_all(self):
        [cb.setChecked(False) for cb in self.checkboxes]

    def popup(self):
        pos = self.pos()
        pos.setY(pos.y() + self.height())
        self.menu.popup(self.parent().mapToGlobal(pos))
