import datetime
from PySide2 import QtWidgets, QtCore, QtGui
from PySide2.QtCore import Qt


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


class DatePickerButton(QtWidgets.QPushButton):
    date_changed = QtCore.Signal()

    def __init__(self, label, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.default_label = label
        self.setText(f' {self.default_label} (off) ')
        self.clicked.connect(self.pop)

        self.first_date = None
        self.last_date = None

        # Menu
        self.dates_menu = QtWidgets.QMenu()
        self.calendar = QtWidgets.QCalendarWidget()
        cancel_button = QtWidgets.QPushButton(' Cancel ')
        cancel_button.clicked.connect(self.dates_menu.close)
        reset_button = QtWidgets.QPushButton(' Reset ')
        reset_button.clicked.connect(self.reset_dates)
        validate_button = QtWidgets.QPushButton(' Confirm ')
        validate_button.clicked.connect(self.set_dates)

        layout = QtWidgets.QVBoxLayout(self.dates_menu)

        layout.addWidget(self.calendar)

        buttons_layout = QtWidgets.QHBoxLayout()
        buttons_layout.addStretch()
        buttons_layout.addWidget(cancel_button)
        buttons_layout.addWidget(reset_button)
        buttons_layout.addWidget(validate_button)
        layout.addLayout(buttons_layout)

    def pop(self):
        self.dates_menu.popup(self.mapToGlobal(self.rect().bottomLeft()))

    def reset_dates(self):
        self.date = None
        self.setText(f' {self.default_label} (off) ')
        self.date_changed.emit()
        self.dates_menu.close()

    def set_dates(self):
        self.date = self.calendar.selectedDate().toPython()
        self.setText(f'{self.default_label} ({self.date:%d/%m/%Y})')
        self.date_changed.emit()
        self.dates_menu.close()

    @property
    def dates(self):
        return self.first_date, self.last_date

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
