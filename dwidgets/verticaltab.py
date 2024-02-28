
from PySide2 import QtWidgets, QtGui, QtCore


GROUP_BOX_STYLE = """QGroupBox {
padding : 3px 3px 3px 3px;
border : 1px solid gray;
border-radius: 2px;
}"""


class VerticalTabWidget(QtWidgets.QWidget):
    def __init__(self, colors=None, parent=None):
        super().__init__(parent)
        self.tab_bar = TabBar(colors=colors, parent=self)
        self.tab_bar.index_changed.connect(self._set_index)

        self.widgets = []

        right_group = QtWidgets.QGroupBox()
        right_group.setStyleSheet(GROUP_BOX_STYLE)
        self.widgets_layout = QtWidgets.QVBoxLayout(right_group)
        self.widgets_layout.setContentsMargins(0, 0, 0, 0)

        tab_layout = QtWidgets.QVBoxLayout()
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.addWidget(self.tab_bar)
        tab_layout.addStretch(1)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(tab_layout)
        layout.setSpacing(0)
        layout.addWidget(right_group)

    def set_spacing(self, value):
        self.tab_bar.set_spacing(value)

    def current_widget(self):
        if not self.widgets:
            return
        return self.widgets[self.tab_bar.index]

    def current_index(self):
        return self.tab_bar.index

    def add_tab(self, widget, name):
        self.tab_bar.add_tab(name)
        self.widgets.append(widget)
        self.widgets_layout.addWidget(widget)

    def add_separator(self):
        self.tab_bar.add_separator()

    def add_section(self, name):
        self.tab_bar.add_section(name)

    def _set_index(self, index):
        print(index)
        for i, widget in enumerate(self.widgets):
            widget.setVisible(index == i)

    def showEvent(self, event):
        self._set_index(self.tab_bar.index)
        super().showEvent(event)


