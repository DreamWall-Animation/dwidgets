from PySide2 import QtWidgets


class ScrollMessageBox(QtWidgets.QMessageBox):
    def __init__(self, text, title=None, parent=None, *args, **kwargs):
        super().__init__(parent=parent, *args, **kwargs)

        if title:
            self.setWindowTitle(title)

        self._text = text
        self.text_edit = QtWidgets.QTextEdit(text=text, readOnly=True)
        self.text = self.text_edit.toPlainText

        self.copy_button = QtWidgets.QPushButton('copy text')
        self.copy_button.clicked.connect(self.text_to_clipboard)

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


if __name__ == '__main__':
    import sys
    app = QtWidgets.QApplication(sys.argv)
    w = QtWidgets.QWidget()
    s = ScrollMessageBox(
        text='content' + '\n1\n2\n3' * 20, title='test', parent=w)
    b = QtWidgets.QPushButton('show', clicked=s.exec_)
    ly = QtWidgets.QVBoxLayout(w)
    ly.addWidget(b)
    w.show()
    app.exit(app.exec_())
