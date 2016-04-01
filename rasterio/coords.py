
from collections import namedtuple

_BoundingBox = namedtuple('BoundingBox', ('left', 'bottom', 'right', 'top'))


class BoundingBox(_BoundingBox):
    """Bounding box named tuple, defining extent in cartesian coordinates

    .. code::

        BoundingBox(left, bottom, right, top)

    Attributes
    ----------
    left :
        Left coordinate
    bottom :
        Bottom coordinate
    right :
        Right coordinate
    top :
        Top coordinate
    """
    pass


def disjoint_bounds(bounds1, bounds2):
    """Compare two bounds and determine if they are disjoint

    Parameters
    ----------
    bounds1: 4-tuple
        rasterio bounds tuple (xmin, ymin, xmax, ymax)
    bounds2: 4-tuple
        rasterio bounds tuple

    Returns
    -------
    boolean
    ``True`` if bounds are disjoint,
    ``False`` if bounds overlap
    """

    return (bounds1[0] > bounds2[2] or bounds1[2] < bounds2[0] or
            bounds1[1] > bounds2[3] or bounds1[3] < bounds2[1])
