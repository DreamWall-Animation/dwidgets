from functools import partial
from PySide2 import QtWidgets


class ChoiceMenu(QtWidgets.QMenu):
    """
    dialog = ChoiceMenu(choices, parent=self)
    if not dialog.exec_(QtGui.QCursor().pos()):
        return
    choice = dialog.choice
    """
    def __init__(self, choices, parent=None):
        super().__init__(parent)
        self.choice = None

        for label in choices:
            self.addAction(label, partial(self.action_clicked, label))

    def action_clicked(self, choice):
        self.choice = choice


class ChoiceScrollMenu(QtWidgets.QMenu):
    """
    dialog = ChoiceScrollMenu(choices, parent=self)
    if not dialog.exec_(QtGui.QCursor().pos()):
        return
    choice = dialog.choice
    """
    def __init__(self, choices, parent=None):
        super().__init__(parent)

        self.choices = choices
        self.choice = None

        self.search_edit = QtWidgets.QLineEdit()
        self.search_edit.textChanged.connect(self.filter_choices)

        self.items_list = QtWidgets.QListWidget()
        self.items_list.itemClicked.connect(self.item_clicked)

        self.setMinimumWidth(200)
        self.setMinimumHeight(400)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(1, 1, 1, 1)
        layout.setSpacing(1)
        layout.addWidget(self.search_edit)
        layout.addWidget(self.items_list)

        self.filter_choices()

    def filter_choices(self):
        search_text = self.search_edit.text().lower()
        choices = [c for c in self.choices if search_text in c.lower()]
        self.items_list.clear()
        for label in choices:
            self.items_list.addItem(label)

    def item_clicked(self, item):
        self.choice = item.text()
        self.close()
