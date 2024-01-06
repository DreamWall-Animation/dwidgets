
from functools import partial, lru_cache
from PySide2 import QtWidgets, QtCore, QtGui
from dwidgets.popupchecklist2 import PopupCheckListButton2
from dwidgets.charts.model import ChartFilter
from dwidgets.charts.settings import (
    DephSettings, get_setting, set_setting,
    MAXIMUM_ROW_HEIGHT, MINIUM_ROW_HEIGHT, FORMATTERS)


class WidgetToggler(QtWidgets.QPushButton):
    def __init__(self, label, widget, parent=None):
        super(WidgetToggler, self).__init__(parent)
        self.setText(' ▼ ' + label)
        self.setStyleSheet('Text-align:left; background-color:rgba(0, 0, 0, 30)')
        self.widget = widget
        self.setCheckable(True)
        self.setChecked(True)
        self.toggled.connect(self._call_toggled)

    def _call_toggled(self, state):
        if state is True:
            self.widget.show()
            self.setText(self.text().replace('►', '▼'))
        else:
            self.widget.hide()
            self.setText(self.text().replace('▼', '►'))


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
    geometries_edited = QtCore.Signal()

    def __init__(self, deph_settings=None, parent=None):
        super().__init__(parent)
        self.deph_settings = deph_settings or DephSettings()

    def rowCount(self, *_):
        return len(self.deph_settings) - 1

    def columnCount(self, *_):
        return 2

    def flags(self, _):
        return (
            QtCore.Qt.ItemIsEnabled |
            QtCore.Qt.ItemIsSelectable |
            QtCore.Qt.ItemIsEditable)

    def setData(self, index, value, role):
        if role not in (QtCore.Qt.UserRole, QtCore.Qt.EditRole):
            return False
        key = ('spacing', 'fork_spacing')[index.column()]
        self.layoutAboutToBeChanged.emit()
        self.deph_settings[index.row() + 1, key] = value
        self.geometries_edited.emit()
        self.layoutChanged.emit()
        return True

    def headerData(self, section, orientation, role):
        if role != QtCore.Qt.DisplayRole:
            return
        if orientation == QtCore.Qt.Vertical:
            return str(section + 1)
        return ('Spacing', 'Fork Spacing')[section]

    def data(self, index, role):
        if not index.isValid():
            return
        if role == QtCore.Qt.TextAlignmentRole:
            return QtCore.Qt.AlignCenter
        roles = (QtCore.Qt.DisplayRole, QtCore.Qt.UserRole, QtCore.Qt.EditRole)
        if role in roles:
            if index.column() == 0:
                return self.deph_settings[index.row() + 1, 'spacing']
            if index.column() == 1:
                return self.deph_settings[index.row() + 1, 'fork_spacing']


class BranchSettingDialog(QtWidgets.QDialog):
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


TEMPLATE = """
<div style="font-size: 12px;">{key} <b>{operator}</b> {values}</div>
"""


class FiltersWidget(QtWidgets.QWidget):
    filters_edited = QtCore.Signal()

    def __init__(self, model=None, parent=None):
        super().__init__(parent)
        self.model = model
        self.list = FiltersListWidget(model)
        self.add_filter = QtWidgets.QPushButton('Add filter')
        self.add_filter.released.connect(self.call_add_filter)
        self.clear = QtWidgets.QPushButton('Clear')
        self.clear.released.connect(self.call_clear)

        btn = QtWidgets.QHBoxLayout()
        btn.setContentsMargins(0, 0, 0, 0)
        btn.addStretch()
        btn.addWidget(self.add_filter)
        btn.addWidget(self.clear)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.list)
        layout.addLayout(btn)

    def call_clear(self):
        self.model.clear_filters()
        self.filters_edited.emit()
        self.list.repaint()

    def call_add_filter(self):
        diag = AddFilterDialog(self.model, self)
        if diag.exec_():
            self.model.add_filter(diag.filter())
            self.filters_edited.emit()
            self.list.repaint()

    def set_model(self, model):
        self.model = model
        self.list.model = model
        self.list.repaint()


