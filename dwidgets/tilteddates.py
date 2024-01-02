import datetime
from PySide2 import QtCore, QtWidgets, QtGui

DEFAULT_ROTATION_ANGLE = 90
DEFAULT_DISPLAY_DATE_FORMAT = '%d %A %y'
DEFAULT_SPACING = 15


class TiltedDates(QtWidgets.QWidget):
    """
    Widget to display list of dates with tilted text.
    """
    def __init__(self, dates, parent=None):
        """
        @dates: List[datetime]
        @parent: QtWidgets.QWidget

        Attributes:
            display_format: str
            angle: int
            spacing: Bool
            font: QFont

        Properties:
            dates: List[datetime]
        """
        super().__init__(parent)
        self._dates = dates
        self._current_date = None
        self.display_format = DEFAULT_DISPLAY_DATE_FORMAT
        self.angle = DEFAULT_ROTATION_ANGLE
        self.spacing = DEFAULT_SPACING
        self.font = QtGui.QFont()
        self.color = None
        self.current_color = None
        self.todays_color = None

    @property
    def dates(self):
        return self._dates

    @dates.setter
    def dates(self, dates):
        self._dates = dates
        self.repaint()

    @property
    def current_date(self):
        return self._current_date

    @current_date.setter
    def current_date(self, date):
        self._current_date = date
        self.repaint()

    def sizeHint(self):
        return QtCore.QSize(600, 600)

    def paintEvent(self, _):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setPen(QtCore.Qt.transparent)
        color = self.color or QtWidgets.QApplication.palette().text().color()
        today = (
            self.todays_color or
            QtWidgets.QApplication.palette().brightText().color())
        current = (
            self.current_color or
            QtWidgets.QApplication.palette().windowText().color())

        painter.translate(20, 100)
        for i, d in enumerate(self.dates):
            if d == self.current_date:
                painter.setBrush(current)
            elif d == datetime.date.today():
                painter.setBrush(today)
            else:
                painter.setBrush(color)
            path = QtGui.QPainterPath()
            text = d.strftime(self.display_format)
            point = QtCore.QPoint(0, 0)
            path.addText(point, self.font, text)
            transform = QtGui.QTransform()
            transform.rotate(self.angle)
            path = transform.map(path)
            path.translate(i * self.spacing, 0)
            painter.drawPath(path)
        painter.end()
