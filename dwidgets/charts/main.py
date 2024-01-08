import sys, os
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import shutil
from functools import partial
from PySide2 import QtWidgets, QtCore
from dwidgets.charts.model import ChartModel, ChartFilter
from dwidgets.charts.settings import ChartViewContext
from dwidgets.charts.chartview import ChartView
from dwidgets.charts.schemawidgets import SchemaEditor
from dwidgets.charts.settingswidgets import (
    BranchSettingDialog, ChartSettings, ColorsSettingsEditor,
    DephSettingsEditor, DictionnariesEditor, ErasePreset, FiltersWidget,
    SortingEditor, WidgetToggler)


class ChartWidget(QtWidgets.QWidget):
    def __init__(self, preset_file_path=None, editor=False, parent=None):
        super().__init__(parent)
        self.preset_file_path = preset_file_path
        self.context = ChartViewContext()

        preset_action = QtWidgets.QAction('Preset', self)
        preset_action.triggered.connect(self.exec_preset_menu)
        open_action = QtWidgets.QAction('Open CSV', self)
        open_action.triggered.connect(self.call_open_csv)
        data_menu = QtWidgets.QMenu('Data')
        data_menu.addAction(open_action)

        self.presets_bar = QtWidgets.QMenuBar()
        self.presets_bar.addAction(preset_action)
        self.presets_bar.addMenu(data_menu)

        self.chart = ChartView(context=self.context)
        self.scroll = QtWidgets.QScrollArea()
        self.scroll.setWidget(self.chart)
        self.scroll.setWidgetResizable(True)
        self.scroll.verticalScrollBar().valueChanged.connect(
            self.chart.repaint)

        self.schema = SchemaEditor(self.context)
        self.schema.branch_settings.connect(self.edit_branch_settings)
        self.schema.schema_edited.connect(self.apply_new_schema)
        self.schema_toggler = WidgetToggler('Schema', self.schema)

        self.filters = FiltersWidget(self.chart.model, self.context)
        self.filters.filters_edited.connect(self.chart.compute_rects)
        self.filters_toggler = WidgetToggler('Filters', self.filters)

        self.chart_settings_editor = ChartSettings(self.context)
        mtd = self.chart.compute_rects
        self.chart_settings_editor.geometries_edited.connect(mtd)
        mtd = self.chart.repaint
        self.chart_settings_editor.setting_edited.connect(mtd)
        self.chart_settings_toggler = WidgetToggler(
            'Settings', self.chart_settings_editor)

        self.colors_settings_editor = ColorsSettingsEditor(self.context)
        self.colors_settings_toggler = WidgetToggler(
            'Color settings', self.colors_settings_editor)

        self.deph_settings_editor = DephSettingsEditor(self.context)
        mtd = self.chart.compute_rects
        self.deph_settings_editor.geometries_edited.connect(mtd)
        self.deph_settings_toggler = WidgetToggler(
            'Paddings', self.deph_settings_editor)

        self.dictionnaries = DictionnariesEditor(
            self.chart.model, self.context)
        self.dictionnaries.translation_edited.connect(self.chart.repaint)
        self.dictionnaries.translation_edited.connect(self.schema.repaint)
        self.dictionnaries.translation_edited.connect(
            self.schema.tree_view.repaint)
        self.dictionnaries_toggler = WidgetToggler(
            'Dictionnaries', self.dictionnaries)

        self.sorting_editor = SortingEditor(
            context=self.context,
            completer=self.chart.model.list_common_keys)
        self.sorting_editor.sorting_edited.connect(self.chart.compute_rects)
        self.sorting_editor_toggler = WidgetToggler(
            'Sorting', self.sorting_editor)

        if not editor:
            layout = QtWidgets.QHBoxLayout(self)
            layout.addWidget(self.scroll)
            return

        right_widget = QtWidgets.QWidget()
        right = QtWidgets.QVBoxLayout(right_widget)
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(0)
        right.addWidget(self.schema_toggler)
        right.addWidget(self.schema)
        right.addWidget(self.filters_toggler)
        right.addWidget(self.filters)
        right.addWidget(self.chart_settings_toggler)
        right.addWidget(self.chart_settings_editor)
        right.addWidget(self.deph_settings_toggler)
        right.addWidget(self.deph_settings_editor)
        right.addWidget(self.colors_settings_toggler)
        right.addWidget(self.colors_settings_editor)
        right.addWidget(self.dictionnaries_toggler)
        right.addWidget(self.dictionnaries)
        right.addWidget(self.sorting_editor_toggler)
        right.addWidget(self.sorting_editor)
        right.addStretch(True)
        right_scroll = QtWidgets.QScrollArea()
        right_scroll.setWidget(right_widget)
        right_scroll.setWidgetResizable(True)

        full_right = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(full_right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        right_layout.addWidget(self.presets_bar)
        right_layout.addWidget(right_scroll)

        splitter = QtWidgets.QSplitter()
        splitter.addWidget(full_right)
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
        self.dictionnaries.set_model(model)
        self.sorting_editor.set_model(model)
        self.schema.set_words(model.list_common_keys())

    def set_entries(self, entries):
        result = self.chart.model.set_entries(entries)
        if not result:
            self.chart.model.set_schema({})
            self.schema.set_schema({})
        self.chart.compute_rects()
        self.schema.set_words(model.list_common_keys())
        self.colors_settings_editor.fill()

    def set_polars_dataframe(self, df, weight_key=None):
        python_dicts = [
            {col.name.replace('|', '-'): value
                for col, value in zip(df.get_columns(), list(row))}
            for row in df.iter_rows()]
        entries = [
            ChartEntry(
                python_dict,
                weight=(
                    python_dicts.get(weight_key, 1)
                    if weight_key is not None else 1))
            for python_dict in python_dicts]
        self.set_entries(entries)

    def call_open_csv(self):
        filepath, result = QtWidgets.QFileDialog.getOpenFileName(
            self, 'Open CSV', filter='(*.csv) | (*.xlsx)')
        if not result:
            return
        self.open_csv(filepath)

    def open_csv(self, filepath):
        try:
            import polars
        except ModuleNotFoundError:
            return QtWidgets.QMessageBox.critical(
                self, 'Error',
                'Polars Library is required to read csv, "pip install polars"',
                QtWidgets.QMessageBox.Ok, QtWidgets.QMessageBox.Ok)
        if os.path.splitext(os.path.basename(filepath))[:-1].lower() == '.csv':
            dataframe = polars.read_csv(filepath)
        else:
            dataframe = polars.read_xlsx(filepath, 'time_spent')
        self.set_polars_dataframe(dataframe, 'time_spent')

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
        dialog = BranchSettingDialog(branch, self.context.branch_settings)
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

        delete = QtWidgets.QMenu('Delete preset')
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
        self.context.set_settings(preset['settings'])
        self.context.colors_settings.data = preset['colors']
        self.context.branch_settings.data = preset['branch_settings']
        self.context.deph_settings.data = preset['deph_settings']
        self.context.translation_settings.data = preset['translation_settings']
        self.chart.model.clear_filters()
        filters = [ChartFilter.deserialize(f) for f in preset['filters']]
        self.chart.model.filters = filters
        self.chart.model.set_entries()
        self.set_schema(preset['schema'])
        self.schema.key_list.compute_rects()

    def preset(self):
        return {
            'deph_settings': self.context.deph_settings.data,
            'translation_settings': self.context.translation_settings.data,
            'colors': self.context.colors_settings.data,
            'settings': self.context.get_settings(),
            'branch_settings': self.context.branch_settings.data,
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
            with open(filepath, 'r') as f:
                return json.load(f)
        except BaseException as e:
            # File does not exist or presets are corrupted.
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
    file_path = "c:/temp/presets.json"
    view = ChartWidget(preset_file_path=file_path, editor=True)
    view.context.translation_settings['value', 'external'] = 'Client'
    view.context.translation_settings['key', 'user-code'] = 'User'
    view.context.sorting_settings['value', 'work_type'] = ['1st-pass', 'lead', 'external']
    view.set_model(model)
    view.set_schema(schema)
    view.show()
    app.exec_()
