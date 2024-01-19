from PySide2 import QtCore, QtGui, QtWidgets
from dwidgets.charts.model import tree_to_schema, schema_to_tree, ChartNode


ROW_HEIGHT = 20
LEVEL_MARGIN = 25
TEXT_MARGIN = 10


class SchemaEditor(QtWidgets.QWidget):
    schema_edited = QtCore.Signal()

    def __init__(self, context, parent=None):
        super().__init__(parent)
        self.key_list = KeyList(context)
        self.tree_view = SchemaTreeView(context)
        self.scroll = QtWidgets.QScrollArea()
        self.scroll.setMinimumHeight(100)
        self.scroll.verticalScrollBar().valueChanged.connect(
            self.tree_view.repaint)
        self.scroll.setWidget(self.tree_view)
        self.scroll.setWidgetResizable(True)
        self.apply = QtWidgets.QPushButton('Apply schema')
        self.apply.released.connect(self.apply_clicked)

        group = QtWidgets.QGroupBox('Keywords')
        keywords = QtWidgets.QHBoxLayout(group)
        keywords.addWidget(self.key_list)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(group)
        layout.addWidget(self.scroll)
        layout.addWidget(self.apply)
        layout.addStretch(1)

        self.branch_settings = self.tree_view.branch_settings
        self.set_words = self.key_list.set_words
        self.set_schema = self.tree_view.set_schema
        self.get_schema = self.tree_view.get_schema

    def apply_clicked(self):
        self.tree_view.apply()
        self.schema_edited.emit()


class KeyList(QtWidgets.QWidget):
    def __init__(self, context, parent=None):
        super().__init__(parent)
        self.context = context
        self.setMouseTracking(True)
        self.words = []
        self.words_rects = {}
        self.option_rect = None

    def set_words(self, words):
        self.words = words
        self.compute_rects()

    def mouseMoveEvent(self, _):
        self.repaint()

    def mousePressEvent(self, event):
        for word, rect in self.words_rects.items():
            if rect.contains(event.pos()):
                drag = QtGui.QDrag(self)
                mime = QtCore.QMimeData()
                mime.setText(word)
                drag.setMimeData(mime)
                drag.setHotSpot(event.pos())
                drag.exec_()

    def mouseReleaseEvent(self, event):
        conditions = (
            event.button() == QtCore.Qt.LeftButton and
            self.option_rect.contains(event.pos()))
        if not conditions:
            return

        diag = EditHiddenKeyWords(self.words, self.context)
        diag.words_changed.connect(self.compute_rects)
        diag.words_changed.connect(self.repaint)
        diag.exec_()

    def compute_rects(self):
        top = 0
        left = 0
        self.words_rects = {}
        for word in self.words:
            if word in self.context.get_setting('hidden_keywords'):
                continue
            text = self.context.translation_settings['key', word]
            static = QtGui.QStaticText(text)
            width = static.size().width() + (TEXT_MARGIN * 2)
            if left != 0 and left + width > self.width():
                left = 0
                top += ROW_HEIGHT
            rect = QtCore.QRect(left, top, width, ROW_HEIGHT)
            self.words_rects[word] = rect
            left += rect.width()
        self.setFixedHeight(rect.bottom() + 7 if self.words else ROW_HEIGHT)
        self.option_rect = QtCore.QRect(
            self.rect().width() - 21, self.rect().bottom() - 21, 20, 20)

    def resizeEvent(self, _):
        self.compute_rects()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        option = QtGui.QTextOption()
        option.setAlignment(QtCore.Qt.AlignCenter)
        cursor = self.mapFromGlobal(QtGui.QCursor.pos())
        for word in self.words:
            if word in self.context.get_setting('hidden_keywords'):
                continue
            rect = self.words_rects[word]
            if rect.contains(cursor):
                painter.drawRect(rect)
            text = self.context.translation_settings['key', word]
            painter.drawText(rect, text, option)
        if self.option_rect:
            if self.option_rect.contains(cursor):
                painter.drawRect(self.option_rect)
            painter.drawText(self.option_rect, '⚙', option)


