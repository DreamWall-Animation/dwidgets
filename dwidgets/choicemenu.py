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


class ChoiceScrollMenu(QtWidgets.QMenu):
    """
    dialog = ChoiceScrollMenu(choices, parent=self)
    if not dialog.exec_(QtGui.QCursor().pos()):
        return
    choice = dialog.choice
    """
    def __init__(self, choices, labels=None, parent=None):
        super().__init__(parent)

        self.choices = choices
        self.labels = labels or choices
        self.choice = None

        self.search_edit = LineEdit()
        self.search_edit.arrow_pressed.connect(self.arrow_clicked)
        self.search_edit.textChanged.connect(self.filter_choices)

        self.items_list = ListWidget()
        self.items_list.itemClicked.connect(self.item_clicked)
        self.items_list.return_pressed.connect(self.handle_return)

        self.setMinimumWidth(200)
        self.setMinimumHeight(400)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(1, 1, 1, 1)
        layout.setSpacing(1)
        layout.addWidget(self.search_edit)
        layout.addWidget(self.items_list)

        self.filter_choices()

    def showEvent(self, event):
        self.search_edit.setFocus()
        return super().showEvent(event)

    def filter_choices(self):
        search_text = self.search_edit.text().lower()
        self.items_list.clear()
        for choice, label in zip(self.choices, self.labels):
            if search_text not in choice and search_text not in label.lower():
                continue
            item = QtWidgets.QListWidgetItem(label)
            item.setData(Qt.UserRole, choice)
            self.items_list.addItem(item)

    def item_clicked(self, item):
        self.choice = item.data(Qt.UserRole)
        self.close()

    def handle_return(self):
        current_row = self.items_list.currentRow() or 0
        self.item_clicked(self.items_list.item(current_row))

    def arrow_clicked(self):
        self.items_list.setFocus()
        if not self.items_list.currentRow():
            self.items_list.setCurrentRow(0)
