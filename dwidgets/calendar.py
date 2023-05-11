import datetime
from PySide2 import QtWidgets, QtCore, QtGui


class CalendarDialog(QtWidgets.QDialog):

    def __init__(self, date, parent=None):
        super().__init__(parent, QtCore.Qt.FramelessWindowHint)
        self.calendar = QtWidgets.QCalendarWidget()
        self.calendar.setSelectedDate(date)

        self.ok = QtWidgets.QPushButton('Set date')
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


def date_prompt(parent=None, start_date=None, position=None):
    if not start_date:
        start_date = datetime.date.today()
    dialog = CalendarDialog(date=start_date, parent=parent)
    if not position:
        position = QtGui.QCursor().pos()
    dialog.move(position)
    if not dialog.exec():
        return
    return dialog.date.toPython()
