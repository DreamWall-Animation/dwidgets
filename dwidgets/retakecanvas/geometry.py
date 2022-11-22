import sys
import math
from PySide2 import QtCore
from dwidgets.retakecanvas.shapes import (
    Bitmap, Text, Rectangle, Circle, Arrow, Stroke)


def get_images_rects(baseimage, stackimages, layout=0):
    """
    layout: RetakeCanvasModel.GRID | STACKED | HORIZONTAL | VERTICAL
    """
    images = [baseimage] + stackimages
    rects = [
        QtCore.QRectF(0, 0, image.size().width(), image.size().height())
        for image in images]
    last_rect = None
    if layout == 2:
        for rect in rects:
            if not last_rect:
                last_rect = rect
                continue
            rect.moveTopLeft(last_rect.topRight())
            last_rect = rect
    elif layout == 3:
        for rect in rects:
            if not last_rect:
                last_rect = rect
                continue
            rect.moveTopLeft(last_rect.bottomLeft())
            last_rect = rect
    elif layout == 0:
        set_grid_layout(rects)
    return rects[1:]


def get_global_rect(baseimage, stackimages, layout=0):
    image_rect = QtCore.QRectF(0, 0, baseimage.width(), baseimage.height())
    rects = get_images_rects(baseimage, stackimages, layout)
    rects.append(image_rect)
    return combined_rect(rects)


def combined_rect(rects):
    left, top = sys.maxsize, sys.maxsize
    right, bottom = -sys.maxsize, -sys.maxsize
    for rect in rects:
        left = min((rect.left(), left))
        top = min((rect.top(), top))
        right = max((rect.right(), right))
        bottom = max((rect.bottom(), bottom))
    return QtCore.QRectF(left, top, right - left, bottom - top)


def set_grid_layout(viewport_rects):
    colcount = math.ceil(math.sqrt(len(viewport_rects)))
    width = max(rect.width() for rect in viewport_rects)
    height = max(rect.height() for rect in viewport_rects)
    top, left = viewport_rects[0].top(), viewport_rects[0].left()
    for i, rect in enumerate(viewport_rects):
        if not i:
            left += width
            continue
        if i % colcount == 0:
            left = viewport_rects[0].left()
            top += height
        rect.moveTopLeft(QtCore.QPointF(left, top))
        left += width
    return


def grow_rect(rect, value):
    if rect is None:
        return None
    return QtCore.QRectF(
        rect.left() - value,
        rect.top() - value,
        rect.width() + (value * 2),
        rect.height() + (value * 2))


def points_rect(points):
    left, top = sys.maxsize, sys.maxsize
    right, bottom = -sys.maxsize, -sys.maxsize
    for point in points:
        left = min((point.x(), left))
        top = min((point.y(), top))
        right = max((point.x(), right))
        bottom = max((point.y(), bottom))
    return QtCore.QRectF(left, top, right - left, bottom - top)


def get_shape_rect(element, viewportmapper):
    if isinstance(element, Stroke):
        points = [p for p, _ in element]
        return viewportmapper.to_viewport_rect(points_rect(points))
    elif isinstance(element, (Arrow, Rectangle, Circle, Text)):
        rect = QtCore.QRectF(element.start, element.end)
        return viewportmapper.to_viewport_rect(rect)
    elif isinstance(element, Bitmap):
        rect = QtCore.QRectF(element.rect)
        return viewportmapper.to_viewport_rect(rect)
