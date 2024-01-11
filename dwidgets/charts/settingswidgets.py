
from functools import partial, lru_cache
from PySide2 import QtWidgets, QtCore, QtGui
from dwidgets.popupchecklist2 import PopupCheckListButton2
from dwidgets.charts.model import ChartFilter
from dwidgets.charts.settings import (
    MAXIMUM_ROW_HEIGHT, MINIUM_ROW_HEIGHT, FORMATTERS)


class WidgetToggler(QtWidgets.QPushButton):
    def __init__(self, label, widget, expanded=True, parent=None):
        super(WidgetToggler, self).__init__(parent)
        self.setText((' ▼ ' if expanded else ' ► ') + label)
        self.setStyleSheet('Text-align:left; background-color:rgb(150, 150, 150)')
        self.widget = widget
        self.setCheckable(True)
        self.setChecked(expanded)
        if not expanded:
            self.widget.setVisible(False)
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

    def __init__(self, context=None, parent=None):
        super().__init__(parent)
        self.context = context

    def rowCount(self, *_):
        return len(self.context.deph_settings) - 1

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
        self.context.deph_settings[index.row() + 1, key] = value
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
                return self.context.deph_settings[index.row() + 1, 'spacing']
            if index.column() == 1:
                return self.context.deph_settings[index.row() + 1, 'fork_spacing']


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

        self.visible = QtWidgets.QComboBox()
        self.visible.addItems(('Always', 'Hide on expanded', 'Never'))
        self.visible.setCurrentText(settings[branch, 'visibility'])
        self.visible.currentTextChanged.connect(self.value_changed)

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
        form.addRow('Visibility', self.visible)
        form.addRow('Height', self.height)
        form.addRow('Top padding', self.top_padding)
        form.addRow('Bottom padding', self.bottom_padding)
        form.addRow('Value formatting', formatter)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.label)
        layout.addLayout(form)

    def value_changed(self, *_):
        self.settings[self.branch, 'visibility'] = self.visible.currentText()
        self.settings[self.branch, 'height'] = self.height.value()
        self.settings[self.branch, 'top_padding'] = self.top_padding.value()
        value = self.bottom_padding.value()
        self.settings[self.branch, 'bottom_padding'] = value
        value = self.value_formatter.currentText()
        self.settings[self.branch, 'formatter'] = value
        self.settings[self.branch, 'value_suffix'] = self.value_suffix.text()
        self.settings_edited.emit()


class ColorsSettingsEditor(QtWidgets.QWidget):
    def __init__(self, context=None, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(250)
        self.context = context
        self.tree = QtWidgets.QTreeWidget()
        self.tree.header().hide()
        self.tree.doubleClicked.connect(self.double_clicked)
        layout = QtWidgets.QHBoxLayout(self)
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
        self.context.colors_settings[key, value] = color

    def fill(self):
        self.tree.clear()
        for key, colors in self.context.colors_settings.data.items():
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

    def __init__(self, model=None, context=None, parent=None):
        super().__init__(parent)
        self.model = model
        self.context = context
        self.list = FiltersListWidget(model)
        self.list.remove_filter.connect(self.call_remove_filter)
        self.list.edit_filter.connect(self.call_edit_filter)
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
        diag = AddEditFilterDialog(self.model, self.context, parent=self)
        diag.show()
        diag.filter_added.connect(self.do_add_filter)
        point = self.list.mapToGlobal(self.list.rect().bottomLeft())
        point.setY(point.y() + 2)
        diag.move(point)

    def call_edit_filter(self, index):
        diag = AddEditFilterDialog(
            self.model, self.context,
            filter=self.model.filters[index], parent=self)
        diag.show()
        diag.filter_added.connect(partial(self.do_edit_filter, index))
        point = self.list.mapToGlobal(self.list.rect().bottomLeft())
        point.setY(point.y() + 2)
        diag.move(point)

    def do_add_filter(self, filter):
        self.model.add_filter(filter)
        self.filters_edited.emit()
        self.list.repaint()

    def do_edit_filter(self, index, filter):
        self.model.replace_filter(index, filter)
        self.filters_edited.emit()
        self.list.repaint()

    def set_model(self, model):
        self.model = model
        self.list.model = model
        self.list.repaint()

    def call_remove_filter(self, index):
        self.model.remove_filter(index)
        self.filters_edited.emit()
        self.list.repaint()


class AddEditFilterDialog(QtWidgets.QWidget):
    filter_added = QtCore.Signal(object)

    def __init__(self, model, context, filter=None, parent=None):
        super().__init__(parent)
        self.setWindowFlags(QtCore.Qt.Popup | QtCore.Qt.FramelessWindowHint)
        self.model = model
        self.context = context
        self.keys = QtWidgets.QComboBox()
        items = [
            i for i in model.list_common_keys()
            if i not in self.context.get_setting('hidden_keywords')]
        self.keys.addItems(items)
        self.keys.currentTextChanged.connect(self.fill_values)
        self.operators = QtWidgets.QComboBox()
        self.operators.addItems(['in', 'not in'])
        self.values = PopupCheckListButton2()
        add = QtWidgets.QPushButton('Add' if filter is None else 'Edit')
        add.released.connect(self.accept)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.keys)
        layout.addWidget(self.operators)
        layout.addWidget(self.values)
        layout.addWidget(add)

        if filter is not None:
            self.set_filter(filter)

    def set_filter(self, filter):
        self.keys.setCurrentText(filter.key)
        self.operators.setCurrentText(filter.operator)
        self.fill_values()
        self.values.set_checked_data(filter.values)

    def accept(self):
        self.filter_added.emit(self.filter())
        self.close()

    def fill_values(self):
        values = self.model.values_for_key(self.keys.currentText())
        self.values.set_items([(str(v), v) for v in values])

    def filter(self):
        return ChartFilter(
            self.keys.currentText(),
            self.operators.currentText(),
            self.values.checked_data())


