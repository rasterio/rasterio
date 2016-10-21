"""Ground control points"""

from collections import namedtuple


class GroundControlPoint(object):
    """A mapping of row, col image coordinates to x, y, z in a CRS"""

    def __init__(self, row=None, col=None, x=None, y=None, z=None):
        self.row = row
        self.col = col
        self.x = x
        self.y = y
        self.z = z
