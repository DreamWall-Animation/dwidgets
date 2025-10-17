from functools import partial
from PySide2 import QtWidgets, QtCore
from PySide2.QtCore import Qt


class ChoiceMenu(QtWidgets.QMenu):
    """
    dialog = ChoiceMenu(choices, parent=self)
    if not dialog.exec_(QtGui.QCursor().pos()):
        return
    choice = dialog.choice
    """
    def __init__(self, choices, icons=None, labels=None, parent=None):
        super().__init__(parent)
        self.choice = None
        labels = labels or choices
        icons = icons or ([None] * len(choices))
        for label, choice, icon in zip(labels, choices, icons):
            action = QtWidgets.QAction(self)
            action.setText(label)
            action.triggered.connect(partial(self.action_clicked, choice))
            if icon:
                action.setIcon(icon)
            self.addAction(action)

    def action_clicked(self, choice):
        self.choice = choice


class LineEdit(QtWidgets.QLineEdit):
    arrow_pressed = QtCore.Signal(Qt.Key)

    def __init__(self, parent=None):
        super().__init__(parent)

    def keyPressEvent(self, event):
        key = event.key()
        if key in (Qt.Key_Down, Qt.Key_Up):
            self.arrow_pressed.emit(key)
        return super().keyPressEvent(event)


class ListWidget(QtWidgets.QListWidget):
    return_pressed = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Return:
            self.return_pressed.emit()
        return super().keyPressEvent(event)


class ChoiceScrollMixin:
    def setup_ui(self, choices, labels=None, title=None, multi=False):

        self.setMinimumWidth(200)
        self.setMinimumHeight(400)

        self.multi = multi
        self.choices = choices
        self.labels = labels or choices
        self.choice = None

        self.search_edit = LineEdit()
        self.search_edit.arrow_pressed.connect(self.arrow_clicked)
        self.search_edit.textChanged.connect(self.filter_choices)

        self.items_list = ListWidget()
        if self.multi:
            self.items_list.setSelectionMode(
                QtWidgets.QAbstractItemView.ExtendedSelection)
        self.items_list.itemClicked.connect(self.item_clicked)
        self.items_list.return_pressed.connect(self.handle_return)

        self.main_layout = QtWidgets.QVBoxLayout(self)
        self.main_layout.setContentsMargins(1, 1, 1, 1)
        self.main_layout.setSpacing(1)
        if title:
            self.main_layout.addWidget(QtWidgets.QLabel(title))
        self.main_layout.addWidget(self.search_edit)
        self.main_layout.addWidget(self.items_list)

        self.filter_choices()

    def showEvent(self, event):
        self.search_edit.setFocus()
        return super().showEvent(event)

    def filter_choices(self):
        search_text = self.search_edit.text().lower()
        self.items_list.clear()
        for choice, label in zip(self.choices, self.labels):
            try:
                text_in_choice = search_text in choice
            except TypeError:
                text_in_choice = False
            if not text_in_choice and search_text not in label.lower():
                continue
            item = QtWidgets.QListWidgetItem(label)
            item.setData(Qt.UserRole, choice)
            self.items_list.addItem(item)

    def item_clicked(self, item):
        if not self.multi:
            self.choice = item.data(Qt.UserRole)
            self.close()

    def handle_return(self):
        current_row = self.items_list.currentRow() or 0
        self.item_clicked(self.items_list.item(current_row))

    def arrow_clicked(self):
        self.items_list.setFocus()
        if not self.items_list.currentRow():
            self.items_list.setCurrentRow(0)


class ChoiceScrollMenu(QtWidgets.QMenu, ChoiceScrollMixin):
    """
    dialog = ChoiceScrollMenu(choices, parent=self)
    if not dialog.exec_(QtGui.QCursor().pos()):
        return
    choice = dialog.choice
    """
    def __init__(
            self, choices, labels=None, title=None, multi=False, parent=None):
        super().__init__(parent=parent)
        self.setup_ui(choices=choices, labels=labels, title=title, multi=multi)


class ChoiceScrollDialog(QtWidgets.QDialog, ChoiceScrollMixin):
    """
    dialog = ChoiceScrollDialog(choices, parent=self)
    if not dialog.exec_(QtGui.QCursor().pos()):
        return
    choice = dialog.choice
    """
    def __init__(
            self, choices, labels=None, title=None, multi=False, parent=None):
        super().__init__(parent=parent)
        self.setup_ui(choices=choices, labels=labels, title=title, multi=multi)

        btn = QtWidgets.QPushButton('Ok', clicked=self.accept)
        ok_layout = QtWidgets.QHBoxLayout()
        ok_layout.addStretch()
        ok_layout.addWidget(btn)
        self.main_layout.addLayout(ok_layout)

    def accept(self):
        self.choice = self.choices = [
            item.data(Qt.UserRole)
            for item in self.items_list.selectedItems()]
        return super().accept()


if __name__ == '__main__':
    dialog = ChoiceScrollDialog(['a', 'b', 'c'], multi=True)
    dialog.exec_()
    choice = dialog.choice
