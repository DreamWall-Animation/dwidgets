import base64
import json
from PySide2 import QtWidgets, QtCore, QtGui
import random


DEFAULT_PADDING = 1.5
DEFAULT_GRADUATION = 20
BALLON_BACKGROUND_COLOR = 'yellow'
BALLON_FILLED_BORDER_COLOR = 'black'
BALLON_EMPTY_BORDER_COLOR = 'white'
BORDER_COLOR = 'darkorange'
GRADUATION_COLOR = 'white'
BUILTIN_COLORS = [
    "#77dd77",
    "#836953",
    "#89cff0",
    "#99c5c4",
    "#9adedb",
    "#aa9499",
    "#aaf0d1",
    "#b2fba5",
    "#b39eb5",
    "#bdb0d0",
    "#bee7a5",
    "#befd73",
    "#c1c6fc",
    "#c6a4a4",
    "#cb99c9",
    "#fdfd96",
    "#ff6961",
    "#ff694f",
    "#ff9899",
    "#ffb7ce",
    "#ca9bf7"
]


class WeightSlider(QtWidgets.QWidget):
    """
    The weight slider is a multi value slider to drive ratios of multiple
    elements. His data can be represented as 2 types:
        - ratios:
            List of numbers representing the absolute position of each index.
            This list has to be ascending. The last element of the list is
            always 1.0.
        - weights:
            List of numbers representing the value of each index. The sum of
            all weights must be 1.0
    """
    released = QtCore.Signal()

    def __init__(
            self,
            weights, colors=None, texts=None, data=None, comments=None,
            orientation=None, graduation=DEFAULT_GRADUATION, parent=None):
        """
        @weights: List[float]
            Sum of weight must be 1.0.
        @colors: List[str]|None,
            List of colors (hex code/color name)
            If None, colors will be automatically selection cycling list a
            predefined 'Pastel' hexadecimal colors.
        @texts: List[str]|None,
            Gives a text description for each items.
            Only affects vertical sliders which has the attribute
            'display_texts' set as True.
            Display a column on the left the display texts.
        @data: List[Any]|None.
            Give possibility to link any data to each value. data MUST be JSON
            serializable.
        @comments: List[str]|None,
            Gives an editable comment to each value.
            Only affects vertical sliders which has the attribute
            'display_comment' set as True.
        @orientation: QtCore.Qt.Direction|None
            Possible values: QtCore.Qt.Vertical or QtCore.Qt.Horizontal
            Default is Horizontal.
        @graduation: int
        @parent: QtWidgets.QWidget

        Attributes:
            border_color: str
            context_menu: QtWidgets.QMenu
            column_width: int
            display_borders: Bool
            display_texts: Bool
            graduation_color: str
            editable: Bool
            padding: int

        Properties:
            colors: List[str] (protected)
            horizontal: Bool (protected)
            texts: List[str] (protected)
            weights: List[float]

        Public methods:
            append_weight
            remove_weight
            set_values

        Signals:
            released

        """
        _args_sanity_check(weights, colors, texts, data, comments, graduation)

        super().__init__(parent=parent)
        self._colors = colors or BUILTIN_COLORS[:len(weights)]
        self._texts = texts or [''] * len(weights)
        self._comments = comments or [''] * len(weights)
        self._data = data or [None] * len(weights)
        self._orientation = orientation or QtCore.Qt.Horizontal
        self._graduation = max((graduation, len(weights)))
        self._rects = []
        self._handles = []
        self._graduation_points = []
        self._handeling_index = None
        self._drag_index = None
        self._pressed_button = None

        self.border_color = BORDER_COLOR
        self.ballon_background_color = BALLON_BACKGROUND_COLOR
        self.ballon_filled_border_color = BALLON_FILLED_BORDER_COLOR
        self.ballon_empty_border_color = BALLON_EMPTY_BORDER_COLOR
        self.column_width = None
        self.context_menu = None
        self.display_borders = False
        self.display_texts = False
        self.display_ballons = False
        self.editable = True
        self.graduation_color = GRADUATION_COLOR
        self.padding = DEFAULT_PADDING
        self.ratios = to_ratios(weights)

        self.setAcceptDrops(True)
        self.setMouseTracking(True)
        self.setMinimumSize(QtCore.QSize(35, 35))

    def _skip_if_not_editable(func):
        def decorator(self, *args, **kwargs):
            if not self.editable:
                return
            return func(self, *args, **kwargs)
        return decorator

    def sizeHint(self):
        if self._orientation == QtCore.Qt.Horizontal:
            return QtCore.QSize(600, 50)
        text_width = 200 if any(self._texts) else 0
        width = min([(self.column_width or 0) + text_width, 30])
        return QtCore.QSize(600, width)

    @property
    def colors(self):
        return self._colors[:]

    @property
    def texts(self):
        return self._texts[:]

    @property
    def data(self):
        return self._data[:]

    @property
    def comments(self):
        return self._comments[:]

    @property
    def horizontal(self):
        return self._orientation == QtCore.Qt.Horizontal

    @property
    def weights(self):
        return to_weights(self.ratios)

    @weights.setter
    def weigths(self, weights):
        _sanity_weights(weights, self._graduation)
        self.ratios = to_ratios(weights)
        self.update_geometries()

    def set_values(
            self, weights, colors=None, texts=None, data=None, comments=None,
            graduation=None):
        graduation = graduation or self._graduation
        _args_sanity_check(weights, colors, texts, data, comments, graduation)
        self.ratios = to_ratios(weights)
        self._colors = colors or BUILTIN_COLORS[:len(weights)]
        self._texts = texts or [''] * len(weights)
        self._data = data or [None] * len(weights)
        self._comments = comments or [''] * len(weights)
        self.update_geometries()
        self.repaint()

    @_skip_if_not_editable
    def append_weight(self, color=None, text=None, data=None, comment=None):
        try:
            color = color or next(
                c for c in BUILTIN_COLORS if c not in self._colors)
        except StopIteration:
            color = random_hexcolor()
        self._colors.append(color)
        self._texts.append(text or '')
        self._data.append(data)
        self._comments.append(comment)
        self.ratios = append_ratio(self.ratios, self._graduation)
        self.update_geometries()
        self.repaint()

    @_skip_if_not_editable
    def get_mouse_cursor(self, point):
        if point_hover_handles(self._handles, point, self.padding * 3) is None:
            return
        if self.horizontal:
            return QtCore.Qt.SizeHorCursor
        return QtCore.Qt.SizeVerCursor

    @_skip_if_not_editable
    def remove_weight(self, index):
        self._colors.pop(index)
        self._texts.pop(index)
        self._data.pop(index)
        self._comments.pop(index)
        self.ratios = remove_ratio(self.ratios, index, self._graduation)
        self.update_geometries()
        self.repaint()

    def update_geometries(self):
        if self.display_texts and not self.horizontal:
            column_width = self.column_width or self.width() / 4
        else:
            column_width = None

        self._rects = build_slider_rects(
            self.rect(), self.weights, self.horizontal, column_width)
        self._handles = build_slider_handles(
            self.rect(), self.weights, self.horizontal)
        self._graduation_points = build_slider_graduations(
            self.rect(), self.ratios, self._graduation, self.horizontal)

    def dragEnterEvent(self, event):
        if event.mimeData().hasColor() and event.mimeData().parent() != self:
            return event.accept()

    def dropEvent(self, event):
        self._pressed_button = None
        if not self.editable:
            return
        data = base64.b64decode(event.mimeData().data('data').toBase64())
        self.append_weight(
            color=event.mimeData().colorData(),
            text=event.mimeData().text(),
            data=json.loads(data) if data else None)
        return event.accept()

    def mousePressEvent(self, event):
        self._pressed_button = event.button()
        point = event.pos()
        width = self.padding * 3
        self._handeling_index = point_hover_handles(self._handles, point, width)
        if self._handeling_index is not None:
            return
        if self._orientation == QtCore.Qt.Vertical:
            rects = [
                QtCore.QRectF(0, r.top(), self.rect().width(), r.height())
                for r in self._rects]
        else:
            rects = self._rects
        self._drag_index = point_hover_rects(rects, point)

    def ballons_visible(self):
        return (
            self.weights and
            self.display_ballons and
            self._orientation == QtCore.Qt.Vertical and
            self.display_texts)

    def hovered_ballon(self, point):
        points = build_ballon_positions(self._rects, self.padding)
        rect = QtCore.QRect(
            0, self._rects[0].top(),
            self._rects[0].right() - self._rects[0].width(),
            self._rects[0].height())
        scale = compute_ballon_scale(rect)
        for i, p in enumerate(points):
            r = QtCore.QRectF(p.x(), p.y(), 90 * scale, 70 * scale)
            if r.contains(point):
                return i

    def mouseReleaseEvent(self, event):
        self._pressed_button = None
        if event.button() == QtCore.Qt.LeftButton:
            if self.ballons_visible():
                index = self.hovered_ballon(event.pos())
                if index is not None:
                    self.execute_comment_dialog(index, event.pos())
                    self.repaint()
                    return
            self.released.emit()
            self._handeling_index = None
            self.update_geometries()
            self.repaint()
        elif event.button() == QtCore.Qt.RightButton and self.context_menu:
            if not self.weights:
                return
            self.context_menu.exec(self.mapToGlobal(event.pos()))
        elif event.button() == QtCore.Qt.MiddleButton:
            if self._drag_index is not None:
                self.remove_weight(self._drag_index)
                self._drag_index = None

    def mouseMoveEvent(self, event):
        button = QtCore.Qt.LeftButton
        if self._drag_index is not None and self._pressed_button == button:
            mime = QtCore.QMimeData()
            mime.setColorData(self._colors[self._drag_index])
            mime.setText(self._texts[self._drag_index])
            data = self.data[self._drag_index]
            mime.setData('data', QtCore.QByteArray(json.dumps(data)))
            mime.setData('index', QtCore.QByteArray(bytes(self._drag_index)))
            mime.setParent(self)
            drag = QtGui.QDrag(self)
            drag.setMimeData(mime)
            drag.setHotSpot(event.pos().toPoint() - self.rect().topLeft())
            drag.exec(QtCore.Qt.CopyAction)
            self._drag_index = None
            return

        if self._handeling_index is None:
            cursor = self.get_mouse_cursor(event.pos())
            if cursor:
                QtWidgets.QApplication.setOverrideCursor(cursor)
            else:
                QtWidgets.QApplication.restoreOverrideCursor()
            return

        index = self._handeling_index
        ratio = to_ratio(self.rect(), event.pos(), self.horizontal)
        self.ratios = set_ratio_at(index, ratio, self.ratios)
        if self._graduation is not None:
            self.ratios = graduate(self.ratios, self._graduation)
        self.update_geometries()
        self.repaint()

    def leaveEvent(self, event):
        QtWidgets.QApplication.restoreOverrideCursor()

    def paintEvent(self, _):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        if self._rects:
            texts = self._texts if self.display_texts else [''] * len(self._colors)
            draw_slider(
                painter=painter,
                rect=self.rect(),
                rects=self._rects,
                colors=self._colors,
                texts=texts,
                padding=self.padding,
                draw_borders=self.display_borders,
                border_color=self.border_color,
                graduations=self._graduation_points,
                graduation_color=self.graduation_color,
                orientation=self._orientation)
            if self.ballons_visible():
                draw_ballons(
                    painter=painter,
                    rects=self._rects,
                    padding=self.padding,
                    fill_ballons=[bool(c) for c in self.comments],
                    background_color=self.ballon_background_color,
                    filled_border_color=self.ballon_filled_border_color,
                    empty_border_color=self.ballon_empty_border_color)
        else:
            draw_empty_slider(
                painter,
                self.rect(),
                self.padding,
                self.display_borders,
                self.border_color)
        painter.end()

    def resizeEvent(self, event):
        self.update_geometries()
        return super().resizeEvent(event)

    def execute_comment_dialog(self, index, position):
        dialog = CommentDialog(self.comments[index])
        dialog.move(self.mapToGlobal(position.toPoint()))
        if dialog.exec() != QtWidgets.QDialog.Accepted:
            return
        self._comments[index] = dialog.comment


