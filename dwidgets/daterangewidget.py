from PySide2 import QtWidgets, QtCore
from PySide2.QtCore import Qt


class DateRangeFilterButton(QtWidgets.QPushButton):
    dates_changed = QtCore.Signal()

    def __init__(self, label, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.default_label = label
        self.setText(f' {self.default_label} (off) ')
        self.clicked.connect(self.pop)

        self.first_date = None
        self.last_date = None

        # Menu
        self.dates_menu = QtWidgets.QMenu()
        self.cal_first = QtWidgets.QCalendarWidget()
        self.cal_last = QtWidgets.QCalendarWidget()
        cancel_button = QtWidgets.QPushButton(' Cancel ')
        cancel_button.clicked.connect(self.dates_menu.close)
        reset_button = QtWidgets.QPushButton(' Reset ')
        reset_button.clicked.connect(self.reset_dates)
        validate_button = QtWidgets.QPushButton(' Confirm ')
        validate_button.clicked.connect(self.set_dates)

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

    def reset_dates(self):
        self.first_date = None
        self.last_date = None
        self.setText(f' {self.default_label} (off) ')
        self.dates_changed.emit()
        self.dates_menu.close()

    def set_dates(self):
        self.first_date = self.cal_first.selectedDate().toPython()
        self.last_date = self.cal_last.selectedDate().toPython()
        self.setText(
            f'{self.default_label} '
            f'({self.first_date:%d/%m/%Y} - {self.last_date:%d/%m/%Y})')
        self.dates_changed.emit()
        self.dates_menu.close()

    @property
    def dates(self):
        return self.first_date, self.last_date

    def mousePressEvent(self, event):
        if event.type() == QtCore.QEvent.MouseButtonPress:
            if event.button() == Qt.MiddleButton:
                self.reset_dates()
        return super().mousePressEvent(event)