class FiltersListWidget(QtWidgets.QWidget):
    remove_filter = QtCore.Signal(int)
    edit_filter = QtCore.Signal(int)

    def __init__(self, model=None, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.model = model
        self.setMinimumHeight(30)

    def set_model(self, model):
        self.model = model
        self.repaint()

    def mouseMoveEvent(self, _):
        self.repaint()

    def mouseReleaseEvent(self, _):
        cursor = self.mapFromGlobal(QtGui.QCursor.pos())
        top = 5
        for i, filter in enumerate(self.model.filters):
            values = ', '.join(str(v) for v in filter.values[:5])
            if len(filter.values) > 5:
                values += f'... (and {len(filter.values)} more)'
            text = TEMPLATE.format(
                key=filter.key, operator=filter.operator, values=values)
            static_text = QtGui.QStaticText(text)
            static_text.setTextWidth(self.rect().width() - 10)
            rect = QtCore.QRect(
                0, top - 2, self.rect().width(),
                static_text.size().height() + 5)
            top += static_text.size().height() + 5
            if rect.contains(cursor):
                close_rect = QtCore.QRect(
                    rect.right() - 16, rect.top(), 15, 15)
                if close_rect.contains(cursor):
                    return self.remove_filter.emit(i)
                return self.edit_filter.emit(i)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        top = 5
        rect = QtCore.QRect(
            0, 0, event.rect().width() - 1,
            event.rect().height() - 1)
        painter.drawRect(rect)
        alternate_row_color = QtGui.QColor('black')
        alternate_row_color.setAlpha(35)
        cursor = self.mapFromGlobal(QtGui.QCursor.pos())
        option = QtGui.QTextOption()
        option.setAlignment(QtCore.Qt.AlignCenter)
        for i, filter in enumerate(self.model.filters):
            values = ', '.join(str(v) for v in filter.values[:5])
            if len(filter.values) > 5:
                values += f'... (and {len(filter.values)} more)'
            text = TEMPLATE.format(
                key=filter.key, operator=filter.operator, values=values)
            static_text = QtGui.QStaticText(text)
            static_text.setTextWidth(event.rect().width() - 10)
            rect = QtCore.QRect(
                0, top - 2, event.rect().width(),
                static_text.size().height() + 5)
            if i % 2 != 0:
                painter.setBrush(alternate_row_color)
                painter.setPen(QtCore.Qt.NoPen)
                painter.drawRect(rect)
                painter.setBrush(QtGui.QBrush())
                painter.setPen(QtGui.QPen())
            painter.drawStaticText(5, top, static_text)
            top += static_text.size().height() + 5
            if rect.contains(cursor):
                close_rect = QtCore.QRect(
                    rect.right() - 16, rect.top(), 15, 15)
                painter.drawRect(close_rect)
                painter.drawText(close_rect, '✘', option)
        self.setFixedHeight(max((30, top + 5)))
        painter.end()


class ChartSettings(QtWidgets.QWidget):
    geometries_edited = QtCore.Signal()
    setting_edited = QtCore.Signal()

    def __init__(self, context, parent=None):
        super().__init__(parent)
        self.context = context

        self.display_output_type = QtWidgets.QCheckBox('Display output types')
        value = self.context.get_setting('display_output_type')
        self.display_output_type.setChecked(value)
        mtd = partial(self.update_settings, True)
        self.display_output_type.released.connect(mtd)
        self.display_keys = QtWidgets.QCheckBox('Display key')
        self.display_keys.setChecked(self.context.get_setting('display_keys'))
        self.display_keys.released.connect(self.update_settings)

        self.default_formatter = QtWidgets.QComboBox()
        self.default_formatter.addItems(list(FORMATTERS)[1:])
        value = context.get_setting('default_formatter')
        self.default_formatter.setCurrentText(value)
        self.default_formatter.currentIndexChanged.connect(
            self._update_settings)

        self.default_suffix = QtWidgets.QLineEdit()
        value = context.get_setting('default_value_suffix')
        self.default_suffix.setText(value)
        self.default_suffix.textEdited.connect(self._update_settings)

        hlayout = QtWidgets.QHBoxLayout()
        hlayout.setContentsMargins(0, 0, 0, 0)
        hlayout.addWidget(QtWidgets.QLabel('Global value formatter: '))
        hlayout.addWidget(self.default_formatter)
        hlayout.addWidget(self.default_suffix)
        hlayout.addStretch()

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.display_output_type)
        layout.addWidget(self.display_keys)
        layout.addLayout(hlayout)

    def update_settings(self, edit_geometries=False):
        value = self.display_output_type.isChecked()
        self.context.set_setting('display_output_type', value)
        self.context.set_setting('display_keys', self.display_keys.isChecked())
        value = self.default_formatter.currentText()
        self.context.set_setting('default_formatter', value)
        value = self.default_suffix.text()
        self.context.set_setting('default_value_suffix', value)
        if edit_geometries:
            self.geometries_edited.emit()
        else:
            self.setting_edited.emit()

    def _update_settings(self, *_):
        self.update_settings(False)


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


