from collections import defaultdict
from PySide2 import QtWidgets, QtCore, QtGui
from dwidgets.charts.dialog import ChartDetails
from dwidgets.charts.model import ChartModel
from dwidgets.charts.settings import (
    ChartViewContext, sort_elements,
    OUTPUT_ARROW_RADIUS, TABLE_MINIMUM_WIDTH,
    TOP_RESIZER_HEIGHT, FORMATTERS, GRADUATION_HEIGHT,
    LEFT_RESIZER_WIDTH, MINIUM_COLUMN_WIDTH, MINIUM_ROW_HEIGHT,
    FORKS_PADDING, FORKS_WIDTH, FORKS_XRADIUS, TOTAL_WIDTH)


class ChartView(QtWidgets.QWidget):
    settings_changed = QtCore.Signal()

    def __init__(
            self,
            context=None,
            parent=None):
        super().__init__(parent)
        self.model = ChartModel()
        self.context = context or ChartViewContext()
        self.setMouseTracking(True)
        self.header_rects = {}
        self.fork_rects = {}
        self.output_rects = {}
        self.resizer_rect = None
        self.collapse_rects = {}
        self.chart_rects = {}
        self.total_rects = {}
        self.navigation_slider = Slider()

        self.possible_action = None
        self.current_action = None
        self.mouse_pressed = False

    def sizeHint(self):
        return QtCore.QSize(800, 600)

    def set_schema(self, schema, collapsed=False):
        self.model.set_schema(schema, collapsed)
        self.compute_rects()

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.mouse_pressed = True
            self.possible_action = self.detect_hovered_action(event.pos())
            if self.possible_action:
                if self.possible_action['type'] in ('toggle', 'chart'):
                    self.execute_action(action=self.possible_action)
                else:
                    self.current_action = self.possible_action

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.mouse_pressed = False
            self.update_override(None)
            self.navigation_slider.ghost = None

    def mouseMoveEvent(self, event):
        if self.mouse_pressed:
            if self.current_action:
                self.execute_action(event.pos())
            return
        self.possible_action = self.detect_hovered_action(event.pos())
        self.update_override(
            None if not self.possible_action
            else self.possible_action.get('cursor'))

    def update_override(self, override):
        current_override = QtWidgets.QApplication.overrideCursor()
        if override != current_override:
            QtWidgets.QApplication.restoreOverrideCursor()
            if override:
                QtWidgets.QApplication.setOverrideCursor(override)

    def detect_hovered_action(self, pos):
        rect = self.map_to_visible_region(self.navigation_slider.rect)
        if rect and rect.contains(pos):
            line = self.map_to_visible_region(get_value_line(
                self.navigation_slider, self.navigation_slider.visible_min))
            area = QtCore.QRect(
                line.p1().x(), line.p1().y(), 4, line.p2().y())
            if area.contains(pos):
                return {
                    'type': 'navigation',
                    'mode': 'min',
                    'cursor': QtCore.Qt.SplitHCursor}
            line = self.map_to_visible_region(get_value_line(
                self.navigation_slider, self.navigation_slider.visible_max))
            area = QtCore.QRect(
                line.p1().x() - 4, line.p1().y(), 4, line.p2().y())
            if area.contains(pos):
                return {
                    'type': 'navigation',
                    'mode': 'max',
                    'cursor': QtCore.Qt.SplitHCursor}
            return {
                'type': 'navigation',
                'mode': 'body',
                'cursor': QtCore.Qt.OpenHandCursor}

        resize_area = self.map_to_visible_region(QtCore.QRect(
            self.resizer_rect.right() - 2,
            self.resizer_rect.top(), 4,
            self.resizer_rect.height()))
        if resize_area.contains(pos):
            return {
                'type': 'horizontal_resize',
                'rect': resize_area,
                'cursor': QtCore.Qt.SplitHCursor}

        for index, rect in self.output_rects.items():
            output = self.model.outputs[index]
            resize_area = QtCore.QRect(
                0, rect.bottom() - 2, LEFT_RESIZER_WIDTH, 4)
            if resize_area.contains(pos):
                return {
                    'type': 'vertical_resize',
                    'branch': output.branch(),
                    'rect': rect,
                    'cursor': QtCore.Qt.SplitVCursor}

        for index, rect in self.fork_rects.items():
            node = self.model.nodes[index]
            if rect.contains(pos):
                return {
                    'type': 'toggle',
                    'node': node}

        for index, content_rects in self.chart_rects.items():
            for key, data in content_rects.items():
                if data['rect'].contains(pos):
                    output = self.model.outputs[index]
                    value = sum(
                        self.model.entries[i].weight
                        for i in output.content[key])
                    branch = output.branch()
                    formatter, suffix = self.get_formatter_and_suffix(branch)
                    value = formatter(
                        data['value'],
                        suffix,
                        data['output_total'],
                        data['maximum'],
                        self.model.total())
                    key_text = self.context.translation_settings['value', key]
                    self.setToolTip(f'{key_text} | {value}')
                    return {
                        'type': 'chart',
                        'node': output,
                        'key': key}

    def leaveEvent(self, _):
        self.possible_action = None
        self.update_override(None)

    def execute_action(self, pos=None, action=None):
        action = action or self.current_action
        if action['type'] == 'horizontal_resize':
            rect = self.resizer_rect
            width = pos.x() - rect.left()
            self.context.set_setting(
                'header_width', max((width, MINIUM_COLUMN_WIDTH)))
            self.compute_rects()
            return
        if action['type'] == 'vertical_resize':
            rect = action['rect']
            bottom = max((pos.y(), rect.top() + MINIUM_ROW_HEIGHT))
            height = bottom - rect.top()
            branch = action['branch']
            self.context.branch_settings[branch, 'height'] = height
            self.compute_rects()
            return
        if action['type'] == 'toggle':
            node = action['node']
            if not ctrl_pressed() and not shift_pressed():
                node.expanded = not node.expanded
            elif not shift_pressed():
                self.model.expand_level(node.level, not node.expanded)
            else:
                self.model.expand_hierarchy(node, not node.expanded)
            self.compute_rects()
            return
        if action['type'] == 'chart':
            entry_indexes = action['node'].content[action['key']]
            entries = [self.model.entries[i] for i in entry_indexes]
            self.current_action = None
            return ChartDetails(
                action['node'], action['key'], entries, self).exec_()
        if action['type'] == 'navigation':
            value = get_value_from_point(self.navigation_slider, pos)
            if action['mode'] == 'min':
                value = max((value, self.navigation_slider.min))
                value = min((value, self.navigation_slider.visible_max - 10))
                self.navigation_slider.visible_min = value
            elif action['mode'] == 'max':
                value = min((value, self.navigation_slider.max))
                value = max((value, self.navigation_slider.visible_min + 10))
                self.navigation_slider.visible_max = value
            elif action['mode'] == 'body':
                if self.navigation_slider.ghost is not None:
                    delta = self.navigation_slider.ghost - value
                    value1 = self.navigation_slider.visible_min - delta
                    value1 = max((value1, self.navigation_slider.min))
                    value1 = min((value1, self.navigation_slider.max - 10))
                    self.navigation_slider.visible_min = value1
                    value2 = self.navigation_slider.visible_max - delta
                    value2 = min((value2, self.navigation_slider.max))
                    value2 = max((value2, self.navigation_slider.min + 10))
                    self.navigation_slider.visible_max = value2
                self.navigation_slider.ghost = value
            self.chart_rects = defaultdict(dict)
            self.repaint()
            return

    def compute_rects(self):
        self.output_rects = {}
        self.header_rects = {}
        self.fork_rects = {}
        width = self.context.get_setting('header_width') - LEFT_RESIZER_WIDTH
        self.resizer_rect = QtCore.QRect(
            LEFT_RESIZER_WIDTH, 0, width, TOP_RESIZER_HEIGHT)
        self.chart_rects = defaultdict(dict)
        self.total_rects = {}
        if self.model.is_empty():
            return
        self.compute_outputs()
        self.settings_changed.emit()
        self.repaint()

    def get_output_spacing(self, parents, new_parents):
        for deph, (p1, p2) in enumerate(zip(parents, new_parents)):
            if p1 != p2:
                return self.context.deph_settings[deph, 'spacing']
        if len(parents) != len(new_parents):
            deph = min((len(parents), len(new_parents)))
            return self.context.deph_settings[deph - 1, 'fork_spacing']
        return 0

    def compute_outputs(self):
        top = TOP_RESIZER_HEIGHT
        left = LEFT_RESIZER_WIDTH + self.context.get_setting('header_width')
        outputs = [o for o in self.model.tree.all_outputs() if o.is_expanded()]
        parents = []

        self.navigation_slider.rect = QtCore.QRect(
            left + self.context.get_output_width(), 0,
            self.rect().width() - left - self.context.get_output_width() -
            TOTAL_WIDTH,
            TOP_RESIZER_HEIGHT)

        for output in outputs:
            if not output.is_expanded():
                continue
            new_parents = output.parents()
            if parents:
                top += self.get_output_spacing(parents, new_parents)
            parents = new_parents
            height = self.context.branch_settings[output.branch(), 'height']
            width = self.context.get_output_width()
            rect = QtCore.QRect(left, top, width, height)
            self.output_rects[output.index] = rect
            top += height

        height = max(self.output_rects[o.index].bottom() for o in outputs)
        height += GRADUATION_HEIGHT
        self.setFixedHeight(max((height, self.parent().height())))

        minimum_width = (
            LEFT_RESIZER_WIDTH +
            self.context.get_setting('header_width') +
            self.context.get_output_width() +
            TOTAL_WIDTH +
            TABLE_MINIMUM_WIDTH)

        self.setMinimumWidth(minimum_width)
        parent = self.parent().parent()
        if parent:
            parent.setMinimumWidth(minimum_width + 50)

    def get_tree_nodes_rects(self, vp_rect):
        header_rects = {}
        fork_rects = {}
        if self.model.is_empty():
            return header_rects, fork_rects
        for node in self.model.tree.flat():
            if not node.parent or not node.is_expanded():
                continue
            left = tree_node_left(node)
            all_outputs = node.all_outputs()
            if not all_outputs:
                continue
            top = min(
                self.output_rects[o.index].top()
                for o in all_outputs if o.index in self.output_rects)
            bot = max(
                self.output_rects[o.index].bottom()
                for o in all_outputs if o.index in self.output_rects)
            if bot < vp_rect.top():
                continue
            if top > vp_rect.bottom():
                return header_rects, fork_rects

            if node.index not in self.header_rects:
                self.build_header_rect(node, left, top)
            header_rects[node.index] = self.header_rects[node.index]

            if not node.is_fork():
                continue
            if node.index in self.fork_rects:
                fork_rects[node.index] = self.fork_rects[node.index]
                continue

            top = min(
                self.output_rects[o.index].top()
                for o in node.outputs())
            bot = max(
                self.output_rects[o.index].bottom()
                for o in node.outputs())
            height = bot - top
            left = LEFT_RESIZER_WIDTH + (FORKS_WIDTH * (node.level - 1))
            width = min((FORKS_WIDTH, self.context.get_setting('header_width')))
            fork_rect = QtCore.QRect(
                left, top, width, height)
            self.fork_rects[node.index] = fork_rect
            fork_rects[node.index] = fork_rect
        return header_rects, fork_rects

    def build_header_rect(self, node, left, top):
        outputs = node.outputs()
        bot = max(
            (self.output_rects[o.index].bottom() for o in outputs),
            default=0)
        height = bot - top
        width = self.context.get_setting('header_width') - left
        rect = QtCore.QRect(left, top, width, height)
        if node.parent.is_fork():
            rect.setLeft(rect.left() + FORKS_PADDING)
        self.header_rects[node.index] = rect

    def get_body(self, vp_rect):
        maximum = self.model.maximum()
        left_limit = (
            list(self.output_rects.values())[0].right()
            if self.output_rects else 0)
        body_width = self.rect().width() - left_limit - TOTAL_WIDTH
        slider = self.navigation_slider
        slider_factor = slider.max - (slider.visible_max - slider.visible_min)
        offset = relative(slider.visible_min, 1, 100, 0, body_width)
        start_left = left_limit - offset
        chart_rects = {}
        total_rects = {}
        for index, output in self.model.outputs.items():
            skip = (
                not output.is_expanded() or
                self.output_rects[output.index].bottom() < vp_rect.top() or
                self.output_rects[output.index].top() > vp_rect.bottom())
            if skip:
                continue
            left = start_left
            rect = self.output_rects[output.index]
            branch = output.branch()
            top, height = get_output_top_height(self.context, branch, rect)

            if index not in self.chart_rects:
                self.build_output_chart_rects(
                    vp_rect, maximum, left_limit,
                    body_width, slider_factor,
                    output, left, top, height)
            total_rects[output.index] = self.total_rects[output.index]
            chart_rects[output.index] = self.chart_rects[output.index]
        return chart_rects, total_rects

    def build_output_chart_rects(
            self, vp_rect, maximum, left_limit, body_width, slider_factor,
            output, left, top, height):

        keys = sorted(output.content.keys(), key=lambda x: str(x))
        if not keys:
            return

        total = sum(
            self.model.entries[i].weight
            for key in keys for i in output.content[key])

        schema = self.context.sorting_settings['value', output.key]
        keys = sort_elements(schema, keys)
        for key in keys:
            value = sum(
                self.model.entries[i].weight
                for i in output.content[key])
            factor = value / maximum
            width = (body_width * factor) * slider_factor
            if left > vp_rect.right() or left + width < left_limit:
                left += width
                continue
            rect = QtCore.QRectF(left, top, width, height)
            rect.setLeft(max((left, left_limit)))
            right = min((rect.right(), vp_rect.right() - TOTAL_WIDTH))
            rect.setRight(right)
            if rect.width() == 0:
                continue
            self.chart_rects[output.index][key] = {
                        'rect': rect, 'value': value, 'maximum': maximum,
                        'output_total': total}
            left += rect.width()
        # Fix total rect left to the right band.
        if left + TOTAL_WIDTH > vp_rect.right() - TOTAL_WIDTH:
            left = vp_rect.right() - TOTAL_WIDTH

        self.total_rects[output.index] = {
            'rect': QtCore.QRect(left, top, TOTAL_WIDTH, height),
            'value': total,
            'output_total': total,
            'maximum': maximum}

    def mouseDoubleClickEvent(self, event):
        if self.detect_hovered_action(event.pos())['type'] == 'navigation':
            self.navigation_slider.reset()
            self.chart_rects = defaultdict(dict)
            self.repaint()

    def set_model(self, model):
        self.model = model
        self.compute_rects()

    def resizeEvent(self, _):
        self.compute_rects()

    def get_formatter_and_suffix(self, branch):
        formatter = self.context.branch_settings[branch, 'formatter']
        formatter = FORMATTERS[formatter]
        if formatter is None:
            formatter = self.context.get_setting('default_formatter')
            suffix = self.context.get_setting('default_value_suffix')
            return FORMATTERS[formatter], suffix
        return formatter, self.context.branch_settings[branch, 'value_suffix']

    def paint_headers(self, painter, header_rects, text_option):
        for index, rect in header_rects.items():
            node = self.model.nodes[index]
            color = self.context.colors_settings['key', node.key]
            painter.setPen(QtCore.Qt.NoPen)
            painter.setBrush(QtGui.QColor(color))
            painter.drawRoundedRect(rect, FORKS_XRADIUS, FORKS_XRADIUS)
            painter.setPen(QtGui.QPen())
            if node.is_fork():
                rect = QtCore.QRect(rect)
                rect.setLeft(rect.left() + FORKS_WIDTH)
            k = self.context.translation_settings['key', node.key]
            v = self.context.translation_settings['value', node.value]
            text = f'{k}:{v}' if self.context.get_setting('display_keys') else f'{v}'
            painter.drawText(rect, text, text_option)

    def map_to_visible_region(self, shape, source=None):
        source = source or self.visibleRegion().rects()[0]
        if isinstance(shape, QtCore.QRect):
            rect = QtCore.QRect(shape)
            rect.moveTo(rect.left(), source.top())
            return rect
        if isinstance(shape, QtCore.QLine):
            return QtCore.QLine(
                shape.p1().x(), shape.p1().y() + source.top(),
                shape.p2().x(), shape.p2().y() + source.top())

    def paintEvent(self, event):
        if self.model.is_empty():
            return
        total = self.model.total()
        painter = QtGui.QPainter(self)
        painter.setRenderHint(painter.Antialiasing)
        option = QtGui.QTextOption()
        option.setAlignment(QtCore.Qt.AlignCenter)
        option.setWrapMode(QtGui.QTextOption.NoWrap)
        header_rects, forks_rects = self.get_tree_nodes_rects(event.rect())
        left = (
            list(self.output_rects.values())[0].right()
            if self.output_rects else 0)
        width = event.rect().width() - left - TOTAL_WIDTH
        rect = QtCore.QRect(
            left, event.rect().top(), width, event.rect().height())
        maximum = self.model.maximum()
        draw_grid(painter, rect)
        painter.setPen(QtCore.Qt.transparent)
        color = QtGui.QColor('black')
        color.setAlpha(35)
        painter.setBrush(color)
        rect = QtCore.QRect(
            LEFT_RESIZER_WIDTH, event.rect().top(),
            left - LEFT_RESIZER_WIDTH, event.rect().height())
        painter.drawRect(rect)
        rect = QtCore.QRect(
            event.rect().right() - TOTAL_WIDTH, event.rect().top(),
            TOTAL_WIDTH, event.rect().height())
        painter.drawRect(rect)
        self.paint_headers(painter, header_rects, option)
        self.paint_forks(painter, forks_rects, option)
        self.paint_outputs(painter, event, option)
        self.paint_charts(painter, total, event, option)
        self.paint_horizontal_resizer(painter, event)
        self.paint_slider(painter, event)
        self.paint_graduation(painter, event, maximum)
        rect = QtCore.QRect(
            self.navigation_slider.rect.right(), event.rect().top(),
            event.rect().width() - self.navigation_slider.rect.right(),
            TOP_RESIZER_HEIGHT)
        painter.drawText(rect, str(round(total, 1)), option)
        painter.end()

    def paint_slider(self, painter, event):
        slider = self.navigation_slider
        if not slider.rect:
            return

        rect = self.map_to_visible_region(slider.rect, event.rect())
        painter.drawRect(rect)
        painter.setPen(QtCore.Qt.red)
        painter.setBrush(QtCore.Qt.red)
        line = self.map_to_visible_region(
            get_value_line(slider, slider.visible_min), event.rect())
        path = get_bracket_path(line, 'left')
        painter.drawPath(path)
        painter.setBrush(QtCore.Qt.red)
        line = self.map_to_visible_region(
            get_value_line(slider, slider.visible_max), event.rect())
        path = get_bracket_path(line, 'right')
        conditions = (
            slider.max != slider.visible_max or
            slider.min != slider.visible_min)
        if conditions:
            brush = QtGui.QBrush()
            brush.setStyle(QtCore.Qt.BDiagPattern)
            color = QtGui.QColor(QtCore.Qt.red)
            color.setAlpha(122)
            brush.setColor(color)
            painter.setBrush(brush)
            line1 = self.map_to_visible_region(
                get_value_line(slider, slider.visible_min), event.rect())
            line2 = self.map_to_visible_region(
                get_value_line(slider, slider.visible_max), event.rect())
            painter.drawRect(QtCore.QRect(line1.p1(), line2.p2()))

        painter.drawPath(path)

    def paint_graduation(self, painter, event, maximum):
        painter.setBrush(QtWidgets.QApplication.palette().background())
        painter.setPen(QtGui.QPen())
        painter.drawRect(
            event.rect().left(), event.rect().bottom() - GRADUATION_HEIGHT,
            event.rect().width(), GRADUATION_HEIGHT + 3)
        left = list(self.output_rects.values())[0].right()
        top = event.rect().bottom() - GRADUATION_HEIGHT
        width = event.rect().right() - TOTAL_WIDTH - left
        rect = QtCore.QRect(left, top, width, GRADUATION_HEIGHT)
        draw_grid(painter, rect, maximum)
        painter.setPen(QtGui.QPen())
        painter.drawLine(rect.topLeft(), rect.bottomLeft())
        painter.drawLine(rect.topRight(), rect.bottomRight())

    def paint_charts(self, painter, total, event, option):
        charts, totals = self.get_body(event.rect())
        for index, content_rects in charts.items():
            if not content_rects:
                continue
            check_rect = list(content_rects.values())[0]['rect']
            if check_rect.bottom() < event.rect().top():
                continue
            if check_rect.top() > event.rect().bottom():
                continue
            output = self.model.outputs[index]
            formatter, suffix = self.get_formatter_and_suffix(output.branch())
            for key, data in content_rects.items():
                rect = data['rect']
                color = self.context.colors_settings['value', key]
                painter.setPen(QtCore.Qt.NoPen)
                painter.setBrush(QtGui.QColor(color))
                painter.drawRect(rect)
                painter.setPen(QtGui.QPen())
                value = formatter(
                    data['value'],
                    suffix,
                    data['output_total'],
                    data['maximum'],
                    total)
                k = self.context.translation_settings['value', key]
                text = f'{k} | {value}'
                s = QtGui.QStaticText(text).size()
                if s.width() < rect.width() and s.height() < rect.height():
                    painter.drawText(rect, text, option)
            total_data = totals[output.index]
            value = formatter(
                total_data['value'],
                suffix,
                data['output_total'],
                data['maximum'],
                total)
            painter.drawText(total_data['rect'], value, option)

    def paint_horizontal_resizer(self, painter, event):
        painter.setBrush(QtWidgets.QApplication.palette().background())
        painter.setPen(QtGui.QPen())
        painter.drawRect(
            event.rect().left(), event.rect().top(),
            event.rect().width(), TOP_RESIZER_HEIGHT)
        rect = self.map_to_visible_region(self.resizer_rect, event.rect())
        painter.drawRect(rect)

    def paint_outputs(self, painter, event, option):
        font = QtGui.QFont()
        font.setBold(True)
        painter.setFont(font)
        for index, rect in self.output_rects.items():
            if rect.bottom() < event.rect().top():
                continue
            if rect.top() > event.rect().bottom():
                break
            output = self.model.outputs[index]
            output = self.model.outputs[index]
            parent = output.parent
            left = (
                self.header_rects[parent.index].right() +
                OUTPUT_ARROW_RADIUS)
            painter.setPen(QtCore.Qt.black)
            painter.setBrush(QtCore.Qt.black)
            point1 = QtCore.QPoint(left, rect.center().y())
            painter.drawEllipse(
                point1, OUTPUT_ARROW_RADIUS,
                OUTPUT_ARROW_RADIUS)
            point2 = QtCore.QPoint(rect.right(), rect.center().y())
            painter.drawLine(point1, point2)
            point = QtCore.QPoint(rect.right(), rect.center().y())
            path = QtGui.QPainterPath(point)
            path.lineTo(QtCore.QPoint(
                rect.right() - OUTPUT_ARROW_RADIUS,
                rect.center().y() - OUTPUT_ARROW_RADIUS))
            path.lineTo(QtCore.QPoint(
                rect.right() - OUTPUT_ARROW_RADIUS,
                rect.center().y() + OUTPUT_ARROW_RADIUS))
            painter.drawPath(path)
            ts = QtGui.QStaticText(output.key).size()
            trect = QtCore.QRect(
                left + OUTPUT_ARROW_RADIUS,
                rect.center().y() - ts.height(),
                rect.right() - (OUTPUT_ARROW_RADIUS * 2) - left,
                ts.height())
            text = self.context.translation_settings['key', output.key]
            if ts.width() < trect.width():
                painter.drawText(trect, text, option)
            painter.setBrush(QtGui.QBrush())
            top = rect.bottom()
            painter.setPen(QtCore.Qt.gray)
            line = QtCore.QLine(0, top, LEFT_RESIZER_WIDTH, top)
            painter.drawLine(line)

        painter.setPen(QtGui.QPen())
        painter.setBrush(QtGui.QBrush())
        line = QtCore.QLine(
            self.rect().left(), TOP_RESIZER_HEIGHT,
            self.rect().right(), TOP_RESIZER_HEIGHT)
        painter.drawLine(line)

    def paint_forks(self, painter, fork_rects, option):
        for index, rect in fork_rects.items():
            node = self.model.nodes[index]
            text = '-' if node.expanded else '+'
            painter.setBrush(QtCore.Qt.gray)
            painter.setPen(QtCore.Qt.NoPen)
            frect = QtCore.QRect(
                rect.left() + 2, rect.top() + 2,
                rect.width() - 4, rect.height() - 4)
            painter.drawRoundedRect(frect, FORKS_XRADIUS, FORKS_XRADIUS)
            painter.setPen(QtGui.QPen())
            painter.drawText(frect, text, option)
            if not node.expanded:
                continue
            line_x = rect.left() + (FORKS_PADDING / 2)
            start_y = rect.bottom()
            painter.setPen(QtGui.Qt.black)
            for child in node.children():
                child_rect = self.header_rects.get(child.index)
                if not child_rect:   # out of frame
                    continue
                x = child_rect.left()
                y = child_rect.center().y()
                painter.drawLine(line_x, y, x, y)
            painter.drawLine(line_x, start_y, line_x, y)


