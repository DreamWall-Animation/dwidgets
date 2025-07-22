import tempfile
from PySide2 import QtWidgets, QtGui, QtCore


DEFAULT_BACKGROUND_COLOR = QtGui.QColor(0, 0, 0, 40)
DEFAULT_BORDER_COLOR = QtCore.Qt.white
DEFAULT_TEXT_COLOR = QtCore.Qt.black
DEFAULT_CROSS_BACKGROUND_COLOR = QtCore.Qt.black
DEFAULT_CROSS_TEXT_COLOR = QtCore.Qt.white
DEFAULT_ITEM_SIZE = 60, 60
DEFAULT_ITEM_SPACING = 13
BORDER_WIDTH = 1.5
DELETER_RADIUS = 15
TEXT_HEIGHT_SQUARE = 15
MARGINS = 10, 10, 10, 10
MINIMUM_HEIGHT = 35


def _coordinate_builder(size, spacing, width):
    left = MARGINS[0]
    top = MARGINS[1]
    yield left, top
    while True:
        left += spacing + size[0]
        limit = left + size[0] + spacing + MARGINS[-1]
        if limit > width:
            left = MARGINS[0]
            top += size[1] + spacing
        yield left, top


class DropFilesArea(QtWidgets.QWidget):
    files_changed = QtCore.Signal()

    def __init__(
            self,
            background_color=None,
            border_color=None,
            text_color=None,
            item_size=None,
            item_spacing=None,
            cross_background_color=None,
            cross_text_color=None,
            supported_extensions=None,
            parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        supported_extensions = supported_extensions or []
        self.supported_extensions = [e.lower() for e in supported_extensions]
        color = cross_background_color or DEFAULT_CROSS_BACKGROUND_COLOR
        self.cross_background_color = color
        self.background_color = background_color or DEFAULT_BACKGROUND_COLOR
        self.cross_text_color = cross_text_color or DEFAULT_CROSS_TEXT_COLOR
        self.border_color = border_color or DEFAULT_BORDER_COLOR
        self.text_color = text_color or DEFAULT_TEXT_COLOR
        self.item_size = item_size or DEFAULT_ITEM_SIZE
        self.item_spacing = item_spacing or DEFAULT_ITEM_SPACING
        self.filepaths = []
        self.setAcceptDrops(True)
        self.hovered_index = None
        self.setMinimumSize(
            MARGINS[0] + MARGINS[2] + self.item_size[0] + self.item_spacing,
            MINIMUM_HEIGHT)

    def sizeHint(self):
        return QtCore.QSize(
            MARGINS[0] + MARGINS[2] +
            (3 * (self.item_size[0] + self.item_spacing)),
            MINIMUM_HEIGHT)

    def mouseMoveEvent(self, event):
        coordinates = _coordinate_builder(
            self.item_size, self.item_spacing, self.width())
        for i, filename in enumerate(self.filepaths):
            top, left = next(coordinates)
            rect = QtCore.QRect(top, left, *self.item_size)
            if rect.contains(event.pos()):
                self.hovered_index = i
                self.update()
                self.setToolTip(filename)
                return
        self.hovered_index = None
        self.setToolTip('')
        self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            if self.hovered_index is None:
                return
            del self.filepaths[self.hovered_index]
            self.files_changed.emit()
            self.update()
        if event.button() == QtCore.Qt.RightButton:
            self.call_context_menu(self.mapToGlobal(event.pos()))

    def call_context_menu(self, point):
        clipboard = QtWidgets.QApplication.clipboard()
        if not clipboard.image():
            return
        action = QtWidgets.QAction('Paste image', self)
        menu = QtWidgets.QMenu(self)
        menu.addAction(action)
        action = menu.exec_(point)
        if not action:
            return

        filepath = f'{tempfile.NamedTemporaryFile().name}.png'
        clipboard.image().save(filepath, format='png', quality=100)
        self.filepaths.append(filepath)
        self.files_changed.emit()
        self.update()

    def dragEnterEvent(self, event):
        mimedata = event.mimeData()
        if not mimedata.hasUrls():
            return False
        if not self.supported_extensions:
            return event.accept()

        accept = any(
            url.path().lower().endswith(tuple(self.supported_extensions))
            for url in mimedata.urls())
        if accept:
            event.accept()

    def dropEvent(self, event):
        self.filepaths.extend([
            url.toLocalFile() for url in event.mimeData().urls()
            if not self.supported_extensions or
            url.toLocalFile().lower().endswith(
                tuple(self.supported_extensions))])
        self.files_changed.emit()
        self.update()

    def clear(self, block_signal=False):
        self.filepaths = []
        if not block_signal:
            self.files_changed.emit()
        self.update()

    def set_colors(
            self,
            background_color=None,
            border_color=None,
            text_color=None):

        self.background_color = background_color or DEFAULT_BACKGROUND_COLOR
        self.border_color = border_color or DEFAULT_BORDER_COLOR
        self.text_color = text_color or DEFAULT_TEXT_COLOR
        self.update()

    def paintEvent(self, _):
        painter = QtGui.QPainter(self)
        painter.setBrush(QtGui.QColor(self.background_color))
        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
        pen = QtGui.QPen(QtGui.QColor(self.border_color))
        pen.setWidthF(BORDER_WIDTH)
        pen.setDashPattern([BORDER_WIDTH * 2, BORDER_WIDTH * 2.5])
        painter.setPen(pen)
        border_rect = QtCore.QRectF(
            self.rect().left() + (BORDER_WIDTH / 2),
            self.rect().top() + (BORDER_WIDTH / 2),
            self.rect().width() - BORDER_WIDTH,
            self.rect().height() - BORDER_WIDTH)
        painter.drawRoundedRect(border_rect, 4, 4)
        if not self.filepaths:
            painter.setPen(QtGui.QColor(self.text_color))
            painter.setBrush(QtCore.Qt.NoBrush)
            font = QtGui.QFont()
            font.setPixelSize(15)
            painter.setFont(font)
            text = 'Drop files here'
            painter.drawText(self.rect(), QtCore.Qt.AlignCenter, text)
            painter.end()
            w = MARGINS[0] + MARGINS[2] + self.item_size[0] + self.item_spacing
            self.setMinimumSize(w, MINIMUM_HEIGHT)
            return

        coordinates = _coordinate_builder(
            self.item_size, self.item_spacing, self.width())

        for i, filename in enumerate(self.filepaths):
            left, top = next(coordinates)
            rect = QtCore.QRectF(left, top, *self.item_size)
            info = QtCore.QFileInfo(filename)
            icon = QtWidgets.QFileIconProvider().icon(info)
            image = icon.pixmap(*self.item_size).toImage()
            painter.drawImage(icon_rect(rect), image)
            painter.setPen(QtGui.QColor(self.text_color))
            painter.setBrush(QtCore.Qt.NoBrush)
            font = QtGui.QFont()
            painter.setFont(font)
            align = QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
            painter.drawText(filename_rect(rect), align, filename)
            pen = QtGui.QPen(QtGui.QColor(self.border_color))
            pen.setStyle(QtCore.Qt.DotLine)
            painter.setPen(pen)
            painter.setBrush(QtCore.Qt.NoBrush)
            painter.drawRect(filename_rect(rect))
            if i == self.hovered_index:
                painter.setPen(QtCore.Qt.NoPen)
                color = QtGui.QColor(self.cross_background_color)
                color.setAlpha(125)
                painter.setBrush(color)
                drect = deleted_rect(rect)
                painter.drawEllipse(drect)
                painter.setPen(QtGui.QColor(self.text_color))
                painter.setBrush(QtCore.Qt.NoBrush)
                font = QtGui.QFont()
                font.setBold(True)
                font.setPixelSize(20)
                painter.setFont(font)
                painter.drawText(drect, QtCore.Qt.AlignCenter, 'X')
        self.setMinimumHeight(rect.bottom() + MARGINS[3])
        painter.end()


def deleted_rect(rect):
    center = rect.center()
    return QtCore.QRect(
        center.x() - DELETER_RADIUS,
        center.y() - DELETER_RADIUS,
        DELETER_RADIUS * 2,
        DELETER_RADIUS * 2)


def icon_rect(rect):
    return QtCore.QRectF(
        rect.left() + (TEXT_HEIGHT_SQUARE / 2),
        rect.top(), rect.width() - TEXT_HEIGHT_SQUARE,
        rect.height() - TEXT_HEIGHT_SQUARE)


def filename_rect(rect):
    return QtCore.QRect(
        rect.left(), rect.bottom() - TEXT_HEIGHT_SQUARE,
        rect.width(), TEXT_HEIGHT_SQUARE)


if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    w = DropFilesArea(
        border_color='#555555',
        background_color='#333333',
        text_color='#CCCCCC')
    w.show()
    app.exec_()
