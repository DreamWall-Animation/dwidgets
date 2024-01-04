import sys, os
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from PySide2 import QtWidgets, QtCore
from dwidgets.charts.model import ChartModel
from dwidgets.charts.settings import (
    BranchSettings, DephSettings, ColorsSettings)
from dwidgets.charts.chartview import ChartView
from dwidgets.charts.schemawidgets import SchemaEditor
from dwidgets.charts.settingswidgets import (
    BranchSettingsEditor, ColorsSettingsEditor,
    DephTableModel, SliderDelegate, WidgetToggler)


class ChartWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.branch_settings = BranchSettings()
        self.deph_settings = DephSettings()
        self.colors_settings = ColorsSettings()

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
        self.schema.schema_edited.connect(self.apply_new_schema)
        self.schema_toggler = WidgetToggler('Schema', self.schema)

        self.branch_settings_editor = BranchSettingsEditor(
            self.chart.model, self.branch_settings)
        self.branch_settings_editor.settings_edited.connect(
            self.chart.compute_rects)
        self.chart.settings_changed.connect(
            self.branch_settings_editor.update_settings_values)
        self.branch_settings_toggler = WidgetToggler(
            'Branch settings', self.branch_settings_editor)

        self.colors_settings_editor = ColorsSettingsEditor(
            self.colors_settings)
        self.colors_settings_toggler = WidgetToggler(
            'Color settings', self.colors_settings_editor)

        self.deph_settings_model = DephTableModel(self.deph_settings)
        self.deph_settings_model.header_edited.connect(self.chart.repaint)
        mtd = self.chart.compute_rects
        self.deph_settings_model.geometries_edited.connect(mtd)
        self.slider_delegate = SliderDelegate(self.deph_settings_model)
        self.chart.settings_changed.connect(
            self.deph_settings_model.layoutChanged.emit)

        self.deph_settings_table = QtWidgets.QTableView()
        self.deph_settings_table.setItemDelegateForColumn(
            1, self.slider_delegate)
        self.deph_settings_table.setItemDelegateForColumn(
            2, self.slider_delegate)
        self.deph_settings_table.setItemDelegateForColumn(
            3, self.slider_delegate)
        self.deph_settings_table.setModel(self.deph_settings_model)
        self.deph_settings_toggler = WidgetToggler(
            'Column settings', self.deph_settings_table)

        right_widget = QtWidgets.QWidget()
        right = QtWidgets.QVBoxLayout(right_widget)
        right.addWidget(self.schema_toggler)
        right.addWidget(self.schema)
        right.addWidget(self.branch_settings_toggler)
        right.addWidget(self.branch_settings_editor)
        right.addWidget(self.deph_settings_toggler)
        right.addWidget(self.deph_settings_table)
        right.addWidget(self.colors_settings_toggler)
        right.addWidget(self.colors_settings_editor)
        right.addStretch(True)
        right_scroll = QtWidgets.QScrollArea()
        right_scroll.setWidget(right_widget)
        right_scroll.setWidgetResizable(True)

        splitter = QtWidgets.QSplitter()
        splitter.addWidget(self.scroll)
        splitter.addWidget(right_scroll)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)

        layout = QtWidgets.QHBoxLayout(self)
        layout.addWidget(splitter)

    def sizeHint(self):
        return QtCore.QSize(800, 600)

    def set_model(self, model):
        self.chart.set_model(model)
        self.branch_settings_editor.set_model(model)
        self.colors_settings_editor.fill()
        self.schema.set_words(model.list_common_keys())

    def apply_new_schema(self):
        self.chart.set_schema(self.schema.get_schema())
        self.branch_settings_editor.update_settings_branches()
        self.colors_settings_editor.fill()

    def set_schema(self, schema):
        self.schema.set_schema(schema)
        self.chart.set_schema(schema)
        self.branch_settings_editor.update_settings_branches()
        self.colors_settings_editor.fill()


if __name__ == '__main__':
    import os
    import json
    path = '$DEV_DATA_ROOT/dwidgets/charts_test.json'
    with open(os.path.expandvars(path), 'r') as f:
        data = json.load(f)
        for d in data[0]:
            d['user'] = d['user']['code']
            d['task_type'] = d['task']['code'].split('-')[-1]
            d['task'] = d['task']['code']
            d['month'] = f'{d["date"][4:6]}-{d["date"][:4]}'
            d['episode'] = d['task'].split('-')[0]
    schema = {
        'user': [
            'work_type',
            'task_type',
            {
                'month': [
                    'work_type',
                    'task_type',
                    {'episode': ['task_type']}
                ]
            }
        ]
    }
    from dwidgets.charts.model import ChartEntry
    entries = [ChartEntry(d, d['time_spent']) for d in data[0]]
    model = ChartModel()
    model.set_entries(entries)

    app = QtWidgets.QApplication([])
    view = ChartWidget()
    view.set_model(model)
    view.set_schema(schema)
    view.show()
    app.exec_()



    # from dwidgets.charts.model import schema_to_tree, tree_to_schema
    # tree = schema_to_tree(schema)
    # for node in tree.flat():
    #     print(node)
    #     for output in node.outputs():
    #         print(output)
    # import pprint
    # pprint.pprint(tree_to_schema(tree))



    # from dwidgets.charts.schemawidgets import SchemaEditor
    # app = QtWidgets.QApplication([])
    # view = SchemaEditor()
    # view.set_schema(schema)
    # view.set_words(model.list_common_keys())
    # view.show()
    # app.exec_()
