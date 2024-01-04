from collections import defaultdict
from PySide2 import QtWidgets, QtCore, QtGui
from dwidgets.charts.dialog import ChartDetails
from dwidgets.charts.model import ChartModel
from dwidgets.charts.settings import (
    BranchSettings, DephSettings, ColorsSettings,
    OUTPUT_ARROW_RADIUS, OUTPUT_WIDTH,
    TOP_RESIZER_HEIGHT, FORMATTERS, GRADUATION_HEIGHT,
    LEFT_RESIZER_WIDTH, MINIUM_COLUMN_WIDTH, MINIUM_ROW_HEIGHT,
    FORKS_PADDING, FORKS_WIDTH, FORKS_XRADIUS, TOTAL_WIDTH)


class ChartView(QtWidgets.QWidget):
    settings_changed = QtCore.Signal()

    def __init__(
            self,
            branch_settings=None,
            deph_settings=None,
            colors_settings=None,
            parent=None):
        super().__init__(parent)
        self.model = ChartModel()
        self.branch_settings = branch_settings or BranchSettings()
        self.deph_settings = deph_settings or DephSettings()
        self.colors_settings = colors_settings or ColorsSettings()
        self.setMouseTracking(True)
        self.header_rects = {}
        self.fork_rects = {}
        self.output_rects = {}
        self.resizer_rects = {}
        self.collapse_rects = {}
        self.chart_rects = {}
        self.total_rects = {}
        self.navigation_slider = Slider()

        self.possible_action = None
        self.current_action = None
        self.mouse_pressed = False

    def sizeHint(self):
        return QtCore.QSize(800, 600)

    def set_schema(self, schema):
        self.model.set_schema(schema)
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

        for index, rect in enumerate(self.resizer_rects):
            resize_area = self.map_to_visible_region(QtCore.QRect(
                rect.right() - 2, rect.top(), 4, rect.height()))
            if resize_area.contains(pos):
                return {
                    'type': 'horizontal_resize',
                    'column': index + 1,
                    'rect': rect,
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
                    self.setToolTip(f'{key} {value}')
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
            rect = action['rect']
            right = max((pos.x(), rect.left() + MINIUM_COLUMN_WIDTH))
            width = right - rect.left()
            self.deph_settings[action['column'], 'width'] = width
            self.compute_rects()
            return
        if action['type'] == 'vertical_resize':
            rect = action['rect']
            bottom = max((pos.y(), rect.top() + MINIUM_ROW_HEIGHT))
            height = bottom - rect.top()
            branch = action['branch']
            self.branch_settings[branch, 'height'] = height
            self.compute_rects()
            return
        if action['type'] == 'toggle':
            node = action['node']
            if not ctrl_pressed():
                node.expanded = not node.expanded
            else:
                self.model.expand_level(node.level, not node.expanded)
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
        self.resizer_rects = []
        self.chart_rects = defaultdict(dict)
        self.total_rects = {}
        if self.model.is_empty():
            return
        max_expanded_deph = self.model.current_deph()
        self.compute_outputs(max_expanded_deph)
        self.compute_resizers(max_expanded_deph)
        self.settings_changed.emit()
        self.repaint()

    def compute_outputs(self, max_expanded_deph):
        top = TOP_RESIZER_HEIGHT
        left = (
            LEFT_RESIZER_WIDTH +
            sum(self.deph_settings[i, 'width']
                for i in range(1, max_expanded_deph + 1)))
        outputs = [o for o in self.model.tree.all_outputs() if o.is_expanded()]
        parents = []
        self.navigation_slider.rect = QtCore.QRect(
            left + OUTPUT_WIDTH, 0,
            self.rect().width() - left - OUTPUT_WIDTH - TOTAL_WIDTH,
            TOP_RESIZER_HEIGHT)
        for output in outputs:
            if not output.is_expanded():
                continue
            new_parents = output.parents()
            if parents:
                for deph, (p1, p2) in enumerate(zip(parents, new_parents)):
                    if p1 != p2:
                        top += self.deph_settings[deph, 'spacing']
                        break
                else:
                    if len(parents) != len(new_parents):
                        deph = min((len(parents), len(new_parents)))
                        top += self.deph_settings[deph, 'fork_spacing']
            parents = new_parents
            height = self.branch_settings[output.branch(), 'height']
            rect = QtCore.QRect(left, top, OUTPUT_WIDTH, height)
            self.output_rects[output.index] = rect
            top += height
        height = max(self.output_rects[o.index].bottom() for o in outputs)
        height += GRADUATION_HEIGHT
        self.setFixedHeight(height)

    def compute_resizers(self, max_expanded_deph):
        self.resizer_rects = []
        for section in range(1, max_expanded_deph + 1):
            left = (
                LEFT_RESIZER_WIDTH +
                sum(self.deph_settings[i, 'width'] for i in range(1, section)))
            width = self.deph_settings[section, 'width']
            rect = QtCore.QRect(left, 0, width, TOP_RESIZER_HEIGHT)
            self.resizer_rects.append(rect)

    def get_tree_nodes_rects(self, vp_rect):
        header_rects = {}
        fork_rects = {}
        for node in self.model.tree.flat():
            if not node.parent or not node.is_expanded():
                continue
            left = (
                LEFT_RESIZER_WIDTH +
                sum(self.deph_settings[i, 'width']
                    for i in range(1, node.level)))
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
                outputs = node.outputs()
                bot = max(
                    (self.output_rects[o.index].bottom() for o in outputs),
                    default=0)
                height = bot - top
                width = self.deph_settings[node.level, 'width']
                rect = QtCore.QRect(left, top, width, height)
                if node.parent.is_fork():
                    rect.setLeft(rect.left() + FORKS_PADDING)
                self.header_rects[node.index] = rect
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
            left = rect.right()
            width = min((
                FORKS_WIDTH, self.deph_settings[node.level + 1, 'width']))
            fork_rect = QtCore.QRect(
                left, top, width, height)
            self.fork_rects[node.index] = fork_rect
            fork_rects[node.index] = fork_rect
        return header_rects, fork_rects

    def compute_headers(self):
        top = TOP_RESIZER_HEIGHT
        max_expanded_deph = self.model.current_deph()
        left = (
            LEFT_RESIZER_WIDTH +
            sum(self.deph_settings[i, 'width']
                for i in range(1, max_expanded_deph + 1)))
        outputs = [o for o in self.model.tree.all_outputs() if o.is_expanded()]
        parents = []
        self.navigation_slider.rect = QtCore.QRect(
            left + OUTPUT_WIDTH, 0,
            self.rect().width() - left - OUTPUT_WIDTH,
            TOP_RESIZER_HEIGHT)
        for output in outputs:
            if not output.is_expanded():
                continue
            new_parents = output.parents()
            if parents:
                for deph, (p1, p2) in enumerate(zip(parents, new_parents)):
                    if p1 != p2:
                        top += self.deph_settings[deph, 'spacing']
                        break
                else:
                    if len(parents) != len(new_parents):
                        deph = min((len(parents), len(new_parents)))
                        top += self.deph_settings[deph, 'fork_spacing']
            parents = new_parents
            height = self.branch_settings[output.branch(), 'height']
            rect = QtCore.QRect(left, top, OUTPUT_WIDTH, height)
            self.output_rects[output.index] = rect
            top += height

        for node in self.model.tree.flat():
            if not node.parent or not node.is_expanded():
                continue
            left = (
                LEFT_RESIZER_WIDTH +
                sum(self.deph_settings[i, 'width']
                    for i in range(1, node.level)))
            all_outputs = node.outputs() or node.all_outputs()
            if not all_outputs:
                continue
            top = min(self.output_rects[o.index].top() for o in all_outputs)
            bot = max(self.output_rects[o.index].bottom() for o in all_outputs)
            height = bot - top
            width = self.deph_settings[node.level, 'width']
            rect = QtCore.QRect(left, top, width, height)
            if node.parent.is_fork():
                rect.setLeft(rect.left() + FORKS_PADDING)
            self.header_rects[node.index] = rect
            if node.is_fork():
                top = min(
                    self.output_rects[o.index].top()
                    for o in node.outputs())
                bot = max(
                    self.output_rects[o.index].bottom()
                    for o in node.outputs())
                height = bot - top
                left = rect.right()
                width = min((
                    FORKS_WIDTH, self.deph_settings[node.level + 1, 'width']))
                self.fork_rects[node.index] = QtCore.QRect(
                    left, top, width, height)

        height = max(self.output_rects[o.index].bottom() for o in outputs)
        self.resizer_rects = []
        for section in range(1, max_expanded_deph + 1):
            left = (
                LEFT_RESIZER_WIDTH +
                sum(self.deph_settings[i, 'width'] for i in range(1, section)))
            width = self.deph_settings[section, 'width']
            rect = QtCore.QRect(left, 0, width, TOP_RESIZER_HEIGHT)
            self.resizer_rects.append(rect)

        self.setFixedHeight(height)

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
            top = (
                self.output_rects[output.index].top() +
                self.branch_settings[output.branch(), 'top_padding'])
            height = (
                self.output_rects[output.index].height() -
                self.branch_settings[output.branch(), 'top_padding'] -
                self.branch_settings[output.branch(), 'bottom_padding'])
            total = 0
            if index not in self.chart_rects:
                keys = sorted(output.content.keys(), key=lambda x: str(x))
                if not keys:
                    continue
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
                    self.chart_rects[output.index][key] = {
                        'rect': rect, 'value': value, 'maximum': maximum}
                    left += rect.width()
                    total += value
                total_data = {
                    'rect': QtCore.QRect(left, top, TOTAL_WIDTH, height),
                    'value': total,
                    'maximum': maximum}
                self.total_rects[output.index] = total_data
            total_rects[output.index] = self.total_rects[output.index]
            chart_rects[output.index] = self.chart_rects[output.index]
        return chart_rects, total_rects

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

    def paint_headers(self, painter, header_rects, text_option):
        for index, rect in header_rects.items():
            node = self.model.nodes[index]
            color = self.colors_settings['key', node.key]
            painter.setPen(QtCore.Qt.NoPen)
            painter.setBrush(QtGui.QColor(color))
            painter.drawRoundedRect(rect, FORKS_XRADIUS, FORKS_XRADIUS)
            painter.setPen(QtGui.QPen())
            painter.drawText(rect, str(node.value), text_option)

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
        draw_grid(painter, rect, 0)
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
        self.paint_charts(painter, event, option)
        self.paint_horizontal_resizers(painter, option, event)
        self.paint_slider(painter, event)
        self.paint_graduation(painter, event)

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

    def paint_graduation(self, painter, event):
        painter.setBrush(QtWidgets.QApplication.palette().background())
        painter.setPen(QtGui.QPen())
        painter.drawRect(
            event.rect().left(), event.rect().bottom() - GRADUATION_HEIGHT,
            event.rect().width(), GRADUATION_HEIGHT + 3)
        rect = QtCore.QRect(
            event.rect().right() - TOTAL_WIDTH,
            event.rect().bottom() - GRADUATION_HEIGHT,
            TOTAL_WIDTH, GRADUATION_HEIGHT + 3)
        option = QtGui.QTextOption()
        option.setAlignment(QtCore.Qt.AlignCenter)
        painter.drawText(rect, str(round(self.model.total(), 1)), option)

    def paint_charts(self, painter, event, option):
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
            formatter = self.branch_settings[output.branch(), 'formatter']
            suffix = self.branch_settings[output.branch(), 'value_suffix']
            formatter = FORMATTERS[formatter]
            for key, data in content_rects.items():
                rect = data['rect']
                color = self.colors_settings['value', key]
                painter.setPen(QtCore.Qt.NoPen)
                painter.setBrush(QtGui.QColor(color))
                painter.drawRect(rect)
                painter.setPen(QtGui.QPen())
                value = formatter(data['value'], suffix, data['maximum'])
                text = f'{key} | {value}'
                s = QtGui.QStaticText(text).size()
                if s.width() < rect.width() and s.height() < rect.height():
                    painter.drawText(rect, text, option)
            total_data = totals[output.index]
            value = formatter(total_data['value'], suffix, data['maximum'])
            painter.drawText(total_data['rect'], value, option)

    def paint_horizontal_resizers(self, painter, option, event):
        painter.setBrush(QtWidgets.QApplication.palette().background())
        painter.drawRect(
            event.rect().left(), event.rect().top(),
            event.rect().width(), TOP_RESIZER_HEIGHT)
        for i, rect in enumerate(self.resizer_rects):
            rect = self.map_to_visible_region(rect, event.rect())
            line = QtCore.QLine(
                rect.right(), rect.top(),
                rect.right(), rect.top() + TOP_RESIZER_HEIGHT)
            painter.drawLine(line)
            painter.drawText(rect, self.deph_settings[i + 1, 'header'], option)

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
            color = self.colors_settings['key', output.key]
            output = self.model.outputs[index]
            parent = output.parent
            if parent.is_fork():
                left = (
                    self.fork_rects[parent.index].right() +
                    OUTPUT_ARROW_RADIUS)
            else:
                left = (
                    self.header_rects[parent.index].right() +
                    OUTPUT_ARROW_RADIUS)
            painter.setPen(QtGui.QColor(color))
            painter.setBrush(QtGui.QColor(color))
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
            if ts.width() < trect.width():
                painter.drawText(trect, str(output.key), option)
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


def draw_grid(painter, rect, maximum):
    n = rect.width() // 10
    if n == 0:
        return
    step = rect.width() / n
    color = QtGui.QColor('black')
    pen = QtGui.QPen()
    for i in range(n + 1):
        color.setAlpha(20 if i % 10 == 0 else 10)
        pen.setWidth(3 if i % 10 == 0 else 1)
        pen.setColor(color)
        painter.setPen(pen)
        left = rect.left() + (step * i)
        painter.drawLine(left, rect.top(), left, rect.bottom())
