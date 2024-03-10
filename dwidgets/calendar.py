import datetime
from functools import partial

from PySide2 import QtWidgets, QtCore, QtGui
from PySide2.QtCore import Qt

from dwidgets.qtutils import move_widget_in_screen


class CalendarDialog(QtWidgets.QDialog):
    def __init__(self, date=None, confirm_label=None, parent=None):
        super().__init__(parent, QtCore.Qt.FramelessWindowHint)

        confirm_label = confirm_label or 'Set date'

        self.calendar = QtWidgets.QCalendarWidget()
        if date:
            self.calendar.setSelectedDate(date)

        self.ok = QtWidgets.QPushButton(confirm_label)
        self.ok.released.connect(self.accept)
        self.cancel = QtWidgets.QPushButton('Cancel')
        self.cancel.released.connect(self.reject)

        self.buttons = QtWidgets.QHBoxLayout()
        self.buttons.setContentsMargins(0, 0, 0, 0)
        self.buttons.setSpacing(0)
        self.buttons.addWidget(self.ok)
        self.buttons.addWidget(self.cancel)

        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        self.layout.addWidget(self.calendar)
        self.layout.addLayout(self.buttons)

    @property
    def date(self):
        return self.calendar.selectedDate()

    def showEvent(self, event) -> None:
        move_widget_in_screen(self)
        return super().showEvent(event)


class DatePickerButton(QtWidgets.QPushButton):
    date_changed = QtCore.Signal()

    def __init__(self, label, time=False, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.default_label = label
        self.setText(f' {self.default_label} (off) ')
        self.clicked.connect(self.pop)
        self.displaytime = time
        self.date = None
        self.first_date = None
        self.last_date = None

        # Menu
        self.dates_menu = QtWidgets.QMenu()
        self.calendar = QtWidgets.QCalendarWidget()
        self.time = QtWidgets.QTimeEdit()

        cancel_button = QtWidgets.QPushButton(' Cancel ')
        cancel_button.clicked.connect(self.dates_menu.close)
        reset_button = QtWidgets.QPushButton(' Reset ')
        reset_button.clicked.connect(self.reset_dates)
        validate_button = QtWidgets.QPushButton(' Confirm ')
        validate_button.clicked.connect(self.set_dates)

        buttons_layout = QtWidgets.QHBoxLayout()
        buttons_layout.addStretch()
        buttons_layout.addWidget(cancel_button)
        buttons_layout.addWidget(reset_button)
        buttons_layout.addWidget(validate_button)

        layout = QtWidgets.QVBoxLayout(self.dates_menu)
        layout.addWidget(self.calendar)
        if self.displaytime:
            layout.addWidget(self.time)
        layout.addLayout(buttons_layout)

    def pop(self):
        self.dates_menu.popup(self.mapToGlobal(self.rect().bottomLeft()))
        move_widget_in_screen(self.dates_menu)

    def reset_dates(self):
        self.date = None
        self.setText(f' {self.default_label} (off) ')
        self.date_changed.emit()
        self.dates_menu.close()

    def set_dates(self):
        self.date = self.calendar.selectedDate().toPython()
        if self.displaytime:
            time = f'{self.datetime:%d/%m/%Y %Hh%M}'
        else:
            time = f'{self.date:%d/%m/%Y}'
        self.setText(f'{self.default_label} ({time})')
        self.date_changed.emit()
        self.dates_menu.close()

    @property
    def dates(self):
        return self.first_date, self.last_date

    @property
    def datetime(self):
        if not self.date:
            return None
        return datetime.datetime(
            self.date.year, self.date.month, self.date.day,
            self.time.time().hour(), self.time.time().minute())

    def mousePressEvent(self, event):
        if event.type() == QtCore.QEvent.MouseButtonPress:
            if event.button() == Qt.MiddleButton:
                self.reset_dates()
        return super().mousePressEvent(event)


def date_prompt(
        parent=None, start_date=None, position=None, confirm_label=None):
    if not start_date:
        start_date = datetime.date.today()
    dialog = CalendarDialog(
        date=start_date, parent=parent, confirm_label=confirm_label)
    if not position:
        position = QtGui.QCursor().pos()
    dialog.move(position)
    if not dialog.exec():
        return
    return dialog.date.toPython()


class MonthSelector(QtWidgets.QWidget):
    month_selected = QtCore.Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.date = datetime.datetime.today().date().replace(day=1)
        self.prev = QtWidgets.QPushButton('◀')
        self.prev.released.connect(partial(self.set_next, True))
        self.current_month = QtWidgets.QPushButton(f'{self.date:%B %Y}')
        self.current_month.released.connect(self.select_month)
        self.current_month.setFixedWidth(150)
        self.next = QtWidgets.QPushButton('▶')
        self.next.released.connect(self.set_next)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.prev)
        layout.addWidget(self.current_month)
        layout.addWidget(self.next)

    def set_next(self, prev=False):
        if prev:
            first = self.date.replace(day=1)
            next_month = first - datetime.timedelta(days=1)
        else:
            next_month = self.date.replace(day=28) + datetime.timedelta(days=4)
        self.set_date(next_month.replace(day=1))

    def get_last_day(self):
        date = self.date.replace(day=28) + datetime.timedelta(days=4)
        return date.replace(day=1) - datetime.timedelta(days=1)

    def set_date(self, date):
        self.date = date
        self.current_month.setText(f'{self.date:%B %Y}')
        self.month_selected.emit(self.date)

    def select_month(self):
        dialog = CalendarDialog(self.date)
        if dialog.exec_():
            self.set_date(dialog.date.toPython())


class WeekSelector(QtWidgets.QWidget):
    next_week_pressed = QtCore.Signal()
    previous_week_pressed = QtCore.Signal()
    select_week_pressed = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        font = QtGui.QFont()
        font.setPixelSize(15)
        font.setBold(True)

        self.previous_week = QtWidgets.QPushButton(
            '◀', styleSheet='font-size: 32px')
        self.previous_week.setFixedSize(30, 30)
        self.previous_week.released.connect(self.previous_week_pressed.emit)
        self.next_week = QtWidgets.QPushButton(
            '▶', styleSheet='font-size: 32px')
        self.next_week.setFixedSize(30, 30)
        self.next_week.released.connect(self.next_week_pressed.emit)
        self.week_selector = QtWidgets.QPushButton('Select Date')
        self.week_selector.setFont(font)
        self.week_selector.released.connect(self.select_week_pressed.emit)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.previous_week)
        layout.addWidget(self.week_selector)
        layout.addWidget(self.next_week)