def shift_pressed():
    modifiers = QtWidgets.QApplication.keyboardModifiers()
    return modifiers == (modifiers | QtCore.Qt.ShiftModifier)


def alt_pressed():
    modifiers = QtWidgets.QApplication.keyboardModifiers()
    return modifiers == (modifiers | QtCore.Qt.AltModifier)


def ctrl_pressed():
    modifiers = QtWidgets.QApplication.keyboardModifiers()
    return modifiers == (modifiers | QtCore.Qt.ControlModifier)


class Slider:
    def __init__(self):
        self.rect = None
        self.min = 1
        self.max = 100
        self.visible_min = 1
        self.visible_max = 100
        self.ghost = None

    def reset(self):
        self.visible_max = self.max
        self.visible_min = self.min


def get_bracket_path(line, direction):
    path = QtGui.QPainterPath()
    path.moveTo(line.p1())
    path.lineTo(line.p2())
    offset1 = +5 if direction == 'left' else -5
    offset2 = +1 if direction == 'left' else -1
    path.lineTo(line.p2().x() + offset1, line.p2().y())
    path.lineTo(line.p2().x() + offset2, line.p2().y() - abs(offset1))
    path.lineTo(line.p2().x() + offset2, line.p1().y() + abs(offset1))
    path.lineTo(line.p2().x() + offset1, line.p1().y() + abs(offset2))
    path.lineTo(line.p2().x() + offset1, line.p1().y())
    path.moveTo(line.p1())
    return path


