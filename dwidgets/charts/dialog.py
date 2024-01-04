
from PySide2 import QtWidgets


class ChartDetails(QtWidgets.QDialog):
    def __init__(self, output, key, entries, parent=None):
        super().__init__(parent)
        self.output = output
        self.key = key
        self.entries = entries
        self.label = QtWidgets.QLabel(
            '.'.join(str(p.value) for p in output.parents() if p.value))
        self.label2 = QtWidgets.QLabel(output.branch())
        value = sum(e.weight for e in entries)
        self.label3 = QtWidgets.QLabel(f'{key}: {value}')
        self.table = QtWidgets.QTableWidget()
        columns = sorted({k for e in entries for k in e.data.keys()})
        self.table.setColumnCount(len(columns))
        self.table.setRowCount(len(entries))
        self.table.setHorizontalHeaderLabels(columns)
        for i, entry in enumerate(entries):
            for key, value in entry.data.items():
                item = QtWidgets.QTableWidgetItem()
                item.setText(str(value))
                self.table.setItem(i, columns.index(key), item)

        form = QtWidgets.QFormLayout()
        form.addRow('Path: ', self.label)
        form.addRow('Branch: ', self.label2)
        form.addRow('Total: ', self.label3)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self.table)