class DephSettingsEditor(QtWidgets.QWidget):
    def __init__(self, context, parent=None):
        super().__init__(parent=parent)

        self.context = context
        self.deph_settings_model = DephTableModel(self.context)
        self.geometries_edited = self.deph_settings_model.geometries_edited
        self.slider_delegate = SliderDelegate(self.deph_settings_model)

        self.deph_settings_table = QtWidgets.QTableView()
        self.deph_settings_table.setItemDelegateForColumn(
            0, self.slider_delegate)
        self.deph_settings_table.setItemDelegateForColumn(
            1, self.slider_delegate)
        self.deph_settings_table.setModel(self.deph_settings_model)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.deph_settings_table)


class DictionnariesEditor(QtWidgets.QWidget):
    translation_edited = QtCore.Signal()

    def __init__(self, model, context, parent=None):
        super().__init__(parent)
        self.key_dict = DictionnaryEditor(
            'key', context, completer=model.list_common_keys)
        self.key_dict.model.translation_edited.connect(
            self.translation_edited.emit)
        self.value_dict = DictionnaryEditor('value', context)
        self.value_dict.model.translation_edited.connect(
            self.translation_edited.emit)
        tab = QtWidgets.QTabWidget()
        tab.addTab(self.key_dict, 'Keywords')
        tab.addTab(self.value_dict, 'Values')

        layout = QtWidgets.QHBoxLayout(self)
        layout.addWidget(tab)

    def set_model(self, model):
        self.key_dict.completer = model.list_common_keys

    def update(self):
        self.key_dict.model.layoutChanged.emit()
        self.value_dict.model.layoutChanged.emit()


