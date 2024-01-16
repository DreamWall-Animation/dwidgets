
from PySide2 import QtWidgets, QtCore, QtGui
from dwidgets.charts.settings import FORMATTERS
from dwidgets.charts.sorting import sort_elements


class ChartDetails(QtWidgets.QDialog):
    def __init__(self, context, output, key, entries, parent=None):
        super().__init__(parent)
        self.setWindowTitle(
            f'Chart Detail: {context.translation_settings["key", key]}')
        self.output = output
        self.context = context
        self.key = key
        self.entries = entries
        self.label = QtWidgets.QLabel(
            '.'.join(str(p.value) for p in output.parents() if p.value))
        self.label2 = QtWidgets.QLabel(output.branch())
        value = sum(e.weight for e in entries)
        txt = (
            f'{context.translation_settings["key", key]} '
            f'{context.translation_settings["value", value]}')
        self.label3 = QtWidgets.QLabel(txt)
        self.table = QtWidgets.QTableWidget()
        self.table.setSortingEnabled(True)
        self.filter_hidden = QtWidgets.QCheckBox('filter hidden keywords')
        self.filter_hidden.setChecked(True)
        self.filter_hidden.released.connect(self.fill)

        form = QtWidgets.QFormLayout()
        form.addRow('Path: ', self.label)
        form.addRow('Branch: ', self.label2)
        form.addRow('Total: ', self.label3)
        form.addWidget(self.filter_hidden)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self.table)
        self.fill()

    def sizeHint(self):
        return QtCore.QSize(800, 500)

    def fill(self):
        columns = sorted({
            k for e in self.entries for k in e.data.keys() if
            not self.filter_hidden.isChecked() or
            k not in self.context.get_setting('hidden_keywords')})
        self.table.setColumnCount(len(columns))
        self.table.setRowCount(len(self.entries))
        labels = [self.context.translation_settings['key', c] for c in columns]
        self.table.setHorizontalHeaderLabels(labels)

        for i, entry in enumerate(self.entries):
            for key, value in entry.data.items():
                if key not in columns:
                    continue
                text = self.context.translation_settings['value', str(value)]
                item = QtWidgets.QTableWidgetItem()
                item.setText(text)
                self.table.setItem(i, columns.index(key), item)


class ChartDetailsTotal(QtWidgets.QDialog):
    def __init__(self, context, output, maximum, total, entries, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Output total details')
        self.context = context
        self.output = output
        self.entries = entries
        self.table = QtWidgets.QTableWidget()

        schema = context.sorting_settings['value', output.key]
        formatter, suffix = self.get_formatter_and_suffix(output.branch())
        keys = sort_elements(schema, list(output.content.keys()))
        self.table.setColumnCount(3)
        self.table.setRowCount(len(keys))
        self.table.setHorizontalHeaderLabels(
            ('Value', 'Entries sum', 'Entries count'))
        self.table.setSortingEnabled(True)
        self.table.setSelectionBehavior(self.table.SelectRows)
        self.table.setShowGrid(False)
        self.table.doubleClicked.connect(self.table_double_clicked)
        output_total = sum(
            entries[i].weight
            for key in keys for i in output.content[key])

        flags = QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable
        for i, key in enumerate(keys):
            color = context.colors_settings['value', str(key)]
            color = QtGui.QColor(color)
            text = context.translation_settings['value', key]
            item = QtWidgets.QTableWidgetItem(text)
            item.setData(QtCore.Qt.UserRole, key)
            item.setData(QtCore.Qt.BackgroundColorRole, color)
            item.setFlags(flags)
            self.table.setItem(i, 0, item)
            value = sum(entries[i].weight for i in output.content[key])
            value = formatter(
                value,
                suffix,
                output_total,
                maximum,
                total)
            item = QtWidgets.QTableWidgetItem(value)
            item.setData(QtCore.Qt.BackgroundColorRole, color)
            item.setFlags(flags)
            item.setData(QtCore.Qt.TextAlignmentRole, QtCore.Qt.AlignCenter)
            item.setData(QtCore.Qt.UserRole, key)
            self.table.setItem(i, 1, item)
            item = QtWidgets.QTableWidgetItem(str(len(output.content[key])))
            item.setData(QtCore.Qt.BackgroundColorRole, color)
            item.setFlags(flags)
            item.setData(QtCore.Qt.TextAlignmentRole, QtCore.Qt.AlignCenter)
            item.setData(QtCore.Qt.UserRole, key)
            self.table.setItem(i, 2, item)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.table)

    def get_formatter_and_suffix(self, branch):
        formatter = self.context.branch_settings[branch, 'formatter']
        formatter = FORMATTERS[formatter]
        if formatter is None:
            formatter = self.context.get_setting('default_formatter')
            suffix = self.context.get_setting('default_value_suffix')
            return FORMATTERS[formatter], suffix
        return formatter, self.context.branch_settings[branch, 'value_suffix']

    def table_double_clicked(self, index):
        row, col = index.row(), index.column()
        key = self.table.item(row, col).data(QtCore.Qt.UserRole)
        ChartDetails(
            self.context,
            self.output,
            key,
            [self.entries[i] for i in self.output.content[key]],
            parent=self.parent()).exec_()
