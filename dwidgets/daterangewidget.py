from PySide2 import QtWidgets, QtCore
from PySide2.QtCore import Qt


class DateRangeFilterButton(QtWidgets.QPushButton):
    dates_changed = QtCore.Signal()

    def __init__(self, label, parent=None, **kwargs):
        super().__init__(parent=parent, **kwargs)

        self.default_label = label
        self.setText(f' {self.default_label} (off) ')
        self.clicked.connect(self.pop)

        self.first_date = None
        self.last_date = None

        # Menu
        self.dates_menu = QtWidgets.QMenu(self)
        self.cal_first = QtWidgets.QCalendarWidget()
        self.cal_last = QtWidgets.QCalendarWidget()
        cancel_button = QtWidgets.QPushButton(' Cancel ')
        cancel_button.clicked.connect(self.dates_menu.close)
        reset_button = QtWidgets.QPushButton(' Reset ')
        reset_button.clicked.connect(self.reset_dates)
        validate_button = QtWidgets.QPushButton(' Confirm ')
        validate_button.clicked.connect(self.confirm_dates)

        layout = QtWidgets.QVBoxLayout(self.dates_menu)

        cal_layout = QtWidgets.QHBoxLayout()
        cal_layout.addWidget(self.cal_first)
        cal_layout.addWidget(self.cal_last)
        layout.addLayout(cal_layout)

        buttons_layout = QtWidgets.QHBoxLayout()
        buttons_layout.addStretch()
        buttons_layout.addWidget(cancel_button)
        buttons_layout.addWidget(reset_button)
        buttons_layout.addWidget(validate_button)
        layout.addLayout(buttons_layout)

    def pop(self):
        self.dates_menu.popup(self.mapToGlobal(self.rect().bottomLeft()))

    def set_dates(self, first_date, last_date, update_calendars=True):
        if first_date == self.first_date and last_date == self.last_date:
            return
        self.first_date = first_date
        self.last_date = last_date
        if update_calendars:
            if first_date:
                self.cal_first.setSelectedDate(first_date)
            if last_date:
                self.cal_last.setSelectedDate(last_date)
        if first_date is None and last_date is None:
            label = f' {self.default_label} (off) '
        else:
            label = (
                f'{self.default_label} '
                f'({self.first_date:%d/%m/%Y} - {self.last_date:%d/%m/%Y})')
        self.setText(label)
        self.dates_changed.emit()
        self.dates_menu.close()

    def reset_dates(self):
        self.set_dates(None, None)

    def confirm_dates(self):
        self.set_dates(
            first_date=self.cal_first.selectedDate().toPython(),
            last_date=self.cal_last.selectedDate().toPython(),
            update_calendars=False)

    @property
    def dates(self):
        return self.first_date, self.last_date

    def mousePressEvent(self, event):
        if event.type() == QtCore.QEvent.MouseButtonPress:
            if event.button() == Qt.MiddleButton:
                self.reset_dates()
        return super().mousePressEvent(event)
