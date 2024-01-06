import sys, os
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import shutil
from functools import partial
from PySide2 import QtWidgets, QtCore
from dwidgets.charts.model import ChartModel, ChartFilter
from dwidgets.charts.settings import (
    BranchSettings, DephSettings, ColorsSettings,
    get_settings, set_settings)
from dwidgets.charts.chartview import ChartView
from dwidgets.charts.schemawidgets import SchemaEditor
from dwidgets.charts.settingswidgets import (
    BranchSettingDialog, ChartSettings, ColorsSettingsEditor, DephTableModel,
    ErasePreset, FiltersWidget, SliderDelegate, WidgetToggler)


class ChartWidget(QtWidgets.QWidget):
    def __init__(self, preset_file_path=None, parent=None):
        super().__init__(parent)
        self.preset_file_path = preset_file_path
        self.branch_settings = BranchSettings()
        self.deph_settings = DephSettings()
        self.colors_settings = ColorsSettings()

        self.presets_bar = QtWidgets.QToolBar()
        action = QtWidgets.QAction('Preset', self)
        action.triggered.connect(self.exec_preset_menu)
        self.presets_bar.addAction(action)
        self.chart = ChartView(
            branch_settings=self.branch_settings,
            deph_settings=self.deph_settings,
            colors_settings=self.colors_settings)
        self.scroll = QtWidgets.QScrollArea()
        self.scroll.setWidget(self.chart)
        self.scroll.setWidgetResizable(True)
        self.scroll.verticalScrollBar().valueChanged.connect(
            self.chart.repaint)

        self.schema = SchemaEditor()
        self.schema.branch_settings.connect(self.edit_branch_settings)
        self.schema.schema_edited.connect(self.apply_new_schema)
        self.schema_toggler = WidgetToggler('Schema', self.schema)

        self.filters = FiltersWidget()
        self.filters.filters_edited.connect(self.chart.compute_rects)
        self.filters_toggler = WidgetToggler('Filters', self.filters)

        self.chart_settings_editor = ChartSettings()
        mtd = self.chart.compute_rects
        self.chart_settings_editor.geometries_edited.connect(mtd)
        mtd = self.chart.repaint
        self.chart_settings_editor.setting_edited.connect(mtd)
        self.chart_settings_toggler = WidgetToggler(
            'Settings', self.chart_settings_editor)

        self.colors_settings_editor = ColorsSettingsEditor(
            self.colors_settings)
        self.colors_settings_toggler = WidgetToggler(
            'Color settings', self.colors_settings_editor)

        self.deph_settings_model = DephTableModel(self.deph_settings)
        mtd = self.chart.compute_rects
        self.deph_settings_model.geometries_edited.connect(mtd)
        self.slider_delegate = SliderDelegate(self.deph_settings_model)
        self.chart.settings_changed.connect(
            self.deph_settings_model.layoutChanged.emit)

        self.deph_settings_table = QtWidgets.QTableView()
        self.deph_settings_table.setItemDelegateForColumn(
            0, self.slider_delegate)
        self.deph_settings_table.setItemDelegateForColumn(
            1, self.slider_delegate)
        self.deph_settings_table.setModel(self.deph_settings_model)
        self.deph_settings_toggler = WidgetToggler(
            'Paddings', self.deph_settings_table)

        right_widget = QtWidgets.QWidget()
        right = QtWidgets.QVBoxLayout(right_widget)
        right.setContentsMargins(0, 0, 0, 0)
        right.addWidget(self.presets_bar)
        right.addWidget(self.schema_toggler)
        right.addWidget(self.schema)
        right.addWidget(self.filters_toggler)
        right.addWidget(self.filters)
        right.addWidget(self.chart_settings_toggler)
        right.addWidget(self.chart_settings_editor)
        right.addWidget(self.deph_settings_toggler)
        right.addWidget(self.deph_settings_table)
        right.addWidget(self.colors_settings_toggler)
        right.addWidget(self.colors_settings_editor)
        right.addStretch(True)
        right_scroll = QtWidgets.QScrollArea()
        right_scroll.setWidget(right_widget)
        right_scroll.setWidgetResizable(True)

        splitter = QtWidgets.QSplitter()
        splitter.addWidget(right_scroll)
        splitter.addWidget(self.scroll)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)

        layout = QtWidgets.QHBoxLayout(self)
        layout.addWidget(splitter)

    def sizeHint(self):
        return QtCore.QSize(800, 600)

    def set_model(self, model):
        self.chart.set_model(model)
        self.colors_settings_editor.fill()
        self.filters.set_model(model)
        self.schema.set_words(model.list_common_keys())

    def apply_new_schema(self):
        if not self.schema.is_valid():
            return QtWidgets.QMessageBox.critical(
                self, 'Error', 'All nodes must have outputs',
                QtWidgets.QMessageBox.Ok, QtWidgets.QMessageBox.Ok)

        self.chart.set_schema(self.schema.get_schema())
        self.colors_settings_editor.fill()

    def set_schema(self, schema):
        self.schema.set_schema(schema)
        self.chart.set_schema(schema)
        self.colors_settings_editor.fill()

    def edit_branch_settings(self, branch):
        dialog = BranchSettingDialog(branch, self.branch_settings)
        dialog.settings_edited.connect(self.chart.compute_rects)
        dialog.exec_()

    def export_presets(self):
        filepath, result = QtWidgets.QFileDialog.getSaveFileName(
            self, 'Save preset', filter='JSON (*.json)')
        if result:
            shutil.copy(self.preset_file_path, filepath)

    def export_preset(self):
        filepath, result = QtWidgets.QFileDialog.getSaveFileName(
            self, 'Save preset', filter='JSON (*.json)')
        if not result:
            return
        name, result = QtWidgets.QInputDialog.getText(
            self, 'Preset name', 'Set name')
        if not result:
            return
        with open(filepath, 'w') as f:
            json.dump({name: self.preset()}, f, indent=2)

    def import_presets(self):
        filepath, result = QtWidgets.QFileDialog.getOpenFileNames(
            self, 'Import preset', filter='JSON (*.json)')
        if not result:
            return
        import_data = self.get_presets_data(filepath[0])
        preset_data = self.get_presets_data()
        for name, preset in import_data.items():
            if name in preset_data:
                question = ErasePreset(name, self)
                result = question.exec_()
                if not result:
                    return
                if question.group.checkedId() == 0:
                    continue
                if question.group.checkedId() == 2:
                    name = question.name.text()
            preset_data[name] = preset
        with open(self.preset_file_path, 'w') as f:
            json.dump(preset_data, f, indent=2)

    def exec_preset_menu(self):
        menu = QtWidgets.QMenu()
        point = self.presets_bar.rect().bottomLeft()

        if not self.preset_file_path:
            load_preset = QtWidgets.QAction('Load preset', self)
            load_preset.triggered.connect(self.load_preset)
            menu.addAction(load_preset)
            export_current_preset = QtWidgets.QAction('Export preset', self)
            export_current_preset.triggered.connect(self.export_preset)
            menu.addAction(export_current_preset)
            menu.exec_(self.presets_bar.mapToGlobal(point))
            return

        save_preset = QtWidgets.QAction('Save Preset', self)
        save_preset.triggered.connect(self.save_preset_dialog)
        menu.addAction(save_preset)

        import_current_preset = QtWidgets.QAction('Import presets', self)
        import_current_preset.triggered.connect(self.import_presets)
        menu.addAction(import_current_preset)

        export_preset = QtWidgets.QAction('Export presets', self)
        export_preset.triggered.connect(self.export_presets)
        menu.addAction(export_preset)

        names = sorted(self.get_presets_data().keys())
        if not names:
            menu.exec_(self.presets_bar.mapToGlobal(point))
            return

        delete = QtWidgets.QMenu("Delete preset")
        menu.addMenu(delete)
        menu.addSeparator()
        for name in names:
            action = QtWidgets.QAction(name, self)
            action.triggered.connect(partial(self.set_preset, name))
            menu.addAction(action)
            action = QtWidgets.QAction(name, self)
            action.triggered.connect(partial(self.delete_preset, name))
            delete.addAction(action)

        menu.exec_(self.presets_bar.mapToGlobal(point))

    def set_preset(self, name):
        self.apply_preset(self.get_presets_data()[name])

    def delete_preset(self, name):
        data = self.get_presets_data()
        del data[name]
        with open(self.preset_file_path, 'w') as f:
            json.dump(data, f, indent=2)

    def apply_preset(self, preset):
        set_settings(preset['settings'])
        self.colors_settings.data = preset['colors']
        self.branch_settings.data = preset['branch_settings']
        self.deph_settings.data = preset['deph_settings']
        self.chart.model.clear_filters()
        filters = [ChartFilter.deserialize(f) for f in preset['filters']]
        self.chart.model.filters = filters
        self.set_schema(preset['schema'])
        self.schema.key_list.compute_rects()

    def preset(self):
        return {
            'deph_settings': self.deph_settings.data,
            'colors': self.colors_settings.data,
            'settings': get_settings(),
            'branch_settings': self.branch_settings.data,
            'filters': [f.serialize() for f in self.chart.model.filters],
            'schema': self.chart.model.schema}

    def load_preset(self):
        filepath, result = QtWidgets.QFileDialog.getOpenFileName(
            self, 'Load preset', filters='JSON (*.json)')
        if not result:
            return
        data = self.get_presets_data(filepath)
        if len(data) == 1:
            name = list(data.keys())[0]
            self.apply_preset(data[name])

    def save_preset_dialog(self):
        name, result = QtWidgets.QInputDialog.getText(
            self, 'Preset name', 'Set name')
        if result:
            self.save_preset(self.preset_file_path, name)

    def get_presets_data(self, filepath=None):
        filepath = filepath or self.preset_file_path
        try:
            print(filepath)
            with open(filepath, 'r') as f:
                return json.load(f)
        except BaseException as e:  # File does not exist or presets are corrupted.
            print(e)
            return {}

    def save_preset(self, filepath, name):
        data = self.get_presets_data()
        data[name] = self.preset()
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)


if __name__ == '__main__':
    import os
    import json
    with open(r"C:\temp\df.json", 'r') as f:
        data = json.load(f)
    schema = {'show': ['work_type']}
    from dwidgets.charts.model import ChartEntry
    entries = [ChartEntry(d, d['time_spent']) for d in data]
    model = ChartModel()
    model.set_entries(entries)

    app = QtWidgets.QApplication([])
    preset_file_path = "c:/temp/presets.json"
    view = ChartWidget(preset_file_path)
    view.set_model(model)
    view.set_schema(schema)
    view.show()
    app.exec_()