class DictionnaryEditor(QtWidgets.QWidget):
    translation_edited = QtCore.Signal()

    def __init__(self, key, context, completer=None, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(300)
        self.key = key
        self.completer = completer
        self.context = context
        self.model = DictionnaryTableModel(key, context)
        self.model.translation_edited.connect(self.translation_edited.emit)
        self.table = QtWidgets.QTableView()
        self.table.verticalHeader().hide()
        self.table.setAlternatingRowColors(True)
        mode = QtWidgets.QAbstractItemView.ExtendedSelection
        self.table.setSelectionMode(mode)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setModel(self.model)
        add = QtWidgets.QPushButton('Add')
        add.released.connect(self.call_add)
        remove = QtWidgets.QPushButton('Remove')
        remove.released.connect(self.call_remove)

        buttons = QtWidgets.QHBoxLayout()
        buttons.setContentsMargins(0, 0, 0, 0)
        buttons.addStretch()
        buttons.addWidget(add)
        buttons.addWidget(remove)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.table)
        layout.addLayout(buttons)

    def call_remove(self):
        indexes = self.table.selectionModel().selectedIndexes()
        rows = sorted({i.row() for i in indexes})
        self.model.deleted_rows(rows)

    def call_add(self):
        completion = self.completer() if self.completer else None
        dialog = AddTranslationDialog(completion, self)
        dialog.show()
        dialog.translation_add.connect(self.add_translation)
        point = self.table.mapToGlobal(self.table.rect().bottomLeft())
        point.setY(point.y() + 2)
        dialog.move(point)

    def add_translation(self, data, display):
        self.context.translation_settings[self.key, data] = display
        self.model.layoutChanged.emit()
        self.model.translation_edited.emit()


class AddTranslationDialog(QtWidgets.QWidget):
    translation_add = QtCore.Signal(str, str)

    def __init__(self, completion=None, parent=None):
        super().__init__(parent)
        self.setWindowFlags(QtCore.Qt.Popup | QtCore.Qt.FramelessWindowHint)
        self.data = QtWidgets.QLineEdit()
        if completion:
            self.data.setCompleter(QtWidgets.QCompleter(completion))
        self.display = QtWidgets.QLineEdit()
        self.data.returnPressed.connect(self.call_add)
        self.display.returnPressed.connect(self.call_add)
        add = QtWidgets.QPushButton('Add')
        add.released.connect(self.call_add)
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.data)
        layout.addWidget(self.display)
        layout.addWidget(add)

    def showEvent(self, event):
        super().showEvent(event)
        self.data.setFocus(QtCore.Qt.MouseFocusReason)

    def call_add(self):
        self.translation_add.emit(self.data.text(), self.display.text())
        self.close()


class DictionnaryTableModel(QtCore.QAbstractTableModel):
    translation_edited = QtCore.Signal()

    def __init__(self, key, context):
        super().__init__()
        self.key = key
        self.context = context

    def rowCount(self, *_):
        try:
            return len(self.context.translation_settings.data[self.key])
        except KeyError:  # No entry already recorded
            return 0

    def columnCount(self, *_):
        return 2

    def deleted_rows(self, rows):
        self.layoutAboutToBeChanged.emit()
        dict_keys = sorted(self.context.translation_settings.data[self.key].keys())
        dict_keys = [dict_keys[r] for r in rows]
        for dict_key in dict_keys:
            del self.context.translation_settings.data[self.key][dict_key]
        self.layoutChanged.emit()
        self.translation_edited.emit()

    def headerData(self, section, orientation, role):
        if role != QtCore.Qt.DisplayRole:
            return
        if orientation == QtCore.Qt.Horizontal:
            return ('Data', 'Display')[section]

    def flags(self, index):
        flags = QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable
        if index.column() == 0:
            return flags
        return flags | QtCore.Qt.ItemIsEditable

    def setData(self, index, value, role):
        if role != QtCore.Qt.EditRole:
            return False
        dict_keys = sorted(
            self.context.translation_settings.data[self.key].keys())
        dict_key = dict_keys[index.row()]
        self.context.translation_settings[self.key, dict_key] = value
        self.translation_edited.emit()
        return True

    def data(self, index, role):
        if role not in (QtCore.Qt.DisplayRole, QtCore.Qt.EditRole):
            return

        dict_keys = sorted(
            self.context.translation_settings.data[self.key].keys())
        dict_key = dict_keys[index.row()]
        if index.column() == 0:
            return dict_key
        return self.context.translation_settings[self.key, dict_key]


