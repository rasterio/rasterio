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


def contains_coord(bounds, coord):
    """Test if coord is contained in bounds.
    Coordinate and bounds are assumed to be relative to the same CRS.

    Parameters
    ----------
    bounds: BoundingBox
    coord: Sequence
        xy coordinate

    Returns
    -------
    boolean
    ``True`` if coord is contained in bounding box
    ``False`` otherwise
    """
    x, y = coord
    # if we are dealing with a possibly south-up bounding box
    bottom, top = sorted((bounds.bottom, bounds.top))
    return (bottom <= y <= top
            and
            bounds.left <= x <= bounds.right)


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
    bounds1_north_up = bounds1[3] > bounds1[1]
    bounds2_north_up = bounds2[3] > bounds2[1]

    if not bounds1_north_up and bounds2_north_up:
        # or both south-up (also True)
        raise ValueError("Bounds must both have the same orientation")

    if bounds1_north_up:
        return (bounds1[0] > bounds2[2] or bounds2[0] > bounds1[2] or
                bounds1[1] > bounds2[3] or bounds2[1] > bounds1[3])
    else:
        return (bounds1[0] > bounds2[2] or bounds2[0] > bounds1[2] or
                bounds1[3] > bounds2[1] or bounds2[3] > bounds1[1])
