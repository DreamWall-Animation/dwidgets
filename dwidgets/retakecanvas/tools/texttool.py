
from PySide2 import QtCore, QtGui
from dwidgets.retakecanvas.geometry import grow_rect, get_shape_rect
from dwidgets.retakecanvas.shapes import Text
from dwidgets.retakecanvas.tools.shapetool import ShapeTool


class TextTool(ShapeTool):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.layername = 'Text'

    def window_cursor_override(self):
        return super().window_cursor_override() or QtCore.Qt.IBeamCursor

    def mousePressEvent(self, event):
        if self.layerstack.is_locked or self.navigator.space_pressed:
            return
        if self.layerstack.current is None:
            self.model.add_layer(undo=False, name=self.layername)
        self.selection.clear()
        self.shape = Text(
            start=self.viewportmapper.to_units_coords(event.pos()),
            text='Text',
            color=self.drawcontext.color,
            bgcolor=self.drawcontext.bgcolor,
            bgopacity=self.drawcontext.bgopacity,
            filled=self.drawcontext.filled,
            text_size=self.drawcontext.text_size)
        self.layerstack.current.append(self.shape)

    def mouseReleaseEvent(self, event):
        shape = self.shape
        if not super().mouseReleaseEvent(event):
            return
        if shape and shape.is_valid:
            self.selection.set(shape)
        self.canvas.selectionChanged.emit()
        return True

    def draw(self, painter):
        if not self.shape or not self.shape.is_valid:
            return

        rect = get_shape_rect(self.shape, self.viewportmapper)
        rect2 = grow_rect(rect, 5)
        path = QtGui.QPainterPath()
        path.addRect(rect)
        path.addRect(rect2)
        pen = QtGui.QPen(QtGui.QColor(0, 0, 0, 0))
        brush = QtGui.QBrush(QtGui.QColor(125, 125, 125))
        brush.setStyle(QtCore.Qt.FDiagPattern)
        painter.setPen(pen)
        painter.setBrush(brush)
        painter.drawPath(path)

        painter.setPen(QtCore.Qt.black)
        painter.setBrush(QtGui.QBrush(QtGui.QColor(0, 0, 0, 0)))
        painter.drawRect(rect)