class EditHiddenKeyWords(QtWidgets.QDialog):
    words_changed = QtCore.Signal()

    def __init__(self, current_words, context, parent=None):
        super().__init__(parent)
        self.words = current_words
        self.context = context
        self.current_words = QtWidgets.QListWidget()
        self.current_words.setSelectionMode(
            QtWidgets.QAbstractItemView.ExtendedSelection)
        for current_word in current_words:
            if current_word in self.context.get_setting('hidden_keywords'):
                continue
            item = QtWidgets.QListWidgetItem(current_word)
            item.setData(QtCore.Qt.UserRole, current_word)
            text = self.context.translation_settings['key', current_word]
            item.setText(text)
            self.current_words.addItem(item)
        self.hidden_words = QtWidgets.QListWidget()
        self.hidden_words.setSelectionMode(
            QtWidgets.QAbstractItemView.ExtendedSelection)
        for word in self.context.get_setting('hidden_keywords'):
            item = QtWidgets.QListWidgetItem(word)
            item.setData(QtCore.Qt.UserRole, word)
            item.setText(self.context.translation_settings['key', word])
            self.hidden_words.addItem(item)

        add = QtWidgets.QPushButton('Hide words ->')
        add.released.connect(self.call_add)
        remove = QtWidgets.QPushButton('<- Show words')
        remove.released.connect(self.call_remove)

        lists = QtWidgets.QGridLayout(self)
        lists.addWidget(QtWidgets.QLabel('Keywords'), 0, 0)
        lists.addWidget(QtWidgets.QLabel('Hidden keyworkds'), 0, 1)
        lists.addWidget(self.current_words, 1, 0)
        lists.addWidget(self.hidden_words, 1, 1)
        lists.addWidget(add, 2, 0)
        lists.addWidget(remove, 2, 1)

    def call_add(self):
        words = [
            i.data(QtCore.Qt.UserRole)
            for i in self.current_words.selectedItems()]
        h = sorted({*(self.context.get_setting('hidden_keywords') + words)})
        self.context.set_setting('hidden_keywords', h)
        self.words_changed.emit()
        self.update_list()

    def update_list(self):
        self.hidden_words.clear()
        self.current_words.clear()
        for cw in self.words:
            if cw in self.context.get_setting('hidden_keywords'):
                continue
            item = QtWidgets.QListWidgetItem(cw)
            item.setData(QtCore.Qt.UserRole, cw)
            item.setText(self.context.translation_settings['key', cw])
            self.current_words.addItem(item)
        for word in self.context.get_setting('hidden_keywords'):
            item = QtWidgets.QListWidgetItem(word)
            item.setData(QtCore.Qt.UserRole, word)
            item.setText(self.context.translation_settings['key', word])
            self.hidden_words.addItem(item)

    def call_remove(self):
        words = [
            i.data(QtCore.Qt.UserRole)
            for i in self.hidden_words.selectedItems()]
        hidden = sorted({
            w for w in self.context.get_setting('hidden_keywords')
            if w not in words})
        self.context.set_setting('hidden_keywords', hidden)
        self.words_changed.emit()
        self.update_list()