def get_value_from_point(slider, point):
    if slider.max - slider.min <= 1:
        return slider.min
    horizontal_divisor = float(slider.max - slider.min) or 1
    horizontal_unit_size = slider.rect.width() / horizontal_divisor
    value = 0
    x = slider.rect.left()
    while x < point.x():
        value += 1
        x += horizontal_unit_size
    # If pointer is closer to previous value, we set the value to previous one.
    if (x - point.x() > point.x() - (x - horizontal_unit_size)):
        value -= 1
    return value + slider.min


def get_value_line(slider, value):
    rect = slider.rect
    horizontal_divisor = float(slider.max - slider.min) or 1
    horizontal_unit_size = rect.width() / horizontal_divisor
    left = rect.left() + ((value - slider.min) * horizontal_unit_size)
    minimum = QtCore.QPoint(left, rect.top())
    maximum = QtCore.QPoint(left, rect.bottom())
    return QtCore.QLine(minimum, maximum)


def relative(value, in_min, in_max, out_min, out_max):
    """
    this function resolve simple equation and return the unknown value
    in between two values.
    a, a" = in_min, out_min
    b, b " = out_max, out_max
    c = value
    ? is the unknown processed by function.
    a --------- c --------- b
    a" --------------- ? ---------------- b"
    """
    factor = float((value - in_min)) / (in_max - in_min)
    width = out_max - out_min
    return out_min + (width * (factor))


