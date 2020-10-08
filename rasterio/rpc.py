from rasterio.compat import Iterable, UserDict, text_type
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