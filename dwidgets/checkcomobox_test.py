import sys
from os.path import dirname

from PySide2 import QtWidgets

sys.path.append(dirname(dirname(__file__)))
from dwidgets.checkcombobox import CheckComboBox  # noqa


class MyApp(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.resize(300, 150)

        mainLayout = QtWidgets.QVBoxLayout()

        self.combo = CheckComboBox()
        mainLayout.addWidget(self.combo)

        for i, item in enumerate(['abc', 'xyz', 'test', 'foo', 'bar']):
            self.combo.addItem(item)
            self.combo.setItemChecked(i, False)

        btn = QtWidgets.QPushButton('Print Values')
        btn.clicked.connect(self.get_values)
        mainLayout.addWidget(btn)

        self.setLayout(mainLayout)

    def get_values(self):
        for i in range(self.combo.count()):
            checked = 'checked' if self.combo.itemChecked(i) else 'NOT checked'
            print(f'Item #{i}: {checked}')


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)

    myApp = MyApp()
    myApp.show()

    app.exit(app.exec_())
