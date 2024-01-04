
from random import randint


DEFAULT_OUTPUT_HEIGHT = 15
FORKS_PADDING = 30
FORKS_WIDTH = 30
FORKS_XRADIUS = 5
OUTPUT_WIDTH = FORKS_PADDING + 20
OUTPUT_ARROW_RADIUS = 4
DEFAULT_COLUMN_WIDTH = 125
DEFAULT_ROW_SPACING = 0
TOP_RESIZER_HEIGHT = 25
LEFT_RESIZER_WIDTH = 15
MINIUM_COLUMN_WIDTH = 30
MINIUM_ROW_HEIGHT = 10
MAXIMUM_ROW_HEIGHT = 150
TOTAL_WIDTH = 60
GRADUATION_HEIGHT = 25


def sum_float1(value, suffix, _):
    return f'{round(value, 1)}{suffix}'


def sum_float2(value, suffix, _):
    return f'{round(value, 2)}{suffix}'


def percent(value, suffix, maximum):
    return f'{round((value / maximum) * 100, 1)}{suffix}'


FORMATTERS = {
    'Percent': percent,
    'Sum as float 1': sum_float1,
    'Sum as float 2': sum_float2,
}


class AbstractSettings:
    """
    Abstract class of settings which can be used as a 3 dimensional defaultdict
    _populate_missing_settings is the method to react to add missing values
    during the get.
    """
    def __init__(self):
        self.data = []

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
            for row in range(len(self.data), index + 1):
                self.data.append({
                    'header': str(row),
                    'width': DEFAULT_COLUMN_WIDTH,
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
            'top_padding': 0,
            'bottom_padding': 0,
            'formatter': list(FORMATTERS.keys())[0],
            'value_suffix': '%'})


class ColorsSettings(AbstractSettings):

    def __init__(self):
        self.data = {}

    def _populate_missing_settings(self, color_type):
        self.data.setdefault(color_type, {})

    def __getitem__(self, index_key):
        color_type, key = index_key
        self._populate_missing_settings(color_type)
        return self.data[color_type].setdefault(key, random_color())


def random_color():
    return f'#{randint(0, 255):02X}{randint(0, 255):02X}{randint(0, 255):02X}'
