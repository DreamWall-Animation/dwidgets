import os
import json
from functools import partial
from PySide2 import QtWidgets, QtCore
from PySide2.QtCore import Qt
from dwidgets.qtutils import move_widget_in_screen


EMPTY_LABEL = '-'


class Presets:
    def __init__(self, json_path):
        self.json_path = json_path

    def _get_presets_content(self):
        os.makedirs(os.path.dirname(self.json_path), exist_ok=True)
        try:
            with open(self.json_path, 'r') as f:
                return json.load(f)
        except json.decoder.JSONDecodeError:
            print(f'Corrupted preset file: {self.json_path}')
            return {}
        except FileNotFoundError:  # Does not exists yet
            return {}

    def list_available_presets(self, button_id):
        presets = self._get_presets_content()
        if button_id not in presets:
            return []
        return list(presets.get(button_id, {}).get('presets', []))

    def get_preset(self, button_id, name):
        if not os.path.exists(self.json_path):
            return []
        try:
            with open(self.json_path, 'r') as f:
                presets = json.load(f)
                r = presets.get(button_id, {}).get('presets', {}).get(name, [])
                return r
        except json.decoder.JSONDecodeError:
            print(f'Corrupted preset file: {self.json_path}')
            return []

    def save_preset(self, button_id, name, values):
        presets = self._get_presets_content()
        button_data = presets.setdefault(button_id, {'presets': {}})
        button_preset = button_data.get('presets', {})
        button_preset[name] = values
        with open(self.json_path, 'w') as f:
            return json.dump(presets, f, indent=4)

    def remove_preset(self, button_id, name):
        presets = self._get_presets_content()
        try:
            del presets[button_id]['presets'][name]
        except KeyError:
            print(f'Preset does not exists {button_id}, {name}')
        with open(self.json_path, 'w') as f:
            return json.dump(presets, f, indent=4)

    def save_states(self, button_id, states):
        presets = self._get_presets_content()
        button_data = presets.setdefault(button_id, {'presets': {}})
        button_data['states'] = states
        with open(self.json_path, 'w') as f:
            return json.dump(presets, f, indent=4)

    def get_states(self, button_id):
        presets = self._get_presets_content()
        return presets.get(button_id, {}).get('states')


def get_multiple_selection_text(
        selected_labels, max_labels, included_title=None):
    if not selected_labels or len(selected_labels) == max_labels:
        text = f'{included_title} (off)' if included_title else EMPTY_LABEL
    elif len(selected_labels) == 1:
        text = selected_labels[0]
        text = f'{included_title}: {text}' if included_title else text
    else:
        text = f'({len(selected_labels)}/{max_labels})'
        text = f'{included_title}: {text}' if included_title else text
    if text == '':
        text = '(empties)'
    return text


class ListWidgetForCheckboxes(QtWidgets.QListView):
    """
    Only here to be able to style it differently.
    """


class PopupCheckList(QtWidgets.QMenu):

    def __init__(
            self,
            items=None,
            selection_limit=None,
            model=None,
            size=None,
            parent=None):
        super().__init__(parent, Qt.Popup | Qt.FramelessWindowHint)
        if size:
            self.setFixedSize(size)

        self.search = QtWidgets.QLineEdit()
        self.search.textEdited.connect(self.research)
        self.model = model or PopupCheckListModel(items, selection_limit)
        self.proxy = PopupCheckListProxyModel()
        self.proxy.setSourceModel(self.model)
        self.list = QtWidgets.QListView()
        self.list.clicked.connect(self.list_clicked)
        self.list.setModel(self.proxy)

        all_ = QtWidgets.QPushButton('All')
        all_.released.connect(self.model.check_all)
        clear = QtWidgets.QPushButton('Clear')
        clear.released.connect(partial(self.model.check_all, False))
        invert = QtWidgets.QPushButton('Invert')
        invert.released.connect(self.model.invert)

        buttons = QtWidgets.QHBoxLayout()
        buttons.setSpacing(0)
        buttons.setContentsMargins(0, 0, 0, 0)
        if not selection_limit:
            buttons.addWidget(all_)
        buttons.addWidget(clear)
        if not selection_limit:
            buttons.addWidget(invert)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.search)
        layout.addWidget(self.list)
        layout.addLayout(buttons)

    def list_clicked(self, index):
        index = self.proxy.mapToSource(index)
        row = index.row()
        self.model.set_checked_row(row, not self.model.checked[row])

    def research(self, text):
        self.proxy.set_text_filter(text)

    def sizeHint(self):
        return QtCore.QSize(250, 250)

    def popup(self, *args, **kwargs):
        self.search.setFocus(Qt.MouseFocusReason)
        super().popup(*args, **kwargs)


class DeletePresetDialog(QtWidgets.QDialog):
    def __init__(self, names, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Delete preset')
        self.combo = QtWidgets.QComboBox()
        self.combo.addItems(names)
        self.delete_button = QtWidgets.QPushButton('Delete')
        self.delete_button.released.connect(self.accept)
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.combo)
        layout.addWidget(self.delete_button)

    @property
    def preset_name(self):
        return self.combo.currentText()


