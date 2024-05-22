from PySide2 import QtWidgets, QtCore, QtGui

DEFAULT_PADDING = 5
DEFAULT_CELL_PADDING = 0
DEFAULT_SPACING = 3
DEFAULT_BG_COLOR = '#556699'
DEFAULT_CROSS_COLOR = '#7788AA'
DEFAULT_HOVER_CROSS_COLOR = '#99CCDD'
DEFAULT_TEXT_STYLE = (
    'font-size:15px; color: #dddddd; font-style:bold; justify-content: center')


class TagView(QtWidgets.QWidget):
    removed = QtCore.Signal(list)
    added = QtCore.Signal(list)

    def __init__(
            self,
            bg_color=None,
            cross_color=None,
            hover_cross_color=None,
            spacing=None):
        super().__init__()
        self.setMouseTracking(True)
        self._tags = []
        self._items = []
        self._texts = []
        self._textstyle = DEFAULT_TEXT_STYLE
        self._padding = DEFAULT_PADDING
        self._cell_padding = DEFAULT_CELL_PADDING
        self._spacing = spacing or DEFAULT_SPACING
        self._bg_color = bg_color or DEFAULT_BG_COLOR
        self._cross_color = cross_color or DEFAULT_CROSS_COLOR
        self._hover_cross_color = (
            hover_cross_color or DEFAULT_HOVER_CROSS_COLOR)
        self.left_clicked = False
        self.constrained_height = False

    def sizeHint(self):
        return QtCore.QSize(200, 60)

    @property
    def padding(self):
        return self._padding

    @padding.setter
    def padding(self, padding):
        self._padding = padding
        self.recompute_items()

    @property
    def cell_padding(self):
        return self._cell_padding

    @cell_padding.setter
    def cell_padding(self, cell_padding):
        self._cell_padding = cell_padding
        self.recompute_items()

    @property
    def spacing(self):
        return self._spacing

    @spacing.setter
    def spacing(self, spacing):
        self._spacing = spacing
        self.recompute_items()

    @property
    def style(self):
        return self._textstyle

    @style.setter
    def style(self, style):
        self._textstyle = style
        self.tags = self.tags

    @property
    def bg_color(self):
        return self._bg_color

    @bg_color.setter
    def bg_color(self, color):
        self._bg_color = color
        self.repaint()

    @property
    def cross_color(self):
        return self._cross_color

    @cross_color.setter
    def cross_color(self, color):
        self._cross_color = color
        self.repaint()

    @property
    def hover_cross_color(self):
        return self._hover_cross_color

    @hover_cross_color.setter
    def hover_cross_color(self, color):
        self._hover_cross_color = color
        self.repaint()

    def pop(self, index):
        removed_tag = self._tags.pop(index)
        self.tags = self._tags
        self.removed.emit([removed_tag])

    def append(self, tag):
        self._tags.append(tag)
        self.tags = self._tags
        self.added.emit([tag])

    def extend(self, tags):
        self._tags.extend(tags)
        self.tags = self._tags
        self.added.emit(tags)

    @property
    def tags(self):
        return self._tags

    @tags.setter
    def tags(self, tags):
        self._tags = list(tags)
        self._texts = [
            QtGui.QStaticText(f'<div style="{self.style}">{t}</div>')
            for t in self._tags]
        self.recompute_items()

    def recompute_items(self):
        rect = grow_rect(self.rect(), -self.padding)
        self._items = get_items(
            rect,
            self._texts,
            self.spacing,
            self.cell_padding)
        self.repaint()
        if self._items:
            height = self._items[-1][0].bottom() + self.padding
            if self.constrained_height:
                self.setFixedHeight(height)
            else:
                self.setMinimumHeight(height)

    def resizeEvent(self, _):
        self.recompute_items()

    def mouseMoveEvent(self, _):
        self.repaint()

    def mousePressEvent(self, event):
        self.left_clicked = event.button() == QtCore.Qt.LeftButton

    def mouseReleaseEvent(self, event):
        if event.button() != QtCore.Qt.LeftButton:
            return
        self.left_clicked = False
        for i, (_, _, rect) in enumerate(self._items):
            if rect.contains(event.pos()):
                self.pop(i)
                return

    def paintEvent(self, _):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        cursor = self.mapFromGlobal(QtGui.QCursor.pos())
        iterator = zip(self._texts, self._items)
        for t, (itemrect, textrect, crossrect) in iterator:
            painter.setPen(QtCore.Qt.transparent)
            roundness = itemrect.height() / 2
            painter.setBrush(QtGui.QColor(self._bg_color))
            painter.drawRoundedRect(itemrect, roundness, roundness)
            hover = crossrect.contains(cursor)
            if hover:
                color = self._hover_cross_color
            else:
                color = self._cross_color
            painter.setBrush(QtGui.QColor(color))
            crossrect = mult_rect(crossrect, 0.8)
            painter.drawEllipse(crossrect)
            x = textrect.center().x() - (t.size().width() / 2) + roundness * .7
            y = textrect.center().y() - (t.size().height() / 2)
            painter.drawStaticText(x, y, t)
            pen = QtGui.QPen(QtGui.QColor(self._bg_color))
            crossrect = mult_rect(crossrect, 0.5)
            pen.setWidthF(crossrect.height() * 0.3)
            painter.setPen(pen)
            painter.drawLine(crossrect.topLeft(), crossrect.bottomRight())
            painter.drawLine(crossrect.topRight(), crossrect.bottomLeft())
        painter.end()


def get_items(rect, statictexts, spacing, cell_padding):
    if not statictexts:
        return []

    item_text_cross_rects = []
    x, y = rect.left(), rect.top()
    height = statictexts[0].size().height() + (2 * cell_padding)

    for i, statictext in enumerate(statictexts):
        size = statictext.size()
        width = size.width() + height + (height / 2)

        if (x + width > rect.right()) and i:
            y += height + spacing
            x = rect.left()

        item = QtCore.QRect(
            x, y,
            width + 2 * cell_padding,
            height)

        text = QtCore.QRect(
            cell_padding + x,
            cell_padding + y,
            size.width(),
            size.height())

        cross = QtCore.QRect(
            item.right() - item.height(),
            item.top(),
            item.height(),
            item.height())

        item_text_cross_rects.append([item, text, cross])
        x += width + spacing + (2 * cell_padding)

    return item_text_cross_rects


def grow_rect(rect, value):
    if rect is None:
        return None
    return QtCore.QRectF(
        rect.left() - value,
        rect.top() - value,
        rect.width() + (value * 2),
        rect.height() + (value * 2))


def mult_rect(rect, value):
    if rect is None:
        return None
    width = rect.width() * value
    height = rect.height() * value
    left = rect.left() + ((rect.width() - width) / 2)
    top = rect.top() + ((rect.height() - height) / 2)
    return QtCore.QRectF(left, top, width, height)


if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    win = TagView()
    win.tags = (
        'peanuts', 'bourito', 'parapat', 'esmeraldaisthebestwomanever',
        'olivier', 'parapa', 'theipper')
    win.style = (
        'font-size:15px; color: #dddddd; font-style:bold;'
        'justify-content: center')
    win.show()
    app.exec_()
