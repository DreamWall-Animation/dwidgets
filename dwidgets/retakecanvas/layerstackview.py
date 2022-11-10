
from PySide2 import QtWidgets, QtCore, QtGui
from dwidgets.retakecanvas.qtutils import pixmap


class LayerStackView(QtWidgets.QWidget):
    ITEM_HEIGHT = 30
    PADDING = 10

    def __init__(self, layerstack, parent=None):
        super().__init__(parent)
        self.layerstack = layerstack
        self.setMinimumWidth(200)
        self.visibility_pixmap = pixmap('visibility.png')
        self.current_item_pixmap = pixmap('current.png')
        self.opacity_bg_pixmap = pixmap('opacity1.png')
        self.opacity_fg_pixmap = pixmap('opacity2.png')
        self.locker_open_pixmap = pixmap('locker2.png')
        self.locker_closed_pixmap = pixmap('locker1.png')

        self.handle_mode = None
        self.handle_index = None
        self.buffer_state = None

    def set_layerstack(self, layerstack):
        self.layerstack = layerstack
        self.repaint()

    def mousePressEvent(self, event):
        if event.button() != QtCore.Qt.LeftButton:
            return
        mode, index = self.get_handle_infos(event.pos())
        self.handle_mode = mode
        self.handle_index = index
        if mode == 'visibility':
            self.buffer_state = not self.layerstack.visibilities[index]
            self.layerstack.visibilities[index] = self.buffer_state
        if mode == 'lock':
            self.buffer_state = not self.layerstack.locks[index]
            self.layerstack.locks[index] = self.buffer_state
        self.repaint()

    def mouseMoveEvent(self, event):
        mode, index = self.get_handle_infos(event.pos())
        if self.handle_mode == 'visibility' and mode == 'visibility':
            self.layerstack.visibilities[index] = self.buffer_state
            self.repaint()
            return
        if self.handle_mode == 'lock' and mode == 'lock':
            self.layerstack.locks[index] = self.buffer_state
            self.repaint()

    def mouseReleaseEvent(self, event):
        if event.button() != QtCore.Qt.LeftButton:
            return
        if not self.handle_mode or not self.handle_index is not None:
            return
        mode, index = self.get_handle_infos(event.pos())
        modes = 'current', 'reorder'
        if self.handle_mode in modes and index == self.handle_index:
            self.layerstack.current_index = index
            self.repaint()
            return

    def get_handle_infos(self, pos):
        for index, row in enumerate(range(len(self.layerstack) - 1, -1, -1)):
            if self.current_item_rect(row).contains(pos):
                return 'current', index
            if self.visibility_rect(row).contains(pos):
                return 'visibility', index
            if self.lock_rect(row).contains(pos):
                return 'lock', index
            if self.text_rect(row).contains(pos):
                return 'reorder', index
            if self.opacity_rect(row).contains(pos):
                return 'opacity', index
        return None, None

    def sizeHint(self):
        height = self.ITEM_HEIGHT * len(self.layerstack) + (2 * self.PADDING)
        height = max((30, height))
        return QtCore.QSize(300, height)

    def resizeEvent(self, event):
        width = max(event.size().width(), self.sizeHint().width())
        self.setFixedHeight(self.sizeHint().height())
        return super().resizeEvent(event)

    def update_size(self):
        self.setFixedHeight(self.sizeHint().height())

    def rects(self):
        height = self.ITEM_HEIGHT
        return [
            QtCore.QRect(0, (height * i) + self.PADDING, self.width(), height)
            for i in range(len(self.layerstack))]

    def button_rect(self, row, section=0, fromleft=True):
        height = self.ITEM_HEIGHT
        top = (height * row) + self.PADDING
        if fromleft:
            left = height * section
            return QtCore.QRect(left, top, height, height)
        right = self.width() - (height * section)
        left = right - height
        return QtCore.QRect(left, top, height, height)

    def current_item_rect(self, row):
        return self.button_rect(row, 0)

    def lock_rect(self, row):
        return self.button_rect(row, 2)

    def visibility_rect(self, row):
        return self.button_rect(row, 1)

    def opacity_rect(self, row):
        return self.button_rect(row, fromleft=False)

    def text_rect(self, row):
        rect_left = self.button_rect(row, 2)
        rect_right = self.button_rect(row, fromleft=False)
        left = rect_left.right()
        top = rect_left.top()
        width = self.width() - left - self.ITEM_HEIGHT
        return QtCore.QRect(left, top, width, self.ITEM_HEIGHT)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        iterator = enumerate(zip((reversed(self.rects())), self.layerstack))
        painter.setPen(QtCore.Qt.transparent)
        color = QtGui.QColor(QtCore.Qt.black)
        color.setAlpha(25)
        painter.setBrush(color)
        painter.drawRoundedRect(event.rect(), self.PADDING, self.PADDING)
        for i, (rect, (layer, name, lock, visible, opacity)) in iterator:
            row = len(self.layerstack) - i - 1
            # Draw alternate row.
            if row % 2 == 0:
                painter.setPen(QtCore.Qt.transparent)
                color = QtGui.QColor(QtCore.Qt.white)
                color.setAlpha(15)
                painter.setBrush(color)
                painter.drawRect(rect)
            # Draw current index.
            if i == self.layerstack.current_index:
                background_color = QtGui.QColor(QtCore.Qt.yellow)
                background_color.setAlpha(35)
                painter.setBrush(background_color)
                painter.setPen(QtCore.Qt.transparent)
                painter.drawRect(rect)
                painter.setBrush(QtCore.Qt.transparent)
                cellrect = grow_rect(self.current_item_rect(row), -3).toRect()
                painter.drawPixmap(cellrect, self.current_item_pixmap)
            # Draw draw visible.
            cellrect = grow_rect(self.visibility_rect(row), -3).toRect()
            painter.setPen(QtCore.Qt.black)
            color = QtGui.QColor(QtCore.Qt.black)
            color.setAlpha(33)
            painter.setBrush(color)
            painter.drawRoundedRect(cellrect, 4, 4)
            if visible:
                cellrect = grow_rect(cellrect, -3).toRect()
                painter.setPen(QtCore.Qt.transparent)
                painter.setBrush(QtCore.Qt.transparent)
                painter.drawPixmap(cellrect, self.visibility_pixmap)
            # Draw draw locker.
            cellrect = grow_rect(self.lock_rect(row), -3).toRect()
            painter.setPen(QtCore.Qt.black)
            color = QtGui.QColor(QtCore.Qt.black)
            color.setAlpha(33)
            painter.setBrush(color)
            painter.drawRoundedRect(cellrect, 4, 4)
            painter.setPen(QtCore.Qt.black)
            px = self.locker_closed_pixmap if lock else self.locker_open_pixmap
            painter.drawPixmap(cellrect, px)
            # Draw opacity.
            cellrect = grow_rect(self.opacity_rect(row), -6).toRect()
            painter.drawPixmap(cellrect, self.opacity_bg_pixmap)
            painter.setOpacity(opacity / 255)
            painter.drawPixmap(cellrect, self.opacity_fg_pixmap)
            painter.setOpacity(1)
            # Draw text
            oldmode = painter.compositionMode()
            mode = QtGui.QPainter.CompositionMode_Difference
            painter.setCompositionMode(mode)
            painter.setPen(QtCore.Qt.white)
            painter.setBrush(QtCore.Qt.transparent)
            option = QtGui.QTextOption()
            option.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
            rect = self.text_rect(row)
            rect.setLeft(rect.left() + 5)
            painter.drawText(rect, name, option)
            painter.setCompositionMode(oldmode)
        painter.end()


def grow_rect(rect, value):
    if rect is None:
        return None
    return QtCore.QRectF(
        rect.left() - value,
        rect.top() - value,
        rect.width() + (value * 2),
        rect.height() + (value * 2))