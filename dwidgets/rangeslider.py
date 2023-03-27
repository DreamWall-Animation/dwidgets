from PySide2 import QtWidgets, QtCore, QtGui


DEFAULT_MIN = 0
DEFAULT_MAX = 100


class RangeSlider(QtWidgets.QWidget):
    range_changed = QtCore.Signal(object, object)

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.decimal = 0
        self.low = QtWidgets.QLineEdit(str(DEFAULT_MIN))
        self.low.textEdited.connect(self.range_edited)
        self.low.setValidator(QtGui.QIntValidator())
        self.low.setFixedWidth(50)

        self.high = QtWidgets.QLineEdit(str(DEFAULT_MAX))
        self.high.textEdited.connect(self.range_edited)
        self.high.setValidator(QtGui.QIntValidator())
        self.high.setFixedWidth(50)
        self.bar = RangeSliderBar()
        self.low_changed = self.bar.low_changed
        self.high_changed = self.bar.high_changed
        self.bar.low_changed.connect(self.set_low)
        self.bar.high_changed.connect(self.set_high)

        self.range = self.bar.range
        self.set_full_range = self.bar.set_full_range
        self.is_min = self.bar.is_min
        self.is_max = self.bar.is_max
        self.is_default = self.bar.is_default

        layout = QtWidgets.QHBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.low)
        layout.addWidget(self.bar)
        layout.addWidget(self.high)

    def set_range(self, low, high):
        self.bar.set_range(low, high)
        self.set_low(low)
        self.set_high(high)

    def set_decimal(self, decimal):
        self.decimal = decimal
        v = QtGui.QDoubleValidator() if decimal else QtGui.QIntValidator()
        self.low.setValidator(v)
        self.high.setValidator(v)
        self.bar.set_decimal(decimal)

    def set_low(self, value):
        self.low.setText(str(value))
        self.range_set()

    def set_high(self, value):
        self.high.setText(str(value))
        self.range_set()

    def range_set(self, *_):
        minimum = self.low.text()
        maximum = self.high.text()
        if not all((minimum, maximum)):
            return
        print(minimum, maximum)
        cls = float if self.decimal else int
        self.range_changed.emit(cls(float(minimum)), cls(float(maximum)))

    def range_edited(self, *_):
        cls = float if self.decimal else int
        minimum = cls(float(self.low.text()))
        maximum = cls(float(self.high.text()))
        self.range_changed.emit(minimum, maximum)
        self.bar.low = minimum
        self.bar.high = maximum
        self.bar.repaint()


