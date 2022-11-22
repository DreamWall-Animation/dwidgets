
import os
from dwidgets.retakecanvas.dialog import OpacityDialog, RenameDialog
from dwidgets.retakecanvas.geometry import grow_rect
from dwidgets.retakecanvas.qtutils import pixmap
from dwidgets.retakecanvas.shapes import Bitmap
from PySide2 import QtCore, QtGui, QtWidgets


class LayerStackView(QtWidgets.QWidget):
    ITEM_HEIGHT = 30
    PADDING = 10

    def __init__(self, model, parent=None):
        super().__init__(parent)
        self.model = model
        self.layerstack = model.layerstack
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
        self.dragging = False

        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            return event.accept()

    def dropEvent(self, event):
        paths = [
            os.path.expandvars(url.path())
            for url in event.mimeData().urls()]
        if paths:
            self.add_layers_from_paths(paths)

    def add_layers_from_paths(self, paths):
        images = [QtGui.QImage(p.strip('/\\')) for p in paths]
        images = [image for image in images if not image.isNull()]
        for image in images:
            size = image.size()
            rect = QtCore.QRectF(0, 0, size.width(), size.height())
            self.model.add_layer(undo=False, name="Imported image")
            self.model.add_shape(Bitmap(image, rect))
        self.model.add_undo_state()
        self.update_size()
        self.repaint()

    def set_model(self, model):
        self.model = model
        self.layerstack = model.layerstack
        self.repaint()

    def mouseDoubleClickEvent(self, event):
        if event.button() != QtCore.Qt.LeftButton:
            return
        mode, index = self.get_handle_infos(event.pos())
        if mode == 'drag':
            dialog = RenameDialog(self.layerstack, index, self)
            row = self.row(index)
            rect = self.text_rect(row)
            point = self.mapToGlobal(rect.topLeft())
            dialog.exec_(point, rect.size())

    def row(self, index):
        return len(self.layerstack) - index - 1

    def mousePressEvent(self, event):
        if event.button() != QtCore.Qt.LeftButton:
            return
        mode, index = self.get_handle_infos(event.pos())
        self.handle_mode = mode
        self.handle_index = index
        if mode == 'visibility':
            self.buffer_state = not self.layerstack.visibilities[index]
            self.layerstack.visibilities[index] = self.buffer_state
        elif mode == 'lock':
            self.buffer_state = not self.layerstack.locks[index]
            self.layerstack.locks[index] = self.buffer_state
        elif mode == 'opacity':
            dialog = OpacityDialog(self.layerstack, index, self)
            row = self.row(index)
            rect = self.opacity_rect(row)
            point = self.mapToGlobal(rect.center())
            result = dialog.exec_(point, rect.size())
            if result != QtWidgets.QDialog.Accepted:
                return
        elif self.handle_mode == 'drag':
            self.layerstack.current_index = self.handle_index
        self.repaint()

    def mouseMoveEvent(self, event):
        mode, index = self.get_handle_infos(event.pos())
        if self.handle_mode == 'visibility' and mode == 'visibility':
            self.layerstack.visibilities[index] = self.buffer_state
        elif self.handle_mode == 'lock' and mode == 'lock':
            self.layerstack.locks[index] = self.buffer_state
        elif self.handle_mode == 'drag' and self.handle_index is not None:
            self.dragging = True
        self.repaint()

    def release(self):
        self.handle_mode = None
        self.handle_index = None
        self.dragging = False
        self.repaint()

    def mouseReleaseEvent(self, event):
        if event.button() != QtCore.Qt.LeftButton:
            return False
        if not self.handle_mode or self.handle_index is None:
            self.release()
            return False
        _, index = self.get_handle_infos(event.pos())
        if self.handle_mode == 'current' and index == self.handle_index:
            self.layerstack.current_index = index
            self.release()
            return True
        if self.handle_mode == 'drag':
            self.drop()
            self.release()
            return True
        self.release()
        return False

    def get_handle_infos(self, pos):
        for index, row in enumerate(range(len(self.layerstack) - 1, -1, -1)):
            if self.current_item_rect(row).contains(pos):
                return 'current', index
            if self.visibility_rect(row).contains(pos):
                return 'visibility', index
            if self.lock_rect(row).contains(pos):
                return 'lock', index
            if self.text_rect(row).contains(pos):
                return 'drag', index
            if self.opacity_rect(row).contains(pos):
                return 'opacity', index
        return None, None

    def sizeHint(self):
        height = self.ITEM_HEIGHT * len(self.layerstack) + (2 * self.PADDING)
        height = max((30, height))
        return QtCore.QSize(300, height)

    def resizeEvent(self, event):
        self.setFixedHeight(self.sizeHint().height())
        return super().resizeEvent(event)

    def update_size(self):
        self.setFixedHeight(self.sizeHint().height())

    def rects(self):
        return [
            self.item_rect(i)
            for i in range(len(self.layerstack))]

    def item_rect(self, row):
        top = (self.ITEM_HEIGHT * row) + self.PADDING
        return QtCore.QRect(0, top, self.width(), self.ITEM_HEIGHT)

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
        left = rect_left.right()
        top = rect_left.top()
        width = self.width() - left - self.ITEM_HEIGHT
        return QtCore.QRect(left, top, width, self.ITEM_HEIGHT)

    def get_drop_infos(self):
        pos = self.mapFromGlobal(QtGui.QCursor.pos())
        _, index = self.get_handle_infos(pos)
        if index is None:
            return None, None, None
        rect = self.item_rect(self.row(index))
        action = 'before' if pos.y() > rect.center().y() else 'after'
        return action, index, rect

    def drop(self):
        action, index, _ = self.get_drop_infos()
        if None in (index, self.handle_index):
            return
        if index == self.handle_index:
            return
        if action == 'after':
            index += 1
        if index == self.handle_index:
            return
        if action == 'before' and index - 1 == self.handle_index:
            return
        self.model.move_layer(self.handle_index, index)

    def get_drop_line(self):
        action, _, rect = self.get_drop_infos()
        if not action:
            return
        if action == 'after':
            return QtCore.QLine(rect.topLeft(), rect.topRight())
        return QtCore.QLine(rect.bottomLeft(), rect.bottomRight())

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        iterator = enumerate(zip((reversed(self.rects())), self.layerstack))
        painter.setPen(QtCore.Qt.transparent)
        color = QtGui.QColor(QtCore.Qt.black)
        color.setAlpha(25)
        painter.setBrush(color)
        painter.drawRoundedRect(event.rect(), self.PADDING, self.PADDING)
        for i, (rect, (_, name, lock, visible, opacity)) in iterator:
            row = self.row(i)
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
            # Draw drag and drop
            if self.handle_mode == 'drag' and self.dragging:
                line = self.get_drop_line()
                if line:
                    pen = QtGui.QPen(QtCore.Qt.black)
                    pen.setWidth(3)
                    painter.setPen(pen)
                    painter.drawLine(line)
        painter.end()