def draw_grid(painter, rect, maximum=None):
    n = rect.width() // 10
    if n == 0:
        return
    step = rect.width() / n
    value_step = (maximum or 0) / n
    color = QtGui.QColor('black')
    pen = QtGui.QPen()
    option = QtGui.QTextOption()
    option.setAlignment(QtCore.Qt.AlignCenter)
    option.setWrapMode(QtGui.QTextOption.NoWrap)
    for i in range(n + 1):
        color.setAlpha(20 if i % 10 == 0 else 10)
        pen.setWidth(3 if i % 10 == 0 else 1)
        pen.setColor(color)
        painter.setPen(pen)
        left = rect.left() + (step * i)
        painter.drawLine(left, rect.top(), left, rect.bottom())
        if maximum is None or i % 10 != 0:
            continue
        color.setAlpha(255)
        pen.setColor(color)
        painter.setPen(pen)
        text = str(round(value_step * i, 1))
        width = QtGui.QStaticText(text).size().width() + 10
        trect = QtCore.QRect(*(left, rect.top(), width, rect.height()))
        if rect.right() < trect.right():
            continue
        painter.drawText(trect, text, option)
    if maximum is None or not n:
        return
    color.setAlpha(255)
    pen.setColor(color)
    painter.setPen(pen)
    text = str(round(maximum, 1))
    width = QtGui.QStaticText(text).size().width() + 10
    trect = QtCore.QRect(*(rect.right(), rect.top(), width, rect.height()))
    painter.drawText(trect, text, option)


def tree_node_left(node):
    if node.level == 1:
        return LEFT_RESIZER_WIDTH
    level = node.level - 2
    return LEFT_RESIZER_WIDTH + (FORKS_WIDTH * level)


def get_output_top_height(context, branch, rect):
    tpadding = context.branch_settings[branch, 'top_padding']
    bpadding = context.branch_settings[branch, 'bottom_padding']
    return rect.top() + tpadding, rect.height() - tpadding - bpadding
