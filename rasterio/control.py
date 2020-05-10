"""Ground control points"""

import uuid
from rasterio.compat import Iterable, UserDict, text_type


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

class RPC(UserDict):
    """Rational Polynomial Coefficients used to map (x, y, z) <-> (row, col).
    
    RPCs are stored in a dict-like structure with methods to serialize and deserialize
    to/from GDAL metadata strings.
    """
    GDAL_RPC_KEYS = (
        "ERR_BIAS",
        "ERR_RAND",
        "HEIGHT_OFF",
        "HEIGHT_SCALE",
        "LAT_OFF",
        "LAT_SCALE",
        "LINE_DEN_COEFF",
        "LINE_NUM_COEFF",
        "LINE_OFF",
        "LINE_SCALE",
        "LONG_OFF",
        "LONG_SCALE",
        "SAMP_DEN_COEFF",
        "SAMP_NUM_COEFF",
        "SAMP_OFF",
        "SAMP_SCALE"
    )

    def __init__(self, data={}, **kwargs):
        UserDict.__init__(self)
        initdata = {}
        initdata.update(data)
        initdata.update(**kwargs)
        initdata = dict(filter(lambda item: item[0] in self.GDAL_RPC_KEYS, initdata.items()))
        self.data.update(initdata)

    def __getitem__(self, key):
        """Normal dict item getter."""
        return self.data[key]

    def __setitem__(self, key, val):
        """Normal dict item setter."""
        self.data[key] = val


    def to_gdal(self):
        """Serialize dict values to string."""
        out = {}

        for key, val in self.items():
            if isinstance(val, Iterable):
                out[key] = ' '.join(map(text_type, val))
            else:
                out[key] = text_type(val)

        return out

    @classmethod
    def from_gdal(cls, rpcs):
        """Deserialize dict values to float or list."""
        out = {}

        for key, val in rpcs.items():
            vals = val.split()
            if len(vals) > 1:
                out[key] = [float(v) for v in vals]
            else:
                out[key] = float(vals[0])

        return cls(out)