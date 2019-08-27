"""GCPS: Ground Control Points base class."""


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
        return self._points

    @property
    def crs(self):
        return self._crs

    @property
    def transform(self):
        return self._transform
