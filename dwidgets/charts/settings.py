import itertools
from random import randint


DEFAULT_OUTPUT_HEIGHT = 15
FORKS_PADDING = 30
FORKS_WIDTH = 30
FORKS_XRADIUS = 5
OUTPUT_WIDTH = 10
OUTPUT_WIDTH_EXPANDED = 80
OUTPUT_ARROW_RADIUS = 4
DEFAULT_COLUMN_WIDTH = 125
TABLE_MINIMUM_WIDTH = 60
DEFAULT_ROW_SPACING = 0
TOP_RESIZER_HEIGHT = 25
LEFT_RESIZER_WIDTH = 15
MINIUM_COLUMN_WIDTH = 30
MINIUM_ROW_HEIGHT = 10
MAXIMUM_ROW_HEIGHT = 150
TOTAL_WIDTH = 60
GRADUATION_HEIGHT = 18
DEFAULT_SETTINGS = {
    'display_output_type': False,
    'header_width': 200,
    'display_keys': False,
    'hidden_keywords': [],
    'default_formatter': 'Percent on output',
    'default_value_suffix': '',
    'use_value_color_for_nodes': False,
    'vsort_nodes_method': 'Alphabetical'
}
COLORS = (
    '#FDBCB4',
    '#F7CDC9',
    '#FFF8E8',
    '#B3CCE8',
    '#749AD6',
    '#536CB0',
    '#B8C3D3',
    '#CEDABF',
    '#E1C1D0',
    '#EFD1CD',
    '#FDECCE',
    '#91EBE8',
    '#C2F7EB',
    '#EAFAF9',
    '#C1EDFA',
    '#AEE5FA',
    '#A0D4F8',
    '#C6DFC8',
    '#FFF3DE',
    '#F6D5C2',
    '#FFADBB',
    '#D39CB6'
)


def sum_float1(value, suffix, _, __, ___):
    return f'{round(value, 1)}{suffix}'


def sum_float2(value, suffix, _, __, ___):
    return f'{round(value, 2)}{suffix}'


def max_percent(value, suffix, _, maximum, __):
    return f'{round((value / maximum) * 100, 1)}{suffix} %'


def total_percent(value, suffix, _, __, total):
    return f'{round((value / total) * 100, 1)}{suffix} %'


def output_percent(value, suffix, output_total, *_):
    return f'{round((value / output_total) * 100, 1)}{suffix} %'


FORMATTERS = {
    'Default': None,
    'Percent on max': max_percent,
    'Percent on total': total_percent,
    'Percent on output': output_percent,
    'Sum as float 1': sum_float1,
    'Sum as float 2': sum_float2,
}


class ChartViewContext:
    def __init__(self):
        self.branch_settings = BranchSettings()
        self.deph_settings = DephSettings()
        self.colors_settings = ColorsSettings()
        self.translation_settings = TranslationSettings()
        self.sorting_settings = SortingSettings()
        self.settings = {}

    def get_settings(self):
        default = DEFAULT_SETTINGS.copy()
        default.update(self.settings)
        self.settings.update(default)
        return self.settings

    def set_settings(self, settings):
        self.settings = settings

    def set_setting(self, key, value):
        if key not in DEFAULT_SETTINGS:
            raise ValueError(f'"{key}" setting does not exists.')
        self.settings[key] = value

    def get_setting(self, key):
        if key not in DEFAULT_SETTINGS:
            raise ValueError(f'"{key}" setting does not exists.')
        return self.settings.setdefault(key, DEFAULT_SETTINGS[key])

    def get_output_width(self):
        if not self.get_setting('display_output_type'):
            return OUTPUT_WIDTH
        return OUTPUT_WIDTH_EXPANDED


class AbstractSettings:
    """
    Abstract class of settings which can be used as a 3 dimensional defaultdict
    _populate_missing_settings is the method to react to add missing values
    during the get.
    """
    def __init__(self):
        self.data = []

    def from_list(self, data):
        self.data = data

    def set_data(self, data):
        self.data = data

    def __bool__(self):
        return True

    def __len__(self):
        return len(self.data)

    def __getitem__(self, index_key):
        index, key = index_key
        self._populate_missing_settings(index)
        return self.data[index][key]

    def __setitem__(self, index_key, value):
        index, key = index_key
        self._populate_missing_settings(index)
        self.data[index][key] = value

    def __repr__(self):
        return repr(self.data)

    def _populate_missing_settings(self):
        raise NotImplementedError()


class DephSettings(AbstractSettings):
    """
    This is the class defined to store the settings of the columns
    """
    def _populate_missing_settings(self, index):
        if index >= len(self.data):
            for _ in range(len(self.data), index + 1):
                self.data.append({
                    'spacing': DEFAULT_ROW_SPACING,
                    'fork_spacing': 0})


class BranchSettings(AbstractSettings):
    """
    This is the class defined to store the settings of the rows
    """
    def __init__(self):
        self.data = {}

    def _populate_missing_settings(self, branch):
        self.data.setdefault(branch, {
            'height': DEFAULT_OUTPUT_HEIGHT,
            'visibility': 'Always',
            'top_padding': 0,
            'bottom_padding': 0,
            'formatter': list(FORMATTERS.keys())[0],
            'value_suffix': '%'})


class TranslationSettings(AbstractSettings):
    def __init__(self):
        self.data = {}

    def _populate_missing_settings(self, word_type):
        self.data.setdefault(word_type, {})

    def __getitem__(self, index_key):
        word_type, key = index_key
        self._populate_missing_settings(word_type)
        return self.data[word_type].get(key, key)


class SortingSettings(AbstractSettings):

    def __init__(self):
        self.data = {}

    def _populate_missing_settings(self, sorting_type):
        self.data.setdefault(sorting_type, {})

    def __getitem__(self, index_key):
        sorting_type, node_type = index_key
        self._populate_missing_settings(sorting_type)
        return self.data[sorting_type].get(node_type, [])


class ColorsSettings(AbstractSettings):

    def __init__(self):
        self.data = {}
        self.generator = itertools.cycle(COLORS)

    def _populate_missing_settings(self, color_type):
        self.data.setdefault(color_type, {})

    def __getitem__(self, index_key):
        color_type, key = index_key
        self._populate_missing_settings(color_type)
        return self.data[color_type].setdefault(key, next(self.generator))
