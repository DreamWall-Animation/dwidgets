
from functools import partial, lru_cache
from PySide2 import QtWidgets, QtCore, QtGui
from dwidgets.charts.settings import (
    DephSettings, MAXIMUM_ROW_HEIGHT, MINIUM_ROW_HEIGHT,
    FORMATTERS)


class WidgetToggler(QtWidgets.QPushButton):
    def __init__(self, label, widget, parent=None):
        super(WidgetToggler, self).__init__(parent)
        self.setText(' v ' + label)
        self.widget = widget
        self.setCheckable(True)
        self.setChecked(True)
        self.toggled.connect(self._call_toggled)

    def _call_toggled(self, state):
        if state is True:
            self.widget.show()
            self.setText(self.text().replace('>', 'v'))
        else:
            self.widget.hide()
            self.setText(self.text().replace('v', '>'))


class SliderDelegate(QtWidgets.QItemDelegate):
    def __init__(self, model):
        super().__init__()
        self.model = model

    def createEditor(self, parent, _, index):
        value = self.model.data(index, QtCore.Qt.UserRole)
        slider = QtWidgets.QSlider(QtCore.Qt.Horizontal, parent=parent)
        slider.setMinimum(0)
        slider.setMaximum(100)
        slider.setValue(value)
        slider.valueChanged.connect(partial(self.set_value, index))
        return slider

    def set_value(self, index, value):
        self.model.setData(index, value, QtCore.Qt.UserRole)


class DephTableModel(QtCore.QAbstractTableModel):
    header_edited = QtCore.Signal()
    geometries_edited = QtCore.Signal()

    def __init__(self, deph_settings=None, parent=None):
        super().__init__(parent)
        self.deph_settings = deph_settings or DephSettings()

    def rowCount(self, *_):
        return len(self.deph_settings) - 1

    def columnCount(self, *_):
        return 4

    def flags(self, _):
        return (
            QtCore.Qt.ItemIsEnabled |
            QtCore.Qt.ItemIsSelectable |
            QtCore.Qt.ItemIsEditable)

    def setData(self, index, value, role):
        if role not in (QtCore.Qt.UserRole, QtCore.Qt.EditRole):
            return False
        key = ('header', 'width', 'spacing', 'fork_spacing')[index.column()]
        self.layoutAboutToBeChanged.emit()
        self.deph_settings[index.row() + 1, key] = value
        if index.column() == 0:
            self.header_edited.emit()
        elif index.column() >= 1:
            self.geometries_edited.emit()
        self.layoutChanged.emit()
        return True

    def headerData(self, section, orientation, role):
        if role != QtCore.Qt.DisplayRole:
            return
        if orientation == QtCore.Qt.Vertical:
            return str(section + 1)
        return ('Label', 'Width', 'Spacing', 'Fork Spacing')[section]

    def data(self, index, role):
        if not index.isValid():
            return
        if role == QtCore.Qt.TextAlignmentRole:
            return QtCore.Qt.AlignCenter
        roles = (QtCore.Qt.DisplayRole, QtCore.Qt.UserRole, QtCore.Qt.EditRole)
        if role in roles:
            if index.column() == 0:
                return self.deph_settings[index.row() + 1, 'header']
            if index.column() == 1:
                return self.deph_settings[index.row() + 1, 'width']
            if index.column() == 2:
                return self.deph_settings[index.row() + 1, 'spacing']
            if index.column() == 3:
                return self.deph_settings[index.row() + 1, 'fork_spacing']


class BranchSettingsEditor(QtWidgets.QWidget):
    settings_edited = QtCore.Signal()

    def __init__(self, model, branch_settings, parent=None):
        super().__init__(parent)
        self.model = model
        self.branch_settings = branch_settings
        self.list = QtWidgets.QListWidget()
        mode = QtWidgets.QAbstractItemView.ScrollPerPixel
        self.list.setVerticalScrollMode(mode)
        self.list.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.list)

    def set_model(self, model):
        self.model = model
        self.update_settings_branches()

    def update_settings_branches(self):
        self.list.clear()
        for branch in self.model.list_branches():
            widget = BranchSettingWidget(branch, self.branch_settings)
            widget.settings_edited.connect(self.settings_edited.emit)
            item = QtWidgets.QListWidgetItem()
            item.setSizeHint(widget.sizeHint())
            self.list.addItem(item)
            self.list.setItemWidget(item, widget)

    def update_settings_values(self):
        for r in range(self.list.count()):
            item = self.list.item(r)
            widget = self.list.itemWidget(item)
            widget.blockSignals(True)
            value = self.branch_settings[widget.branch, 'height']
            widget.height.setValue(value)
            value = self.branch_settings[widget.branch, 'top_padding']
            widget.top_padding.setValue(value)
            value = self.branch_settings[widget.branch, 'bottom_padding']
            widget.bottom_padding.setValue(value)
            widget.blockSignals(False)