class PopupCheckListProxyModel(QtCore.QSortFilterProxyModel):
    def __init__(self):
        super().__init__()
        self._text_filter = ''

    def filterAcceptsRow(self, source_row, _):
        model = self.sourceModel()
        label = model.items[source_row][0].lower()
        return all(
            n in label for m in self._text_filter.lower().split(',')
            for n in m.split(' '))

    def set_text_filter(self, text):
        self._text_filter = text
        self.invalidateFilter()


class PopupCheckListModel(QtCore.QAbstractListModel):
    checked_items_changed = QtCore.Signal(list)

    def __init__(self, items=None, selection_limit=None):
        super().__init__()
        self.items = items.copy() if items else []
        self.checked = [False] * len(self.items)
        self.selection_history = []  # used in case of check limitation
        self.selection_limit = selection_limit

    def rowCount(self, *_):
        return len(self.items)

    def flags(self, _):
        return Qt.ItemIsEnabled | Qt.ItemIsUserCheckable

    # In order to be able to toggle the state clicking on the label as well,
    # the setData is disabled.
    # def setData(self, index, value, role):
    #     if role == Qt.CheckStateRole:
    #         self.layoutAboutToBeChanged.emit()
    #         if value == Qt.Checked:
    #             self.checked[index.row()] = True
    #             self.append_selected_to_history(index.row())
    #         else:
    #             self.checked[index.row()] = False
    #             self.remove_selected_from_history(index.row())
    #         self.checked_items_changed.emit(self.checked_data())
    #         self.layoutChanged.emit()
    #         return True
    #     return False

    def remove_selected_from_history(self, row):
        if row in self.selection_history:
            self.selection_history.remove(row)

    def append_selected_to_history(self, row):
        if not self.selection_limit:
            return
        if row in self.selection_history:
            self.selection_history.remove(row)
            self.selection_history.append(row)
            return
        self.selection_history.append(row)
        if len(self.selection_history) <= self.selection_limit:
            return
        turn_off_index = self.selection_history.pop(0)
        self.checked[turn_off_index] = False

    def row(self, row):
        return self.items[row]

    def set_items(self, items):
        self.layoutAboutToBeChanged.emit()
        data = self.checked_data()
        self.items = items
        self.set_checked_data(data)
        self.layoutChanged.emit()

    def data(self, index, role=Qt.UserRole):
        if role == Qt.UserRole:
            return self.items[index.row()][-1]
        if role == Qt.DisplayRole:
            return self.items[index.row()][0]
        if role == Qt.CheckStateRole:
            return Qt.Checked if self.checked[index.row()] else Qt.Unchecked

    def set_checked_row(self, row, state):
        self.layoutAboutToBeChanged.emit()
        self.checked[row] = state
        if state:
            self.append_selected_to_history(row)
        else:
            self.remove_selected_from_history(row)
        self.checked_items_changed.emit(self.checked_data())
        self.layoutChanged.emit()

    def set_checked_data(self, data, unchecked=False):
        self.layoutAboutToBeChanged.emit()
        if not unchecked:
            self.checked = [item_data in data for (_, item_data) in self.items]
        else:
            self.checked = [
                item_data not in data for (_, item_data) in self.items]

        # Restore a selection history if a limit has been set.
        if self.selection_limit is not None:
            checked_indexes = [
                i for i, s in enumerate(self.checked) if s is True]
            checked_indexes = checked_indexes[-self.selection_limit:]
            self.checked = [
                i in checked_indexes for i in range(len(self.items))]
            self.selection_history = checked_indexes

        self.layoutChanged.emit()

    def checked_data(self):
        return [self.items[i][-1] for i, v in enumerate(self.checked) if v]

    def unchecked_data(self):
        return [self.items[i][-1] for i, v in enumerate(self.checked) if not v]

    def checked_labels(self):
        return [self.items[i][0] for i, v in enumerate(self.checked) if v]

    def check_all(self, state=True):
        self.layoutAboutToBeChanged.emit()
        self.checked = [state for _ in self.checked]
        self.checked_items_changed.emit(self.checked_data())
        self.layoutChanged.emit()

    def invert(self):
        self.layoutAboutToBeChanged.emit()
        self.checked = [not state for state in self.checked]
        self.checked_items_changed.emit(self.checked_data())
        self.layoutChanged.emit()

    def has_filter_activated(self):
        return all(self.checked) or not any(self.checked)