class RangeSliderBar(QtWidgets.QWidget):
    low_changed = QtCore.Signal(object)
    high_changed = QtCore.Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.decimal = 0
        self._min = DEFAULT_MIN
        self._max = DEFAULT_MAX
        self._low = self._min
        self._high = self._max
        self._edit_mode = None
        self._mousepressed = False

        self.bracket_color = '#000000'
        self.range_color = '#777777'
        self.background_color = '#666666'
        self.border_color = '#111111'

    def sizeHint(self):
        return QtCore.QSize(400, 25)

    @property
    def min(self):
        return self._min / 10 ** self.decimal

    @min.setter
    def min(self, value):
        self._min = value * (10 ** self.decimal)
        self.repaint()

    @property
    def max(self):
        return self._max / 10 ** self.decimal

    @max.setter
    def max(self, value):
        self._max = value * (10 ** self.decimal)
        self.repaint()

    @property
    def low(self):
        return self._low / 10 ** self.decimal

    @low.setter
    def low(self, value):
        self._low = value * (10 ** self.decimal)
        self.repaint()

    @property
    def high(self):
        return self._high / 10 ** self.decimal

    @high.setter
    def high(self, value):
        self._low = value * (10 ** self.decimal)
        self.repaint()

    def is_min(self):
        return self.min == self.low

    def is_max(self):
        return self.max == self.high

    def is_default(self):
        return self.is_min() and self.is_max()

    @property
    def range(self):
        return (
            None if self.is_min() else self.low,
            None if self.is_max() else self.high)

    def set_decimal(self, decimal):
        self.decimal = decimal
        self.low_changed.emit(self.low)
        self.high_changed.emit(self.high)
        self.repaint()

    def set_range(self, low, high):
        low *= 10 ** self.decimal
        high *= 10 ** self.decimal
        self._low = max((low, self._min))
        self._high = min((high, self._max))
        self.repaint()

    def set_full_range(self, minimum, maximum):
        self._min = minimum * (10 ** self.decimal)
        self._max = maximum * (10 ** self.decimal)
        self._low = max((self._low, self._min))
        self._high = min((self._high, self._max))
        self.repaint()

    def find_edit_mode(self, point):
        v = get_value_from_point(self, point)
        return 'left' if abs(v - self._low) < abs(v - self._high) else 'right'

    def change_value_from_point(self, point):
        value = get_value_from_point(self, point)
        if self._edit_mode == 'left':
            self._low = min((max((self._min, value)), self._high - 1))
            self.low_changed.emit(self.low)
        else:
            self._high = max((min((self._max, value)), self._low + 1))
            self.high_changed.emit(self.high)
        self.repaint()

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self._mousepressed = True
            self._edit_mode = self.find_edit_mode(event.pos())
            self.change_value_from_point(event.pos())

    def mouseReleaseEvent(self, event):
        self._mousepressed = False
        return super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not self._mousepressed:
            return
        self.change_value_from_point(event.pos())
        self.repaint()

    def paintEvent(self, _):
        painter = QtGui.QPainter(self)
        painter.setPen(QtGui.QColor(self.border_color))
        painter.setBrush(QtGui.QColor(self.background_color))
        painter.drawRect(self.rect())
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(QtGui.QColor(self.range_color))
        line1 = get_value_line(self, self.low)
        line2 = get_value_line(self, self.high)
        painter.drawRect(QtCore.QRect(line1.p1(), line2.p2()))
        painter.setBrush(QtGui.QColor(self.bracket_color))
        path = get_bracket_path(line1, 'left')
        painter.drawPath(path)
        path = get_bracket_path(line2, 'right')
        painter.drawPath(path)
        painter.end()


def get_value_line(slider, value):
    rect = slider.rect()
    horizontal_divisor = float(slider.max - slider.min) or 1
    horizontal_unit_size = rect.width() / horizontal_divisor
    left = (value - slider.min) * horizontal_unit_size
    minimum = QtCore.QPoint(left, rect.top())
    maximum = QtCore.QPoint(left, rect.bottom())
    return QtCore.QLine(minimum, maximum)


def get_bracket_path(line, direction):
    path = QtGui.QPainterPath()
    path.moveTo(line.p1())
    path.lineTo(line.p2())
    offset1 = +5 if direction == 'left' else -5
    offset2 = +1 if direction == 'left' else -1
    path.lineTo(line.p2().x() + offset1, line.p2().y())
    path.lineTo(line.p2().x() + offset2, line.p2().y() - abs(offset1))
    path.lineTo(line.p2().x() + offset2, line.p1().y() + abs(offset1))
    path.lineTo(line.p2().x() + offset1, line.p1().y() + abs(offset2))
    path.lineTo(line.p2().x() + offset1, line.p1().y())
    path.moveTo(line.p1())
    return path


def get_mark_lines(slider, marks):
    return [get_value_line(slider, mark) for mark in marks]


def get_value_from_point(slider, point):
    if slider._max - slider._min <= 1:
        return slider.min
    horizontal_divisor = float(slider._max - slider._min) or 1
    horizontal_unit_size = slider.rect().width() / horizontal_divisor
    value = 0
    x = 0
    while x < point.x():
        value += 1
        x += horizontal_unit_size
    # If pointer is closer to previous value, we set the value to previous one.
    if (x - point.x() > point.x() - (x - horizontal_unit_size)):
        value -= 1
    return value + slider._min


if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    slider = RangeSlider()
    slider.set_decimal(2)
    slider.set_full_range(0, 200)
    slider.set_range(0, 200)
    slider.show()
    app.exec_()