class BranchSettingWidget(QtWidgets.QWidget):
    settings_edited = QtCore.Signal()

    def __init__(self, branch, settings, parent=None):
        super().__init__(parent)
        self.branch = branch
        self.settings = settings
        self.label = QtWidgets.QLabel(branch)
        font = QtGui.QFont()
        font.setBold(True)
        font.setPixelSize(13)
        self.label.setFont(font)

        self.height = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.height.setMinimum(MINIUM_ROW_HEIGHT)
        self.height.setMaximum(MAXIMUM_ROW_HEIGHT)
        self.height.setValue(settings[branch, 'height'])
        self.height.valueChanged.connect(self.value_changed)

        self.top_padding = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.top_padding.setMinimum(0)
        self.top_padding.setMaximum(MAXIMUM_ROW_HEIGHT / 3)
        self.top_padding.setValue(settings[branch, 'top_padding'])
        self.top_padding.valueChanged.connect(self.value_changed)

        self.bottom_padding = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.bottom_padding.setMinimum(0)
        self.bottom_padding.setMaximum(MAXIMUM_ROW_HEIGHT / 3)
        self.bottom_padding.setValue(settings[branch, 'bottom_padding'])
        self.bottom_padding.valueChanged.connect(self.value_changed)

        self.value_formatter = QtWidgets.QComboBox()
        self.value_formatter.addItems(FORMATTERS.keys())
        self.value_formatter.setCurrentText(settings[branch, 'formatter'])
        self.value_formatter.currentIndexChanged.connect(self.value_changed)

        self.value_suffix = QtWidgets.QLineEdit()
        self.value_suffix.setText(settings[branch, 'value_suffix'])
        self.value_suffix.textEdited.connect(self.value_changed)

        formatter = QtWidgets.QWidget()
        formatter_layout = QtWidgets.QHBoxLayout(formatter)
        formatter_layout.setContentsMargins(0, 0, 0, 0)
        formatter_layout.addWidget(self.value_formatter)
        formatter_layout.addWidget(QtWidgets.QLabel('suffix:'))
        formatter_layout.addWidget(self.value_suffix)

        form = QtWidgets.QFormLayout()
        form.addRow('Height', self.height)
        form.addRow('Top padding', self.top_padding)
        form.addRow('Bottom padding', self.bottom_padding)
        form.addRow('Bottom padding', self.bottom_padding)
        form.addRow('Value formatting', formatter)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.label)
        layout.addLayout(form)

    def value_changed(self, _):
        self.settings[self.branch, 'height'] = self.height.value()
        self.settings[self.branch, 'top_padding'] = self.top_padding.value()
        value = self.bottom_padding.value()
        self.settings[self.branch, 'bottom_padding'] = value
        value = self.value_formatter.currentText()
        self.settings[self.branch, 'formatter'] = value
        self.settings[self.branch, 'value_suffix'] = self.value_suffix.text()
        self.settings_edited.emit()


class ColorsSettingsEditor(QtWidgets.QWidget):
    def __init__(self, colors_settings=None, parent=None):
        super().__init__(parent)
        self.colors_settings = colors_settings
        self.tree = QtWidgets.QTreeWidget()
        self.tree.header().hide()
        self.tree.doubleClicked.connect(self.double_clicked)
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.tree)

    def double_clicked(self, index):
        item = self.tree.itemFromIndex(index)
        key, value, color = item.data(0, QtCore.Qt.UserRole)
        color = QtWidgets.QColorDialog.getColor(color, self, 'Get Color')
        if not color:
            return
        color = color.name()
        item.setIcon(0, get_square_icon(color))
        item.setData(0, QtCore.Qt.UserRole, (key, value, color))
        self.colors_settings[key, value] = color

    def fill(self):
        self.tree.clear()
        for key, colors in self.colors_settings.data.items():
            root = QtWidgets.QTreeWidgetItem()
            root.setFlags(QtCore.Qt.ItemIsEnabled)
            root.setText(0, key)
            self.tree.addTopLevelItem(root)
            for value, color in colors.items():
                root.setFlags(
                    QtCore.Qt.ItemIsEnabled |
                    QtCore.Qt.ItemIsSelectable)
                item = QtWidgets.QTreeWidgetItem()
                item.setData(0, QtCore.Qt.UserRole, (key, value, color))
                item.setIcon(0, get_square_icon(color))
                item.setText(0, str(value))
                root.addChild(item)
        self.tree.expandAll()


@lru_cache()
def get_square_icon(color):
    px = QtGui.QPixmap(QtCore.QSize(60, 60))
    px.fill(QtCore.Qt.transparent)
    painter = QtGui.QPainter(px)
    pen = QtGui.QPen()
    pen.setWidth(2)
    painter.setPen(pen)
    painter.setBrush(QtGui.QColor(color))
    painter.drawRect(0, 0, 60, 60)
    painter.end()
    return QtGui.QIcon(px)
