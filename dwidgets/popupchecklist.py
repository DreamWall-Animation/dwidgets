from contextlib import contextmanager
from PySide2 import QtWidgets, QtCore
from PySide2.QtCore import Qt


EMPTY_LABEL = '-'


def get_multiple_selection_text(
        selected_labels, max_labels, included_title=None):
    if not selected_labels or len(selected_labels) == max_labels:
        text = f'{included_title} (off)' if included_title else EMPTY_LABEL
    elif len(selected_labels) == 1:
        text = selected_labels[0]
        text = f'{included_title}: {text}' if included_title else text
    else:
        text = f'({len(selected_labels)}/{max_labels})'
        text = f'{included_title}: {text}' if included_title else text
    return text


class ListWidgetForCheckboxes(QtWidgets.QListWidget):
    """
    Only here to be able to style it differently.
    """


class PopupCheckList(QtWidgets.QMenu):
    checked_items_changed = QtCore.Signal(list)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.checkboxes = []
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)

        self.list_widget = ListWidgetForCheckboxes(
            minimumHeight=200, minimumWidth=200)
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

        menu_layout = QtWidgets.QVBoxLayout()
        menu_layout.setContentsMargins(0, 0, 0, 0)
        menu_layout.setSpacing(0)
        self.setLayout(menu_layout)
        menu_layout.addWidget(self.list_widget)
        buttons_layout = QtWidgets.QHBoxLayout()
        menu_layout.addLayout(buttons_layout)
        buttons_layout.addWidget(clear_btn)
        buttons_layout.addWidget(invert_btn)
        buttons_layout.addWidget(all_btn)

    def _toggle_checkbox(self, item):
        cb = self.list_widget.itemWidget(item)
        cb.setChecked(not cb.isChecked())

    def set_items(self, labels, checked=None):
        checked = checked if checked is not None else []
        self.checkboxes.clear()
        self.list_widget.clear()
        for label in labels:
            cb = QtWidgets.QCheckBox(label, checked=label in checked)
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

    def all_checked(self):
        return all(cb.isChecked() for cb in self.checkboxes)

    def check_all(self):
        with self._single_signal():
            [cb.setChecked(True) for cb in self.checkboxes]

    def uncheck_all(self):
        with self._single_signal():
            [cb.setChecked(False) for cb in self.checkboxes]

    def invert(self):
        with self._single_signal():
            [cb.setChecked(not cb.isChecked()) for cb in self.checkboxes]

    def set_checked_items(self, labels, emit_signal=True):
        self.uncheck_all()
        self.blockSignals(True)
        for checkbox in self.checkboxes:
            if checkbox.text() in labels:
                checkbox.setChecked(True)
        self.blockSignals(False)
        if emit_signal:
            self._send_signal()


class PopupCheckListButton(QtWidgets.QPushButton):
    checked_items_changed = QtCore.Signal(list)

    def __init__(self, included_title=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.included_title = included_title
        self.menu = PopupCheckList(self)
        self.clicked.connect(self.popup)
        self.menu.checked_items_changed.connect(self._set_text)
        self.menu.checked_items_changed.connect(
            self.checked_items_changed.emit)

        self.set_items = self.menu.set_items
        self.set_checked_items = self.menu.set_checked_items
        self.checked_items_labels = self.menu.checked_items_labels
        self.all_checked = self.menu.all_checked
        self.check_all = self.menu.check_all
        self.uncheck_all = self.menu.uncheck_all
        self.invert = self.menu.invert

        self._set_text()

    def popup(self):
        position = self.mapToGlobal(self.rect().bottomLeft())
        self.menu.popup(position)

    def _set_text(self):
        labels = self.menu.checked_items_labels()
        text = get_multiple_selection_text(
            labels, len(self.menu.checkboxes), self.included_title)
        self.setText(text)

    def mousePressEvent(self, event):
        if event.type() == QtCore.QEvent.MouseButtonPress:
            if event.button() == Qt.MiddleButton:
                self.menu.uncheck_all()
            elif event.button() == Qt.RightButton:
                self.menu.invert()
        return super().mousePressEvent(event)
