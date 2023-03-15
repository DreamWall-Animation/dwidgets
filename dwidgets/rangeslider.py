from PySide2 import QtWidgets, QtCore, QtGui


DEFAULT_MIN = 0
DEFAULT_MAX = 100


class RangeSlider(QtWidgets.QWidget):
    range_changed = QtCore.Signal(int, int)

    def __init__(self, parent=None):
        super().__init__(parent=parent)
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
        self.set_range = self.bar.set_range
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

    def set_low(self, value):
        self.low.setText(str(value))

    def set_high(self, value):
        self.high.setText(str(value))

    def range_edited(self, *_):
        minimum = int(self.low.text())
        maximum = int(self.high.text())
        self.range_changed(minimum, maximum)
        self.bar.low = minimum
        self.bar.high = maximum
        self.bar.repaint()


class RangeSliderBar(QtWidgets.QWidget):
    low_changed = QtCore.Signal(int)
    high_changed = QtCore.Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.min = DEFAULT_MIN
        self.max = DEFAULT_MAX
        self.low = self.min
        self.high = self.max
        self._edit_mode = None
        self._mousepressed = False

        self.bracket_color = '#000000'
        self.range_color = '#777777'
        self.background_color = '#666666'
        self.border_color = '#111111'

    def sizeHint(self):
        return QtCore.QSize(400, 25)

    def is_min(self):
        return self.min == self.low

    def is_max(self):
        return self.max == self.high

    def is_default(self):
        return self.is_min() and self.is_max()

    @property
    def range(self):
        return self.low, self.high

    def set_range(self, low, high):
        self.low = max((low, self.min))
        self.hight = min((high, self.max))
        self.repaint()

    def set_full_range(self, minimum, maximum):
        self.min = minimum
        self.max = maximum
        self.low = max((self.low, minimum))
        self.high = min((self.high, maximum))
        self.repaint()

    def find_edit_mode(self, point):
        v = get_value_from_point(self, point)
        return 'left' if abs(v - self.low) < abs(v - self.max) else 'right'

    def change_value_from_point(self, point):
        value = get_value_from_point(self, point)
        print(value)
        if self._edit_mode == 'left':
            self.low = min((max((self.min, value)), self.high - 1))
            self.low_changed.emit(self.low)
        else:
            self.high = max((min((self.max, value)), self.low + 1))
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
    if slider.max - slider.min <= 1:
        return slider.min
    horizontal_divisor = float(slider.max - slider.min) or 1
    horizontal_unit_size = slider.rect().width() / horizontal_divisor
    value = 0
    x = 0
    while x < point.x():
        value += 1
        x += horizontal_unit_size
    # If pointer is closer to previous value, we set the value to previous one.
    if (x - point.x() > point.x() - (x - horizontal_unit_size)):
        value -= 1
    return value + slider.min


if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    slider = RangeSlider()
    slider.show()
    app.exec_()