class SortingEditor(QtWidgets.QWidget):
    sorting_edited = QtCore.Signal()

    def __init__(self, key='value', context=None, completer=None, parent=None):
        super().__init__(parent)
        self.context = context
        self.setMinimumHeight(300)
        self.key = key
        self.completer = completer
        self.model = SortingTableModel(key, context)
        self.model.sorting_edited.connect(self.sorting_edited.emit)
        self.table = QtWidgets.QTableView()
        self.table.verticalHeader().hide()
        self.table.setAlternatingRowColors(True)
        mode = QtWidgets.QAbstractItemView.ExtendedSelection
        self.table.setSelectionMode(mode)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setModel(self.model)
        add = QtWidgets.QPushButton('Add')
        add.released.connect(self.call_add)
        remove = QtWidgets.QPushButton('Remove')
        remove.released.connect(self.call_remove)

        buttons = QtWidgets.QHBoxLayout()
        buttons.setContentsMargins(0, 0, 0, 0)
        buttons.addStretch()
        buttons.addWidget(add)
        buttons.addWidget(remove)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.table)
        layout.addLayout(buttons)

    def call_remove(self):
        indexes = self.table.selectionModel().selectedIndexes()
        rows = sorted({i.row() for i in indexes})
        self.model.deleted_rows(rows)

    def set_model(self, model):
        self.completer = model.list_common_keys

    def call_add(self):
        completion = self.completer() if self.completer else None
        dialog = AddTranslationDialog(completion, self)
        dialog.show()
        dialog.translation_add.connect(self.add_sorting)
        point = self.table.mapToGlobal(self.table.rect().bottomLeft())
        point.setY(point.y() + 2)
        dialog.move(point)

    def add_sorting(self, data, display):
        values = [v.strip(' ') for v in display.split(',')]
        self.context.sorting_settings[self.key, data] = values
        self.model.layoutChanged.emit()
        self.model.sorting_edited.emit()


class SortingTableModel(QtCore.QAbstractTableModel):
    sorting_edited = QtCore.Signal()

    def __init__(self, key, context):
        super().__init__()
        self.key = key
        self.context = context

    def rowCount(self, *_):
        try:
            return len(self.context.sorting_settings.data[self.key])
        except KeyError:  # No entry already recorded
            return 0

    def columnCount(self, *_):
        return 2

    def deleted_rows(self, rows):
        self.layoutAboutToBeChanged.emit()
        dict_keys = sorted(self.context.sorting_settings.data[self.key].keys())
        dict_keys = [dict_keys[r] for r in rows]
        for dict_key in dict_keys:
            del self.context.sorting_settings.data[self.key][dict_key]
        self.layoutChanged.emit()
        self.sorting_edited.emit()

    def headerData(self, section, orientation, role):
        if role != QtCore.Qt.DisplayRole:
            return
        if orientation == QtCore.Qt.Horizontal:
            return ('Keyword', 'Value order')[section]

    def flags(self, index):
        flags = QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable
        if index.column() == 0:
            return flags
        return flags | QtCore.Qt.ItemIsEditable

    def setData(self, index, value, role):
        if role != QtCore.Qt.EditRole:
            return False
        dict_keys = sorted(
            self.context.sorting_settings.data[self.key].keys())
        dict_key = dict_keys[index.row()]
        values = [v.strip(' ') for v in value.split(',')]
        self.context.sorting_settings[self.key, dict_key] = values
        self.sorting_edited.emit()
        return True

    def data(self, index, role):
        if role not in (QtCore.Qt.DisplayRole, QtCore.Qt.EditRole):
            return

        dict_keys = sorted(
            self.context.sorting_settings.data[self.key].keys())
        dict_key = dict_keys[index.row()]
        if index.column() == 0:
            return dict_key
        return ', '.join(self.context.sorting_settings[self.key, dict_key])


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
