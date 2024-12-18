from functools import partial
from PySide2 import QtWidgets


class ScrollMessageBox(QtWidgets.QMessageBox):
    def __init__(
            self, text, title=None, parent=None, buttons_and_roles=None,
            *args, **kwargs):
        super().__init__(parent=parent, *args, **kwargs)
        self.clicked_role = None

        if title:
            self.setWindowTitle(title)

        self._text = text
        self.text_edit = QtWidgets.QTextEdit(text=text, readOnly=True)
        self.text = self.text_edit.toPlainText

        self.copy_button = QtWidgets.QPushButton('copy text')
        self.copy_button.clicked.connect(self.text_to_clipboard)

        if buttons_and_roles:
            for label, role in buttons_and_roles:
                button = self.addButton(label, role)
                button.clicked.connect(partial(self.set_role, role))
        else:
            self.setButtonText(1, 'Close')

        cols = self.layout().columnCount()
        self.layout().addWidget(self.text_edit, 0, 0, 1, cols)
        self.layout().addWidget(self.copy_button, 1, 0, 1, cols)

        if 'minimumWidth' not in kwargs:
            self.text_edit.setMinimumWidth(400)
        if 'minimumHeight' not in kwargs:
            self.text_edit.setMinimumHeight(400)

    def text_to_clipboard(self):
        clip = QtWidgets.QApplication.clipboard()
        clip.setText(self._text)

    def set_role(self, role):
        self.clicked_role = role


if __name__ == '__main__':
    import sys

    def exec_box():
        buttons = (
            ('Yes', QtWidgets.QMessageBox.YesRole),
            ('No', QtWidgets.QMessageBox.NoRole))
        s = ScrollMessageBox(
            text='content' + '\n1\n2\n3' * 20, title='test', parent=w,
            buttons_and_roles=buttons)
        print(s.exec_())

    app = QtWidgets.QApplication(sys.argv)
    w = QtWidgets.QWidget()
    b = QtWidgets.QPushButton('show', clicked=exec_box)
    ly = QtWidgets.QVBoxLayout(w)
    ly.addWidget(b)
    w.show()
    app.exit(app.exec_())
