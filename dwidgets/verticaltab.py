
from PySide2 import QtWidgets, QtGui, QtCore


GROUP_BOX_STYLE = """QGroupBox {
padding : 3px 3px 3px 3px;
border : 1px solid gray;
border-radius: 2px;
}"""


class VerticalTabWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tab_button_group = QtWidgets.QButtonGroup()
        self.tab_button_group.setExclusive(True)
        self.tab_button_group.buttonReleased.connect(self._update)

        self.buttons = []
        self.widgets = []

        right_group = QtWidgets.QGroupBox()
        right_group.setStyleSheet(GROUP_BOX_STYLE)
        self.widgets_layout = QtWidgets.QVBoxLayout(right_group)
        self.widgets_layout.setContentsMargins(0, 0, 0, 0)
        self.buttons_layout = QtWidgets.QVBoxLayout()
        self.buttons_layout.setContentsMargins(0, 0, 0, 0)
        self.buttons_layout.setSpacing(0)
        self.buttons_layout.addStretch(1)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(self.buttons_layout)
        layout.setSpacing(0)
        layout.addWidget(right_group)

    def current_widget(self):
        if not self.tab_button_group.checkedId():
            return
        return self.widgets[self.tab_button_group.checkedId()]

    def current_index(self):
        return self.tab_button_group.checkedId()

    def add_tab(self, widget, name):
        button = QtWidgets.QPushButton(f'{name} ')
        button.setCheckable(True)
        button.setFlat(True)
        button.setStyleSheet("text-align:right;")
        self.buttons.append(button)
        self.widgets.append(widget)
        self.widgets_layout.addWidget(widget)
        index = self.buttons_layout.count() - 1
        self.buttons_layout.insertWidget(index, button)
        id_ = len(self.tab_button_group.buttons())
        self.tab_button_group.addButton(button, id_)
        if id_ == 0:
            self.buttons[id_].setChecked(True)

    def add_separator(self):
        self.buttons_layout.insertSpacing(self.buttons_layout.count() - 1, 4)

    def add_section(self, name):
        self.add_separator()
        label = QtWidgets.QLabel(f'{name} ')
        label.setAlignment(QtCore.Qt.AlignRight)
        font = QtGui.QFont()
        font.setBold(True)
        label.setFont(font)
        self.buttons_layout.insertWidget(self.buttons_layout.count() - 1, label)

    def _update(self, *_):
        for i, widget in enumerate(self.widgets):
            widget.setVisible(self.current_index() == i)

    def showEvent(self, event):
        self._update()
        super().showEvent(event)


if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    tab = VerticalTabWidget()
    tab.add_tab(QtWidgets.QTableWidget(), 'test')
    tab.add_tab(QtWidgets.QCalendarWidget(), 'calendar')
    tab.show()
    app.exec_()
