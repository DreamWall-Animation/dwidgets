from contextlib import contextmanager
from PySide2 import QtWidgets, QtCore
from PySide2.QtCore import Qt


class PopupCheckList(QtWidgets.QPushButton):
    checked_items_changed = QtCore.Signal(list)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.checkboxes = []

        self.list_widget = QtWidgets.QListWidget()
        self.list_widget.itemClicked.connect(self._toggle_checkbox)
        clear_btn = QtWidgets.QPushButton(
            'clear', clicked=self.uncheck_all,
            maximumHeight=30, minimumWidth=60)
        invert_btn = QtWidgets.QPushButton(
            'invert', clicked=self.invert,
            maximumHeight=30, minimumWidth=60)
        all_btn = QtWidgets.QPushButton(
            'all', clicked=self.check_all,
            maximumHeight=30, minimumWidth=60)

        self.menu = QtWidgets.QMenu()
        menu_layout = QtWidgets.QVBoxLayout()
        menu_layout.setContentsMargins(0, 0, 0, 0)
        menu_layout.setSpacing(0)
        self.menu.setLayout(menu_layout)
        menu_layout.addWidget(self.list_widget)
        buttons_layout = QtWidgets.QHBoxLayout()
        menu_layout.addLayout(buttons_layout)
        buttons_layout.addWidget(clear_btn)
        buttons_layout.addWidget(invert_btn)
        buttons_layout.addWidget(all_btn)

        self.clicked.connect(self.popup)

    def mousePressEvent(self, event):
        if event.type() == QtCore.QEvent.MouseButtonPress:
            if event.button() == Qt.MiddleButton:
                self.uncheck_all()
            elif event.button() == Qt.RightButton:
                self.invert()
        return super().mousePressEvent(event)

    def _toggle_checkbox(self, item):
        cb = self.list_widget.itemWidget(item)
        cb.setChecked(not cb.isChecked())

    def _set_text(self):
        labels = self.checked_items_labels()
        if not labels or len(labels) == len(self.checkboxes):
            text = ' '
        elif len(labels) == 1:
            text = labels[0]
        else:
            text = f'({len(labels)}/{len(self.checkboxes)})'
        self.setText(text)

    def set_items(self, labels):
        self.checkboxes.clear()
        self.list_widget.clear()
        for label in labels:
            cb = QtWidgets.QCheckBox(label)
            cb.stateChanged.connect(self._set_text)
            cb.stateChanged.connect(self._send_signal)
            host_item = QtWidgets.QListWidgetItem()
            self.list_widget.addItem(host_item)
            self.list_widget.setItemWidget(host_item, cb)
            self.checkboxes.append(cb)

    def _send_signal(self):
        self.checked_items_changed.emit(self.checked_items_labels())

    @contextmanager
    def _single_signal(self):
        self.blockSignals(True)
        yield
        self.blockSignals(False)
        self._send_signal()

    def checked_items_labels(self):
        return [cb.text() for cb in self.checkboxes if cb.isChecked()]

    def check_all(self):
        with self._single_signal():
            [cb.setChecked(True) for cb in self.checkboxes]

    def uncheck_all(self):
        with self._single_signal():
            [cb.setChecked(False) for cb in self.checkboxes]

    def invert(self):
        with self._single_signal():
            [cb.setChecked(not cb.isChecked()) for cb in self.checkboxes]

    def popup(self):
        if not self.checkboxes:
            return
        parent = self.parent()
        self.list_widget.setMinimumWidth(self.width())
        checkbox_height = self.checkboxes[0].height() + 2
        pos = self.pos()
        self.list_widget.setMinimumHeight(min(
            self.list_widget.count() * checkbox_height, parent.height() / 3))
        pos.setY(pos.y() + self.height())
        self.menu.popup(parent.mapToGlobal(pos))
