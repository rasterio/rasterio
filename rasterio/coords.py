
from collections import namedtuple

BoundingBox = namedtuple('BoundingBox', ('left', 'bottom', 'right', 'top'))


def disjoint_bounds(bounds1, bounds2):
    """Returns True if bounds do not overlap

    Parameters
    ----------
    bounds1: rasterio bounds tuple (xmin, ymin, xmax, ymax)
    bounds2: rasterio bounds tuple
    """

    return (bounds1[0] > bounds2[2] or bounds1[2] < bounds2[0] or
            bounds1[1] > bounds2[3] or bounds1[3] < bounds2[1])