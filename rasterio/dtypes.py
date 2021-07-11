"""Mapping of GDAL to Numpy data types.

Since 0.13 we are not importing numpy here and data types are strings.
Happily strings can be used throughout Numpy and so existing code will
not break.

"""
import numpy

bool_ = 'bool'
ubyte = uint8 = 'uint8'
sbyte = int8 = 'int8'
uint16 = 'uint16'
int16 = 'int16'
uint32 = 'uint32'
int32 = 'int32'
float32 = 'float32'
float64 = 'float64'
complex_ = 'complex'
complex64 = 'complex64'
complex128 = 'complex128'

complex_int16 = "complex_int16"

dtype_fwd = {
    0: None,  # GDT_Unknown
    1: ubyte,  # GDT_Byte
    2: uint16,  # GDT_UInt16
    3: int16,  # GDT_Int16
    4: uint32,  # GDT_UInt32
    5: int32,  # GDT_Int32
    6: float32,  # GDT_Float32
    7: float64,  # GDT_Float64
    8: complex_int16,  # GDT_CInt16
    9: complex64,  # GDT_CInt32
    10: complex64,  # GDT_CFloat32
    11: complex128,  # GDT_CFloat64
}

dtype_rev = dict((v, k) for k, v in dtype_fwd.items())

dtype_rev["uint8"] = 1
dtype_rev["int8"] = 1
dtype_rev["complex"] = 11
dtype_rev["complex_int16"] = 8

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
    'int8': (-128, 127),
    'uint8': (0, 255),
    'uint16': (0, 65535),
    'int16': (-32768, 32767),
    'uint32': (0, 4294967295),
    'int32': (-2147483648, 2147483647),
    'float32': (-3.4028235e+38, 3.4028235e+38),
    'float64': (-1.7976931348623157e+308, 1.7976931348623157e+308)}


def in_dtype_range(value, dtype):
    """
    Check if the value is within the dtype range
    """
    if numpy.dtype(dtype).kind == "f" and (numpy.isinf(value) or numpy.isnan(value)):
        return True
    range_min, range_max = dtype_ranges[dtype]
    return range_min <= value <= range_max


def _gdal_typename(dt):
    try:
        return typename_fwd[dtype_rev[dt]]
    except KeyError:
        return typename_fwd[dtype_rev[dt().dtype.name]]


def check_dtype(dt):
    """Check if dtype is a known dtype."""
    if str(dt) in dtype_rev:
        return True
    elif callable(dt) and str(dt().dtype) in dtype_rev:
        return True
    return False


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

    if values.dtype.kind in ('i', 'u'):
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

    if values.dtype.name == _getnpdtype(dtype).name:
        return True

    elif values.dtype.kind == 'f':
        return np.allclose(values, values.astype(dtype), equal_nan=True)

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


def _is_complex_int(dtype):
    return isinstance(dtype, str) and dtype.startswith("complex_int")


def _getnpdtype(dtype):
    import numpy as np
    if _is_complex_int(dtype):
        return np.dtype("complex64")
    else:
        return np.dtype(dtype)