class PopupCheckListButton2(QtWidgets.QWidget):
    checked_items_changed = QtCore.Signal(list)

    def __init__(
            self, included_title=None, static_title=False, items=None,
            allow_save_presets=False, selection_limit=None, presets_path=None,
            presets_button_id=None, restore_states=True, default=False,
            save_unchecked_values=False, parent=None):
        super().__init__(parent)
        self.menu_width = None

        self.model = PopupCheckListModel(
            items=items, selection_limit=selection_limit)
        self.model.checked_items_changed.connect(self._set_text)
        self.model.checked_items_changed.connect(self.save_states)
        self.model.checked_items_changed.connect(
            self.checked_items_changed.emit)

        self.presets = Presets(presets_path) if presets_path else None
        self.presets_button_id = presets_button_id
        self.save_unchecked_states = save_unchecked_values
        self.static_title = static_title

        self.presets_menu = None

        self.menu = None
        self.included_title = included_title

        self.button = QtWidgets.QPushButton()
        self.button.clicked.connect(self.popup)
        self.presets_dropdown = QtWidgets.QPushButton('▼')
        self.presets_dropdown.released.connect(self.execute_preset_menu)
        self.presets_dropdown.setFixedWidth(20)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.button)
        if allow_save_presets:
            layout.addWidget(self.presets_dropdown)

        self.set_items = self.model.set_items
        self.set_checked_data = self.model.set_checked_data
        self.checked_labels = self.model.checked_labels
        self.checked_data = self.model.checked_data
        self.all_checked = self.model.has_filter_activated
        self.check_all = self.model.check_all
        self.uncheck_all = partial(self.model.check_all, False)
        self.invert = self.model.invert

        if self.presets and restore_states:
            states = self.presets.get_states(self.presets_button_id)
            if states is not None:
                self.model.set_checked_data(
                    states, self.save_unchecked_states)
            else:
                self.model.check_all(default)
        else:
            self.model.check_all(default)

        self._set_text()

    def save_states(self, data):
        if not self.presets:
            return
        if self.save_unchecked_states:
            data = self.model.unchecked_data()
        self.presets.save_states(self.presets_button_id, data)

    def popup(self):
        position = self.mapToGlobal(self.rect().bottomLeft())
        if self.menu is None:
            self.menu = PopupCheckList(
                model=self.model,
                selection_limit=self.model.selection_limit,
                parent=self)
            if self.menu_width:
                self.menu.setFixedWidth(self.menu_width)
        self.menu.popup(position)
        move_widget_in_screen(self.menu)

    def _set_text(self):
        if self.static_title:
            self.button.setText(self.included_title or EMPTY_LABEL)
            return
        labels = self.model.checked_labels()
        text = get_multiple_selection_text(
            labels, self.model.rowCount(), self.included_title)
        self.button.setText(text)

    def mousePressEvent(self, event):
        if event.type() == QtCore.QEvent.MouseButtonPress:
            if event.button() == Qt.MiddleButton:
                self.model.check_all(False)
            elif event.button() == Qt.RightButton:
                self.model.invert()
        return super().mousePressEvent(event)

    def execute_preset_menu(self):
        self.presets_menu = QtWidgets.QMenu(self)
        save_action = QtWidgets.QAction('Save preset', self)
        save_action.triggered.connect(self.save_preset)
        self.presets_menu.addAction(save_action)

        names = self.presets.list_available_presets(self.presets_button_id)
        if names:
            remove_action = QtWidgets.QAction('Remove preset', self)
            remove_action.triggered.connect(self.remove_preset)
            self.presets_menu.addAction(remove_action)

            self.presets_menu.addSeparator()
            for name in names:
                action = QtWidgets.QAction(name, self)
                action.triggered.connect(partial(self.set_preset, name))
                self.presets_menu.addAction(action)

        point = self.button.rect().bottomLeft()
        point = self.button.mapToGlobal(point)
        self.presets_menu.exec_(point)

    def set_preset(self, name):
        data = self.presets.get_preset(self.presets_button_id, name)
        self.model.set_checked_data(data)
        self.save_states(data)
        self.checked_items_changed.emit(self.model.checked_data())

    def save_preset(self):
        name, result = QtWidgets.QInputDialog.getText(self, 'Preset Name', '')
        if not result:
            return
        self.presets.save_preset(
            self.presets_button_id, name,
            self.model.checked_data())

    def remove_preset(self):
        names = self.presets.list_available_presets(self.presets_button_id)
        diag = DeletePresetDialog(names)
        if not diag.exec_():
            return
        self.presets.remove_preset(self.presets_button_id, diag.preset_name)

    def setFixedWidth(self, width):
        self.menu_width = width
        super().setFixedWidth(width)


if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    items = [
        ('porque', 'torqué'),
        ('vamos', 'part'),
        ('paraliki', 'paralaka'),
        ('porqua', 'tioquerqué'),
        ('vamosso', 'par0t'),
        ('paralikouii', 'paralaku')]
    menu = PopupCheckListButton2(
        'Ramon zora',
        selection_limit=0,
        presets_path='c:/temp/my_preset_test.json',
        presets_button_id='theoneandonly',
        allow_save_presets=True,
        save_unchecked_values=True,
        restore_states=True,
        items=items)
    menu.show()
    app.exec_()