class AddFilterDialog(QtWidgets.QDialog):
    def __init__(self, model, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Add Filter')
        self.model = model
        self.keys = QtWidgets.QComboBox()
        self.keys.addItems(model.list_common_keys())
        self.keys.currentTextChanged.connect(self.fill_values)
        self.operators = QtWidgets.QComboBox()
        self.operators.addItems(['in', 'not in'])
        self.values = PopupCheckListButton2()

        add = QtWidgets.QPushButton('Add')
        add.released.connect(self.accept)

        hlayout = QtWidgets.QHBoxLayout()
        hlayout.setContentsMargins(0, 0, 0, 0)
        hlayout.addWidget(self.keys)
        hlayout.addWidget(self.operators)
        hlayout.addWidget(self.values)

        but_layout = QtWidgets.QHBoxLayout()
        but_layout.setContentsMargins(0, 0, 0, 0)
        but_layout.addStretch(1)
        but_layout.addWidget(add)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addLayout(hlayout)
        layout.addLayout(but_layout)

    def fill_values(self):
        values = self.model.values_for_key(self.keys.currentText())
        self.values.set_items([(str(v), v) for v in values])

    def filter(self):
        return ChartFilter(
            self.keys.currentText(),
            self.operators.currentText(),
            self.values.checked_data())


class FiltersListWidget(QtWidgets.QWidget):
    def __init__(self, model=None, parent=None):
        super().__init__(parent)
        self.model = model
        self.setMinimumHeight(30)

    def set_model(self, model):
        self.model = model
        self.repaint()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        top = 5
        rect = QtCore.QRect(
            0, 0, event.rect().width() - 1,
            event.rect().height() - 1)
        painter.drawRect(rect)
        alternate_row_color = QtGui.QColor('black')
        alternate_row_color.setAlpha(35)
        for i, filter in enumerate(self.model.filters):
            values = ', '.join(str(v) for v in filter.values[:5])
            if len(filter.values) > 5:
                values += f'... (and {len(filter.values)} more)'
            text = TEMPLATE.format(
                key=filter.key, operator=filter.operator, values=values)
            static_text = QtGui.QStaticText(text)
            static_text.setTextWidth(event.rect().width() - 10)
            if i % 2 != 0:
                rect = QtCore.QRect(
                    0, top - 2, event.rect().width(),
                    static_text.size().height() + 5)
                painter.setBrush(alternate_row_color)
                painter.setPen(QtCore.Qt.NoPen)
                painter.drawRect(rect)
                painter.setBrush(QtGui.QBrush())
                painter.setPen(QtGui.QPen())
            painter.drawStaticText(5, top, static_text)
            top += static_text.size().height() + 5
        self.setFixedHeight(max((30, top + 5)))
        painter.end()


class ChartSettings(QtWidgets.QWidget):
    geometries_edited = QtCore.Signal()
    setting_edited = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.display_output_type = QtWidgets.QCheckBox('Display output types')
        self.display_output_type.setChecked(get_setting('display_output_type'))
        mtd = partial(self.update_settings, True)
        self.display_output_type.released.connect(mtd)
        self.display_keys = QtWidgets.QCheckBox('Display key')
        self.display_keys.setChecked(get_setting('display_keys'))
        self.display_keys.released.connect(self.update_settings)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.display_output_type)
        layout.addWidget(self.display_keys)

    def update_settings(self, edit_geometries=False):
        value = self.display_output_type.isChecked()
        set_setting('display_output_type', value)
        set_setting('display_keys', self.display_keys.isChecked())
        if edit_geometries:
            self.geometries_edited.emit()
        else:
            self.setting_edited.emit()


class ErasePreset(QtWidgets.QDialog):
    def __init__(self, name, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Error')

        label = QtWidgets.QLabel(f'Preset named:"{name}" already exists')
        self.skip = QtWidgets.QRadioButton('Skip')
        self.skip.setChecked(True)
        self.erase = QtWidgets.QRadioButton('Erase')
        self.rename = QtWidgets.QRadioButton('Rename')
        self.group = QtWidgets.QButtonGroup()
        self.group.addButton(self.skip, 0)
        self.group.addButton(self.erase, 1)
        self.group.addButton(self.rename, 2)
        self.name = QtWidgets.QLineEdit(name)

        self.continue_ = QtWidgets.QPushButton('Continue')
        self.continue_.released.connect(self.accept)
        self.cancel = QtWidgets.QPushButton('Cancel')
        self.cancel.released.connect(self.reject)

        but_layout = QtWidgets.QHBoxLayout()
        but_layout.addStretch()
        but_layout.addWidget(self.continue_)
        but_layout.addWidget(self.cancel)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(label)
        layout.addWidget(self.skip)
        layout.addWidget(self.erase)
        layout.addWidget(self.rename)
        layout.addWidget(self.name)
        layout.addLayout(but_layout)


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