class CommentDialog(QtWidgets.QDialog):
    def __init__(self, comment, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Set comment')
        self.text = QtWidgets.QPlainTextEdit()
        self.text.setPlainText(comment)
        self.ok = QtWidgets.QPushButton('Ok')
        self.ok.released.connect(self.accept)
        self.cancel = QtWidgets.QPushButton('Cancel')
        self.cancel.released.connect(self.reject)

        self.layout_btn = QtWidgets.QHBoxLayout()
        self.layout_btn.addWidget(self.ok)
        self.layout_btn.addWidget(self.cancel)

        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.addWidget(self.text)
        self.layout.addLayout(self.layout_btn)

    @property
    def comment(self):
        return self.text.toPlainText()


def _args_sanity_check(weights, colors, texts, data, comments, graduation):
    """This function assert the arguments to build a slider is valid"""
    _sanity_weights(weights, graduation)

    to_check = {
        'data': data, 'colors': colors, 'texts': texts, 'comments': comments}

    for name, elements in to_check.items():
        if elements is not None and len(elements) != len(weights):
            raise ValueError(
                f'Numbers of specified {name} does not '
                'matchs with number of weights')


def _sanity_weights(weights, graduation):
    """
    Ensure the number of weights is no longer than graduation and its sum is
    equal 1.0.
    """
    if not weights:
        return
    if graduation is not None and len(weights) > graduation:
        msg = 'Weights number cant be longer than graduation.'
        raise ValueError(msg)
    if to_ratios(weights)[-1] != 1.0 or sum(weights) != 1:
        raise ValueError('Sum of weigths has to be equal to 1.0')
    for weight in weights:
        if not (0 < weight <= 1):
            raise ValueError('Slider weight must be between 0 and 1')


def point_hover_handles(handles, point, width):
    for i, handle in enumerate(handles):
        if handle_to_rect(handle, width).contains(point):
            return i


def point_hover_rects(rects, point):
    for i, rect in enumerate(rects):
        if rect.contains(point):
            return i


def random_hexcolor():
    return '#%02X%02X%02X' % (
        random.randint(0, 255),
        random.randint(0, 255),
        random.randint(0, 255))


def handle_to_rect(line, width):
    left = line.p1().x() - width / 2
    top = line.p1().y() - width / 2
    right = line.p2().x() + width / 2
    bottom = line.p2().y() + width / 2
    rect = QtCore.QRectF()
    rect.setLeft(left)
    rect.setTop(top)
    rect.setRight(right)
    rect.setBottom(bottom)
    return rect


def draw_empty_slider(painter, rect, padding, draw_borders, border_color):
    brush = QtWidgets.QApplication.palette().dark()

    bgrect = build_rect_with_padding(rect, padding)
    painter.setBrush(brush)
    painter.drawRoundedRect(bgrect, 8, 8)
    if not draw_borders:
        return
    pen = QtGui.QPen(QtGui.QColor(border_color))
    pen.setWidthF(3)
    painter.setPen(pen)
    painter.setBrush(QtCore.Qt.transparent)
    painter.drawRoundedRect(build_rect_with_padding(rect, padding), 8, 8)


def get_comment_path(position, scale=1):
    """
    Build the shape of comment icon as QPainterPath.
     _____
    /     \
    \   __/
     |/

    """
    path = QtGui.QPainterPath(QtCore.QPointF(20, 50))
    path.setFillRule(QtCore.Qt.WindingFill)
    path.lineTo(20, 70)
    path.lineTo(30, 50)
    path.lineTo(80, 50)
    path.cubicTo(85, 50, 90, 45, 90, 40)
    path.lineTo(90, 10)
    path.cubicTo(90, 5, 85, 0, 80, 0)
    path.lineTo(10, 0)
    path.cubicTo(5, 0, 0, 5, 0, 10)
    path.lineTo(0, 40)
    path.cubicTo(0, 45, 5, 50, 10, 50)
    path.closeSubpath()

    path.moveTo(15, 12)
    path.lineTo(72, 12)
    path.moveTo(15, 24)
    path.lineTo(72, 24)
    path.moveTo(15, 36)
    path.lineTo(72, 36)

    transform = QtGui.QTransform()
    if position:
        transform.translate(position.x(), position.y())
    transform.scale(scale, scale)
    return transform.map(path)


def draw_slider(
        painter, rect, rects, colors, texts, padding, draw_borders,
        border_color, graduations, graduation_color, orientation):

    for r, color, text in zip(rects, colors, texts):
        painter.setPen(QtCore.Qt.transparent)
        qcolor = QtGui.QColor(color)
        if orientation == QtCore.Qt.Vertical:
            l, t, w, h = 0, r.top(), rect.width(), r.height()
            full_rect = QtCore.QRect(l, t, w, h)
            full_rect = build_rect_with_padding(full_rect, padding)
            qcolor.setAlpha(75)
            painter.setBrush(qcolor)
            painter.drawRoundedRect(full_rect, 8, 8)
            if text:
                painter.setPen(QtCore.Qt.black)
                painter.setBrush(QtCore.Qt.black)
                full_rect.setRight(full_rect.right() - r.width())
                text = QtGui.QStaticText(text)
                x = full_rect.center().x() - (text.size().width() / 2)
                y = full_rect.center().y() - (text.size().height() / 2)
                painter.drawStaticText(int(x), int(y), text)
        painter.setPen(QtCore.Qt.transparent)
        r = build_rect_with_padding(r, padding)
        brush = QtGui.QBrush(qcolor)
        qcolor.setAlpha(255)
        painter.setBrush(brush)
        painter.drawRoundedRect(r, 8, 8)

    if graduations:
        draw_graduation(
            painter, r, orientation, graduations, padding, graduation_color)

    if draw_borders:
        pen = QtGui.QPen(QtGui.QColor(border_color))
        pen.setWidthF(3)
        painter.setPen(pen)
        painter.setBrush(QtCore.Qt.transparent)
        painter.drawRoundedRect(build_rect_with_padding(rect, padding), 8, 8)


def draw_graduation(painter, rect, orientation, points, padding, color):
    color = QtGui.QColor(color)
    color.setAlpha(150)
    pen = QtGui.QPen(color)
    pen.setWidth(1)
    painter.setPen(pen)
    painter.setBrush(QtGui.QBrush(color))
    for point in points:
        if orientation == QtCore.Qt.Horizontal:
            start = QtCore.QPoint(point.x(), rect.top())
            end = QtCore.QPoint(point.x(), rect.height() + (padding * 2))
        else:
            start = QtCore.QPoint(rect.left(), point.y())
            end = QtCore.QPoint(rect.right(), point.y())
        painter.drawLine(start, end)


def draw_ballons(
        painter, rects, padding, fill_ballons, background_color,
        filled_border_color, empty_border_color):
    pen = QtGui.QPen()
    pen.setWidthF(2)
    pen.setJoinStyle(QtCore.Qt.MiterJoin)
    pen.setCapStyle(QtCore.Qt.RoundCap)
    centers = build_ballon_positions(rects, padding)
    rect = QtCore.QRect(
        0, rects[0].top(),
        rects[0].right() - rects[0].width(),
        rects[0].height())
    scale = compute_ballon_scale(rect)
    for center, filled in zip(centers, fill_ballons):
        if filled:
            bg_color = QtGui.QColor(background_color)
            bg_color.setAlpha(50)
            border_color = QtGui.QColor(filled_border_color)
        else:
            bg_color = QtGui.QColor(0, 0, 0, 0)
            border_color = QtGui.QColor(empty_border_color)
            border_color.setAlpha(50)

        painter.setBrush(bg_color)
        pen.setColor(border_color)
        painter.setPen(pen)
        painter.drawPath(get_comment_path(center, scale))


def compute_ballon_scale(rect):
    return 0.4 if rect.width() > 120 else (rect.width() / 120) * 0.4


def build_ballon_positions(rects, padding):
    rects = [QtCore.QRectF(0, r.top(), r.width(), r.height()) for r in rects]
    padding = QtCore.QPoint(padding * 6, padding * 6)
    return [rect.topLeft() + padding for rect in rects]


def build_slider_rects(rect, weights, horizontal=True, column_width=None):
    weight_in = 0
    weight_out = 0
    rects = []

    for weight in weights:
        weight_out += weight
        start = to_grade(rect, weight_in, horizontal)
        width = to_grade(rect, weight, horizontal)
        if horizontal:
            rects.append(QtCore.QRectF(start, 0, width, rect.height()))
        else:
            left = rect.right() - column_width if column_width else 0
            cwidth = column_width or rect.width()
            rects.append(QtCore.QRectF(left, start, cwidth, width))
        weight_in = weight_out

    return rects


def build_slider_handles(rect, weights, horizontal=True):
    total = 0
    lines = []

    for weight in weights[:-1]:
        total += weight
        grade = to_grade(rect, total, horizontal)
        if horizontal:
            start = QtCore.QPointF(grade, rect.top())
            end = QtCore.QPointF(grade, rect.bottom())
        else:
            start = QtCore.QPointF(rect.left(), grade)
            end = QtCore.QPointF(rect.right(), grade)
        lines.append(QtCore.QLineF(start, end))

    return lines


def build_slider_graduations(rect, ratios, graduation, horizontal=True):
    total = 0
    points = []
    step = 1 / graduation

    while total < 1:
        total += step
        if total in ratios:
            continue
        grade = to_grade(rect, total, horizontal)
        if horizontal:
            point = QtCore.QPointF(grade, rect.center().y())
        else:
            point = QtCore.QPointF(rect.center().x(), grade)
        points.append(point)

    return points


def build_rect_with_padding(rect, padding):
    padding = min([rect.width(), rect.height(), padding * 2])
    return QtCore.QRectF(
        rect.left() + padding,
        rect.top() + padding,
        rect.width() - (padding * 2),
        rect.height() - (padding * 2))


def to_ratio(rect, point, horizontal=True):
    """
    rect: QRect|QRect
    point: QPoint|QPointF
    return: ratio as float
    """
    grade = point.x() - rect.left() if horizontal else point.y() - rect.top()
    width = rect.width() if horizontal else rect.height()
    return min(max((grade / width), 0.0), 1.0)


def to_grade(rect, ratio, horizontal=True):
    """
    rect: QRect|QRect
    ratio: max(min(float, 1), 0)
    return: float
    """
    offset = rect.left() if horizontal else rect.top()
    width = rect.width() if horizontal else rect.height()
    return (width * ratio) + offset


def to_index(rect, point, weights, horizontal=True):
    """
    Find the weight index from qpoint.
    """
    ratio = to_ratio(rect, point, horizontal=horizontal)
    for i, weight in enumerate(weights):
        if ratio <= weight:
            return i
    return i


def graduate(ratios, limit):
    """
    Snap the given ratios to graduated values.
    """
    if len(ratios) > limit:
        raise ValueError(
            'Impossible to graduated more weights'
            f' ({len(ratios)}) than limit given ({limit})')
    grade = 1.0 / limit
    result = []
    for i, ratio in enumerate(ratios):
        minimum = grade * (i + 1)
        maximum = 1 - (grade * ((len(ratios) - (i + 1))))
        ratio = closest_ratio(ratio, grade)
        ratio = min((maximum, max((minimum, ratio))))
        while ratio in result:
            ratio += grade
        result.append(round(ratio, 5))
    return result


def closest_ratio(ratio, grade):
    n = 0
    while n <= 1.0:
        if ratio == n:
            return n
        if n < ratio < n + grade:
            return n if ratio - n < n + grade - ratio else n + grade
        n = round(n + grade, 5)
    raise ValueError("Impossible to find closest ratio")


def to_ratios(weights):
    """
    Convert weight list to ratios.
    input:  [0.2, 0.3, 0.4, 0.1]
    output: [0.2, 0.5, 0.9, 1.0]
    """
    total = 0.0
    result = []
    for weight in weights:
        total += weight
        result.append(round(total, 5))
    return result


def to_weights(ratios):
    """
    Convert ratio list to weights.
    input:  [0.2, 0.5, 0.9, 1.0]
    output: [0.2, 0.3, 0.4, 0.1]
    """
    result = []
    result.extend(round(ratio - sum(result), 5) for ratio in ratios)
    return result


def set_ratio_at(index, ratio, ratios, min_weight=0.1):
    """
    Change the ratio in a list of ratios and adapt value around if necessary.
    """
    minimum = min_weight * (index + 1)
    maximum = 1 - (min_weight * ((len(ratios) - (index + 1))))
    ratio = min((maximum, max((minimum, ratio))))
    result = []
    for i, r in enumerate(ratios):
        if i < index:
            security = min_weight * (index - i)
            result.append(min((r, ratio - security)))
        if i == index:
            result.append(ratio)
        if i > index:
            security = min_weight * (i - index)
            result.append(max((r, ratio + security)))
    return result


def append_ratio(ratios, graduation):
    """
    Add a ratio at the end of the list.
    """
    if len(ratios) == graduation:
        raise ValueError("Cannot add weights to slider")
    grade = 1 / graduation
    maximum = grade * (graduation - len(ratios))
    added = min([maximum, 1 / (len(ratios) + 1)])
    ratios = [round(r * (1 - added), 5) for r in ratios] + [1]
    return graduate(ratios, graduation)


def remove_ratio(ratios, index, graduation):
    """
    Remove the ratio at given index and adapt values around.
    """
    weights = to_weights(ratios)
    mult = 1 - weights[index]
    weights.pop(index)
    weights = [round(w / mult, 5) for w in weights]
    return graduate(to_ratios(weights), graduation)