class SchemaTreeView(QtWidgets.QWidget):
    branch_settings = QtCore.Signal(str)

    def __init__(self, context, parent=None):
        super().__init__(parent)
        self.context = context
        self.setMouseTracking(True)
        self.setAcceptDrops(True)
        self.tree = ChartNode()
        self.nodes = {}
        self.outputs = {}
        self.node_rects = {}
        self.output_rects = {}
        self.root_rect = None
        self.highlight = None
        self.applied = True

    def dragEnterEvent(self, event):
        reject = (
            not isinstance(event.source(), KeyList) or
            not event.mimeData().hasText())
        if reject:
            return False
        event.accept()

    def dragMoveEvent(self, event):
        for index, rect in self.node_rects.items():
            if rect.contains(event.pos()):
                self.highlight = index
                self.repaint()
                return
        for index, rect in self.output_rects.items():
            if rect.contains(event.pos()):
                self.highlight = index
                self.repaint()
                return
        self.highlight = self.tree.index
        self.repaint()

    def dragLeaveEvent(self, event):
        self.highlight = None
        self.repaint()

    def dropEvent(self, event):
        index = self.highlight
        self.highlight = None
        key = event.mimeData().text()
        if index in self.outputs:
            output = self.outputs[index]
            parent = output.parent
            parent.delete_output(output)
            branch = tuple((*parent.branch, output.key))
            child = parent.child(output.key, output.key, branch, branch)
            child.append(key, key, None)
            self.applied = False
            self.update_schema()
            return
        if index in self.nodes:
            node = self.nodes[index]
            node.append(key, key, None)
            self.applied = False
            self.update_schema()
            return

        self.tree.child(key, key, [key], [key])
        self.applied = False
        self.update_schema()
        return

    def apply(self):
        self.applied = True
        self.repaint()

    def set_schema(self, schema):
        self.tree, self.nodes, self.outputs = schema_to_tree(schema)
        self.compute_rects()

    def sizeHint(self):
        return QtCore.QSize(300, 200)

    def mouseMoveEvent(self, event):
        self.repaint()

    def compute_rects(self):
        self.node_rects = {}
        self.output_rects = {}
        top = 0
        for node in self.tree.flat():
            if node.parent is None:  # root
                continue
            self.node_rects[node.index] = QtCore.QRect(
                0, top, self.width(), ROW_HEIGHT)
            top += ROW_HEIGHT
            for output in node.outputs():
                self.output_rects[output.index] = QtCore.QRect(
                    0, top, self.width(), ROW_HEIGHT)
                top += ROW_HEIGHT
        self.node_rects[self.tree.index] = QtCore.QRect(
            0, top, self.width(), ROW_HEIGHT)
        parent = self.parent()
        if parent:
            height = max((top + ROW_HEIGHT, parent.height()))
        else:
            height = top + ROW_HEIGHT
        self.setFixedHeight(height)

    def resizeEvent(self, _):
        self.compute_rects()
        self.repaint()

    def leaveEvent(self, _):
        self.repaint()

    def enterEvent(self, _):
        self.repaint()

    def update_schema(self):
        self.nodes = {n.index: n for n in self.tree.flat() if n.level}
        self.outputs = {o.index: o for o in self.tree.all_outputs()}
        self.compute_rects()
        self.repaint()

    def mouseReleaseEvent(self, event):
        for index, rect in self.node_rects.items():
            if not rect.contains(event.pos()):
                continue
            if get_delete_rect(rect).contains(event.pos()):
                node = self.nodes[index]
                node.parent.delete_child(node)
                self.update_schema()
                self.applied = False
                return
        for index, rect in self.output_rects.items():
            if not rect.contains(event.pos()):
                continue
            if get_settings_rect(rect).contains(event.pos()):
                output = self.outputs[index]
                self.branch_settings.emit(output.branch())
                return
            if get_delete_rect(rect).contains(event.pos()):
                output = self.outputs[index]
                parent = output.parent
                parent.delete_output(output)
                flip = (
                    not parent.outputs() and
                    not parent.children() and
                    parent.parent.level > 0)
                if flip:
                    parent.parent.delete_child(parent)
                    branch = parent.branch[-2]
                    parent.parent.append(branch, branch, None)

                self.applied = False
                self.update_schema()
                return

    def repr(self):
        for node in self.tree.flat():
            print(node)
            for output in node.outputs():
                print(output)

    def get_schema(self):
        output_keys = sorted({o.key for o in self.tree.all_outputs()})
        nodes = self.tree.flat()[1:]
        # Fill level missing output.
        for node in nodes:
            if not node.outputs():
                print('no output for node', node.key, node.value, 'add key')
                if output_keys:
                    for key in output_keys:
                        node.append(key, key, None)
                    continue
                node.append(node.key, node.key, None)
        self.update_schema()
        return tree_to_schema(self.tree)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setPen(QtCore.Qt.transparent)
        painter.drawRect(event.rect())
        painter.setPen(QtGui.QPen())
        option = QtGui.QTextOption()
        option.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft)
        option2 = QtGui.QTextOption()
        option2.setAlignment(QtCore.Qt.AlignCenter)
        cursor = self.mapFromGlobal(QtGui.QCursor.pos())
        for index, rect in self.node_rects.items():
            if index == self.tree.index:
                continue
            node = self.nodes[index]
            left = LEVEL_MARGIN * (node.level - 1)
            text_rect = QtCore.QRect(
                left, rect.top(), rect.width() - left, rect.height())
            painter.drawRect(text_rect)
            text_rect.setLeft(text_rect.left() + TEXT_MARGIN)
            text = self.context.translation_settings['key', node.key]
            painter.drawText(text_rect, text, option)
            if not node.outputs():
                brush = QtGui.QBrush()
                brush.setStyle(QtCore.Qt.BDiagPattern)
                color = QtGui.QColor('orange')
                color.setAlpha(122)
                brush.setColor(color)
                painter.setBrush(brush)
                painter.setPen(QtCore.Qt.NoPen)
                painter.drawRect(text_rect)
                painter.setPen(QtGui.QPen())
                painter.setBrush(QtGui.QBrush())
            if rect.contains(cursor):
                delete_rect = get_delete_rect(rect)
                painter.drawRect(delete_rect)
                painter.drawText(delete_rect, '✘', option2)

        painter.setBrush(QtCore.Qt.green)
        for index, rect in self.output_rects.items():
            node = self.outputs[index]
            left = LEVEL_MARGIN * node.parent.level
            text_rect = QtCore.QRect(
                left, rect.top(), rect.width() - left, rect.height())
            painter.drawRect(text_rect)
            text_rect.setLeft(text_rect.left() + TEXT_MARGIN)
            text = self.context.translation_settings['key', node.key]
            painter.drawText(text_rect, text, option)
            if rect.contains(cursor):
                delete_rect = get_delete_rect(rect)
                painter.drawRect(delete_rect)
                painter.drawText(delete_rect, '✘', option2)
                settings_rect = get_settings_rect(rect)
                painter.drawRect(settings_rect)
                painter.drawText(settings_rect, '⚙', option2)

        if self.highlight is not None:
            rect = (
                self.node_rects.get(self.highlight) or
                self.output_rects.get(self.highlight))
            color = QtGui.QColor(QtCore.Qt.yellow)
            color.setAlpha(150)
            painter.setPen(QtCore.Qt.NoPen)
            painter.setBrush(color)
            painter.drawRect(rect)

        if not self.applied:
            pen = QtGui.QPen(QtGui.QColor('orange'))
            pen.setWidth(5)
            painter.setPen(pen)
            painter.setBrush(QtCore.Qt.NoBrush)
            painter.drawRoundedRect(event.rect(), 3, 3)

        painter.end()


def get_delete_rect(rect):
    return QtCore.QRect(
        rect.right() - rect.height(), rect.top(), rect.height(), rect.height())


def get_settings_rect(rect):
    return QtCore.QRect(
        rect.right() - (rect.height() * 2),
        rect.top(), rect.height(), rect.height())
