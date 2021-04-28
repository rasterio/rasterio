"""Bounding box tuple, and disjoint operator."""

from collections import namedtuple

BoundingBox = namedtuple('BoundingBox', ('left', 'bottom', 'right', 'top'))
BoundingBox.__doc__ = \
    """Bounding box named tuple, defining extent in cartesian coordinates.

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

def disjoint_bounds(bounds1, bounds2):
    """Compare two bounds and determine if they are disjoint.

    Parameters
    ----------
    bounds1: 4-tuple
        rasterio bounds tuple (left, bottom, right, top)
    bounds2: 4-tuple
        rasterio bounds tuple

    Returns
    -------
    boolean
    ``True`` if bounds are disjoint,
    ``False`` if bounds overlap
    """
    try:
        intersect_bounds(bounds1, bounds2)
        return True
    except BoundsError:
        return False


def reorient_bound(bound):
    def order(a, b):
        if b < a:
            return b, a
        return a, b

    l, b, r, t = bound
    if l < r and b < t:
        return BoundingBox(*bound)
    l, r = order(l, r)
    b, t = order(b, t)
    return BoundingBox(l, b, r, t)


def intersect_bounds(bounds1, bounds2):
    """Return the intersection of two bounds if it exists

    Parameters
    ----------
    bounds1: 4-tuple
        rasterio bounds tuple (left, bottom, right, top)
    bounds2: 4-tuple
        rasterio bounds tuple

    Returns
    -------
    BoundingBox
    """
    bounds1 = reorient_bound(bounds1)
    bounds2 = reorient_bound(bounds2)

    int_w = max(bounds1[0], bounds2[0])
    int_e = min(bounds1[2], bounds2[2])
    int_s = max(bounds1[1], bounds2[1])
    int_n = min(bounds1[3], bounds2[3])

    if int_w < int_e and int_s < int_n:
        return BoundingBox(int_w, int_s, int_e, int_n)
    raise BoundsError("empty intersection")