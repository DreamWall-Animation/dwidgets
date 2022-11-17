import math


def distance(a, b):
    """ return distance between two points """
    x = (b.x() - a.x())**2
    y = (b.y() - a.y())**2
    return math.sqrt(abs(x + y))


def distance_qline_qpoint(line, point):
    return distance_point_segment(
        point.x(), point.y(),
        line.p1().x(), line.p1().y(),
        line.p2().x(), line.p2().y())


def line_magnitude(x1, y1, x2, y2):
    return math.sqrt(math.pow((x2 - x1), 2) + math.pow((y2 - y1), 2))


def distance_point_segment(px, py, x1, y1, x2, y2):
    """
    https://maprantala.com/
        2010/05/16/measuring-distance-from-a-point-to-a-line-segment-in-python
    http://local.wasp.uwa.edu.au/~pbourke/geometry/pointline/source.vba
    """
    line_mag = line_magnitude(x1, y1, x2, y2)

    if line_mag < 0.00000001:
        return 9999

    u1 = (((px - x1) * (x2 - x1)) + ((py - y1) * (y2 - y1)))
    u = u1 / (line_mag * line_mag)

    if (u < 0.00001) or (u > 1):
        # closest point does not fall within the line segment, take the
        # shorter distance to an endpoint.
        ix = line_magnitude(px, py, x1, y1)
        iy = line_magnitude(px, py, x2, y2)
        return iy if ix > iy else ix
    else:
        # Intersecting point is on the line, use the formula
        ix = x1 + u * (x2 - x1)
        iy = y1 + u * (y2 - y1)
        return line_magnitude(px, py, ix, iy)
