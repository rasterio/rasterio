"""Mapping of GDAL to Numpy data types.

Since 0.13 we are not importing numpy here and data types are strings.
Happily strings can be used throughout Numpy and so existing code will
break.

Within Rasterio, to test data types, we use Numpy's dtype() factory to
do something like this:

    if np.dtype(destination.dtype) == np.dtype(rasterio.uint8): ...
"""

bool_ = 'bool'
ubyte = uint8 = 'uint8'
uint16 = 'uint16'
int16 = 'int16'
uint32 = 'uint32'
int32 = 'int32'
float32 = 'float32'
float64 = 'float64'
complex_ = 'complex'
complex64 = 'complex64'
complex128 = 'complex128'

# Not supported:
#  GDT_CInt16 = 8, GDT_CInt32 = 9, GDT_CFloat32 = 10, GDT_CFloat64 = 11

dtype_fwd = {
    0: None,            # GDT_Unknown
    1: ubyte,           # GDT_Byte
    2: uint16,          # GDT_UInt16
    3: int16,           # GDT_Int16
    4: uint32,          # GDT_UInt32
    5: int32,           # GDT_Int32
    6: float32,         # GDT_Float32
    7: float64,         # GDT_Float64
    8: complex_,        # GDT_CInt16
    9: complex_,        # GDT_CInt32
    10: complex64,      # GDT_CFloat32
    11: complex128}    # GDT_CFloat64

dtype_rev = dict((v, k) for k, v in dtype_fwd.items())
dtype_rev['uint8'] = 1

typename_fwd = {
    0: 'Unknown',
    1: 'Byte',
    2: 'UInt16',
    3: 'Int16',
    4: 'UInt32',
    5: 'Int32',
    6: 'Float32',
    7: 'Float64',
    8: 'CInt16',
    9: 'CInt32',
    10: 'CFloat32',
    11: 'CFloat64'}

typename_rev = dict((v, k) for k, v in typename_fwd.items())

dtype_ranges = {
    'uint8': (0, 255),
    'uint16': (0, 65535),
    'int16': (-32768, 32767),
    'uint32': (0, 4294967295),
    'int32': (-2147483648, 2147483647),
    'float32': (-3.4028235e+38, 3.4028235e+38),
    'float64': (-1.7976931348623157e+308, 1.7976931348623157e+308)}


def _gdal_typename(dt):
    try:
        return typename_fwd[dtype_rev[dt]]
    except KeyError:
        return typename_fwd[dtype_rev[dt().dtype.name]]


def check_dtype(dt):
    """Check if dtype is a known dtype."""
    if dt not in dtype_rev:
        try:
            return dt().dtype.name in dtype_rev
        except:
            return False
    return True


def get_minimum_dtype(values):
    """Determine minimum type to represent values.

    Uses range checking to determine the minimum integer or floating point
    data type required to represent values.

    Parameters
    ----------
    values: list-like


    Returns
    -------
    rasterio dtype string
    """
    import numpy as np

    if not is_ndarray(values):
        values = np.array(values)

    min_value = values.min()
    max_value = values.max()

    if values.dtype.kind == 'i':
        if min_value >= 0:
            if max_value <= 255:
                return uint8
            elif max_value <= 65535:
                return uint16
            elif max_value <= 4294967295:
                return uint32
        elif min_value >= -32768 and max_value <= 32767:
            return int16
        elif min_value >= -2147483648 and max_value <= 2147483647:
            return int32

    else:
        if min_value >= -3.4028235e+38 and max_value <= 3.4028235e+38:
            return float32
        return float64


def is_ndarray(array):
    """Check if array is a ndarray."""
    import numpy as np

    return isinstance(array, np.ndarray) or hasattr(array, '__array__')


def can_cast_dtype(values, dtype):
    """Test if values can be cast to dtype without loss of information.

    Parameters
    ----------
    values: list-like
    dtype: numpy dtype or string

    Returns
    -------
    boolean
        True if values can be cast to data type.
    """
    import numpy as np

    if not is_ndarray(values):
        values = np.array(values)

    if values.dtype.name == np.dtype(dtype).name:
        return True

    elif values.dtype.kind == 'f':
        return np.allclose(values, values.astype(dtype))

    else:
        return np.array_equal(values, values.astype(dtype))


def validate_dtype(values, valid_dtypes):
    """Test if dtype of values is one of valid_dtypes.

    Parameters
    ----------
    values: list-like
    valid_dtypes: list-like
        list of valid dtype strings, e.g., ('int16', 'int32')

    Returns
    -------
    boolean:
        True if dtype of values is one of valid_dtypes
    """
    import numpy as np

    if not is_ndarray(values):
        values = np.array(values)

    return (values.dtype.name in valid_dtypes or
            get_minimum_dtype(values) in valid_dtypes)
