"""Mapping of GDAL to Numpy data types.

Since 0.13 we are not importing numpy here and data types are strings.
Happily strings can be used throughout Numpy and so existing code will
not break.

"""
import numpy as np

from rasterio.env import GDALVersion

_GDAL_AT_LEAST_35 = GDALVersion.runtime().at_least("3.5")
_GDAL_AT_LEAST_37 = GDALVersion.runtime().at_least("3.7")

bool_ = 'bool'
ubyte = uint8 = 'uint8'
sbyte = int8 = 'int8'
uint16 = 'uint16'
int16 = 'int16'
uint32 = 'uint32'
int32 = 'int32'
uint64 = 'uint64'
int64 = 'int64'
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

if _GDAL_AT_LEAST_35:
    dtype_fwd[12] = int64 # GDT_Int64
    dtype_fwd[13] = uint64 # GDT_UInt64

if _GDAL_AT_LEAST_37:
    dtype_fwd[14] = sbyte # GDT_Int8

dtype_rev = dict((v, k) for k, v in dtype_fwd.items())

dtype_rev["uint8"] = 1
if not _GDAL_AT_LEAST_37:
    dtype_rev["int8"] = 1

dtype_rev["complex"] = 11
dtype_rev["complex_int16"] = 8


def _get_gdal_dtype(type_name):
    try:
        return dtype_rev[type_name]
    except KeyError:
        raise TypeError(
            f"Unsupported data type {type_name}. "
            f"Allowed data types: {list(dtype_rev)}."
        )

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

if _GDAL_AT_LEAST_35:
    typename_fwd[12] = 'Int64'
    typename_fwd[13] = 'UInt64'

if _GDAL_AT_LEAST_37:
    typename_fwd[14] = 'Int8'

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

if _GDAL_AT_LEAST_35:
    dtype_ranges['int64'] = (-9223372036854775808, 9223372036854775807)
    dtype_ranges['uint64'] = (0, 18446744073709551615)


def in_dtype_range(value, dtype):
    """
    Check if the value is within the dtype range
    """
    if np.dtype(dtype).kind == "f" and (np.math.isinf(value) or np.math.isnan(value)):
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


def _get_minimum_int(min_value, max_value):
    """Determine minimum int"""
    if min_value >= 0:
        if max_value <= 1:
            return bool_
        if max_value <= 255:
            return uint8
        elif max_value <= 65535:
            return uint16
        elif max_value <= 4294967295:
            return uint32
        if not _GDAL_AT_LEAST_35:
            raise ValueError("Values out of range for supported dtypes")
        return uint64
    elif min_value >= -128 and max_value <= 127:
        return int8
    elif min_value >= -32768 and max_value <= 32767:
        return int16
    elif min_value >= -2147483648 and max_value <= 2147483647:
        return int32
    if not _GDAL_AT_LEAST_35:
        raise ValueError("Values out of range for supported dtypes")
    return int64


def _get_minimum_float(min_value, max_value):
    if min_value >= -3.4028235e+38 and max_value <= 3.4028235e+38:
        return float32
    return float64


def _get_minimum_complex(min_value, max_value):
    real_dt = _get_minimum_float(min_value.real, max_value.real)
    imag_dt = _get_minimum_float(min_value.imag, max_value.imag)
    if (real_dt, imag_dt) == ('float32', 'float32'):
        return complex64
    return complex128


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
    is_arr = is_ndarray(values)
    if is_arr:
        if values.size == 0:
            return None
        dtype = values.dtype
    else:
        if not values:
            return None
        dtype = np.result_type(min_value, max_value)

    if dtype.kind in {'i', 'u'}:
        if is_arr:
            min_value = values.min()
            max_value = values.max()
        else:
            min_value = min(values)
            max_value = max(values)
        return _get_minimum_int(min_value, max_value)
    elif dtype.kind in {'f', 'c'}:
        # Check finite values range
        if is_arr:
            fvals = values[np.isfinite(values)]
            if fvals.size == 0:
                return None
            min_value = fvals.min()
            max_value = fvals.max()
        else:
            fvals = tuple(filter(np.math.isfinite, values))
            if not fvals:
                return None
            min_value = min(fvals)
            max_value = max(fvals)
        
        if dtype.kind == 'f':
            return _get_minimum_float(min_value, max_value)
        return _get_minimum_complex(min_value, max_value)


def is_ndarray(array):
    """Check if array is a ndarray."""

    return isinstance(array, np.ndarray) or hasattr(array, '__array__')


def can_cast_dtype(values, dtype):
    """Test if values can be cast to dtype without loss of information.

    Parameters
    ----------
    values: list-like
    dtype: numpy.dtype or string

    Returns
    -------
    boolean
        True if values can be cast to data type.
    """
    values = np.asarray(values)

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
    values = np.asarray(values)

    return (values.dtype.name in valid_dtypes or
            get_minimum_dtype(values) in valid_dtypes)


def _is_complex_int(dtype):
    return isinstance(dtype, str) and dtype.startswith("complex_int")


def _getnpdtype(dtype):
    if _is_complex_int(dtype):
        return np.dtype("complex64")
    else:
        return np.dtype(dtype)