class TabBar(QtWidgets.QWidget):
    index_changed = QtCore.Signal(int)

    def __init__(self, colors=None, parent=None):
        super().__init__(parent)
        self.items = []
        self.index = 0
        self.spacing = 10
        self.label_height = 20
        self.button_height = 20
        self.colors = colors or self.get_application_colors()

    def mousePressEvent(self, event):
        top = 0
        i = 0
        for item in self.items:
            if item['type'] == 'separator':
                top += self.spacing
            if item['type'] == 'section':
                top += self.label_height
            if item['type'] == 'tab':
                rect = QtCore.QRect(0, top, self.width(), self.button_height)
                if rect.contains(event.pos()):
                    self.index = i
                    self.index_changed.emit(i)
                    self.repaint()
                    return
                top += self.button_height
                i += 1

    def sizeHint(self):
        return QtCore.QSize(200, 200)

    def get_application_colors(self):
        palette = QtWidgets.QApplication.palette()
        return {
            'unchecked_background': palette.color(QtGui.QPalette.Base),
            'checked_background': palette.color(QtGui.QPalette.Light),
            'text_color': palette.color(QtGui.QPalette.ButtonText),
            'label_color': palette.color(QtGui.QPalette.Mid),
            'border': palette.color(QtGui.QPalette.Mid)
        }

    def set_spacing(self, value):
        self.spacing = value
        self.update_size()

    def add_separator(self):
        self.items.append({'type': 'separator'})
        self.update_size()

    def add_section(self, label):
        self.items.append({'type': 'section', 'label': label})
        self.update_size()

    def add_tab(self, label):
        self.items.append({'type': 'tab', 'label': label})
        self.update_size()

    def update_size(self):
        bottom = 0
        width = 0
        for item in self.items:
            if item['type'] == 'separator':
                bottom += self.spacing
            if item['type'] == 'section':
                bottom += self.label_height
            if item['type'] == 'tab':
                bottom += self.button_height
                twidth = QtGui.QStaticText(item['label']).size().width() * 1.2
                width = max((width, twidth))
        if not width:
            width = self.sizeHint().width()
        if self.parent():
            bottom = max((bottom, self.parent().height()))
        self.setFixedSize(width, bottom)
        self.repaint()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        i = 0
        top = 0
        need_sepline = False
        alignment = int(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        for item in self.items:
            if item['type'] == 'separator':
                top += self.spacing
                need_sepline = False
            if item['type'] == 'section':
                painter.setPen(QtCore.Qt.NoPen)
                painter.setBrush(QtGui.QColor(self.colors['label_color']))
                rect = QtCore.QRect(
                    0, top, event.rect().width(), self.label_height)
                painter.drawRect(rect)
                font = QtGui.QFont()
                font.setBold(True)
                painter.setFont(font)
                painter.setBrush(QtGui.QBrush())
                painter.setPen(QtGui.QColor(self.colors['text_color']))
                text = f'{item["label"]}   '
                painter.drawText(rect, alignment, text)
                mode = QtGui.QPainter.CompositionMode_SourceOver
                painter.setCompositionMode(mode)
                top += self.label_height
                need_sepline = False
            if item['type'] == 'tab':
                checked = i == self.index
                color = (
                    'checked_background' if checked else
                    'unchecked_background')
                rect = QtCore.QRect(
                    0, top, event.rect().width(), self.button_height)
                painter.setPen(QtCore.Qt.NoPen)
                painter.setBrush(QtGui.QColor(self.colors[color]))
                painter.setPen(QtGui.QColor(self.colors['border']))
                if not checked:
                    if need_sepline:
                        painter.drawLine(
                            event.rect().width() * .15,
                            rect.top(),
                            event.rect().right(),
                            rect.top())
                    need_sepline = True
                else:
                    need_sepline = False
                    left = int(event.rect().width() * .05)
                    path = get_current_path(
                        QtCore.QRect(
                            left, top, (event.rect().width() - left) + 1,
                            self.button_height + 2))
                    painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
                    painter.drawPath(path)
                    painter.setRenderHint(QtGui.QPainter.Antialiasing, False)
                text = f'{item["label"]} '
                painter.setBrush(QtCore.Qt.NoBrush)
                painter.setPen(QtGui.QColor(self.colors['text_color']))
                painter.setFont(QtGui.QFont())
                painter.drawText(rect, alignment, text)
                top += self.button_height
                i += 1
        painter.end()


def get_current_path(rect):
    roundness = 4

    start = QtCore.QPoint(rect.right(), rect.top() - roundness)
    path = QtGui.QPainterPath()
    path.moveTo(start)

    point1 = QtCore.QPoint(rect.right(), rect.top() - (roundness / 2))
    point2 = QtCore.QPoint(rect.right() - (roundness / 2), rect.top())
    point3 = QtCore.QPoint(rect.right() - roundness, rect.top())
    path.cubicTo(point1, point2, point3)

    point = QtCore.QPoint(rect.left() + roundness, rect.top())
    path.lineTo(point)

    point1 = QtCore.QPoint(rect.left() + (roundness / 2), rect.top())
    point2 = QtCore.QPoint(rect.left(), rect.top() + (roundness / 2))
    point3 = QtCore.QPoint(rect.left(), rect.top() + roundness)
    path.cubicTo(point1, point2, point3)

    point = QtCore.QPoint(rect.left(), rect.bottom() - roundness)
    path.lineTo(point)

    point1 = QtCore.QPoint(rect.left(), rect.bottom() - (roundness / 2))
    point2 = QtCore.QPoint(rect.left() + (roundness / 2), rect.bottom())
    point3 = QtCore.QPoint(rect.left() + roundness, rect.bottom())
    path.cubicTo(point1, point2, point3)

    point = QtCore.QPoint(rect.right() - roundness, rect.bottom())
    path.lineTo(point)

    point1 = QtCore.QPoint(rect.right() - (roundness / 2), rect.bottom())
    point2 = QtCore.QPoint(rect.right(), rect.bottom() + (roundness / 2))
    point3 = QtCore.QPoint(rect.right(), rect.bottom() + roundness)
    path.cubicTo(point1, point2, point3)

    return path


if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    tab = VerticalTabWidget()
    tab.add_tab(QtWidgets.QTableWidget(), 'test')
    tab.add_section('putain de camion')
    tab.add_tab(QtWidgets.QCalendarWidget(), 'calendar')
    tab.show()
    app.exec_()
