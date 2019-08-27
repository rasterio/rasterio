"""Ground control points"""

import uuid


class GroundControlPoint(object):
    """A mapping of row, col image coordinates to x, y, z."""

    def __init__(self, row=None, col=None, x=None, y=None, z=None,
                 id=None, info=None):
        """Create a new ground control point

        Parameters
        ----------
        row, col : float, required
            The row (or line) and column (or pixel) coordinates that
            map to spatial coordinate values ``y`` and ``x``,
            respectively.
        x, y : float, required
            Spatial coordinates of a ground control point.
        z : float, optional
            Optional ``z`` coordinate.
        id : str, optional
            A unique identifer for the ground control point.
        info : str, optional
            A short description for the ground control point.
        """
        if any(x is None for x in (row, col, x, y)):
            raise ValueError("row, col, x, and y are required parameters.")
        if id is None:
            id = str(uuid.uuid4())
        self.id = id
        self.info = info
        self.row = row
        self.col = col
        self.x = x
        self.y = y
        self.z = z

    def __repr__(self):
        args = ', '.join(['{}={}'.format(att, repr(getattr(self, att)))
                         for att in ('row', 'col', 'x', 'y', 'z', 'id', 'info')
                         if getattr(self, att) is not None])
        return "GroundControlPoint({})".format(args)

    def asdict(self):
        """A dict representation of the GCP"""
        return {'id': self.id, 'info': self.info, 'row': self.row,
                'col': self.col, 'x': self.x, 'y': self.y, 'z': self.z}

    @property
    def __geo_interface__(self):
        """A GeoJSON representation of the GCP"""
        coords = [self.x, self.y]
        if self.z is not None:
            coords.append(self.z)
        return {'id': self.id, 'type': 'Feature',
                'geometry': {'type': 'Point', 'coordinates': tuple(coords)},
                'properties': self.asdict()}


class GCPS(object):
    """Base class for GCPS."""

    def __init__(self, points, crs, transform):
        """
        Create a GCPS object.

        Parameters
        ----------
        points: list of GroundControlPoint
            Zero or more ground control points.
        crs: CRS
            The coordinate reference system of the ground control points.
        transform: affine.Affine()
            Affine transformation created from the GCPS.

        """
        self._points = points
        self._crs = crs
        self._transform = transform

    def __iter__(self):
        """
        Return a tuple of GCPS information.

        For compatibility issue, it returns only points and crs information.

        """
        return iter((self.points, self.crs))

    @property
    def points(self):
        """Return points list."""
        return self._points

    @property
    def crs(self):
        """Return the coordinate reference system information."""
        return self._crs

    @property
    def transform(self):
        """Return the affine transformation information."""
        return self._transform
