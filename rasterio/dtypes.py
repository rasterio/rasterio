"""Mapping of GDAL to Numpy data types."""

import numpy

from rasterio.env import GDALVersion

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
    12: uint64,  # GDT_UInt64
    13: int64, # GDT_Int64
}

if _GDAL_AT_LEAST_37:
    dtype_fwd[14] = sbyte  # GDT_Int8

if _GDAL_AT_LEAST_37:
    dtype_fwd[14] = sbyte # GDT_Int8

dtype_rev = {v: k for k, v in dtype_fwd.items()}

dtype_rev["uint8"] = 1
dtype_rev["complex"] = 11
dtype_rev["complex_int16"] = 8

if not _GDAL_AT_LEAST_37:
    dtype_rev["int8"] = 1


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
    11: 'CFloat64',
    12: 'UInt64',
    13: 'Int64',
}


if _GDAL_AT_LEAST_37:
    typename_fwd[14] = "Int8"

if _GDAL_AT_LEAST_37:
    typename_fwd[14] = 'Int8'

typename_rev = {v: k for k, v in typename_fwd.items()}

f32i = numpy.finfo("float32")
f64i = numpy.finfo("float64")

dtype_ranges = {
    "int8": (-128, 127),
    "uint8": (0, 255),
    "uint16": (0, 65535),
    "int16": (-32768, 32767),
    "uint32": (0, 4294967295),
    "int32": (-2147483648, 2147483647),
    "float32": (float(f32i.min), float(f32i.max)),
    "float64": (float(f64i.min), float(f64i.max)),
    "int64": (-9223372036854775808, 9223372036854775807),
    "uint64": (0, 18446744073709551615),
}

dtype_info_registry = {"c": numpy.finfo, "f": numpy.finfo, "i": numpy.iinfo, "u": numpy.iinfo}


def in_dtype_range(value, dtype):
    """Test if the value is within the dtype's range of values, Nan, or Inf."""
    # The name of this function is a misnomer. What we're actually
    # testing is whether the value can be represented by the data type.
    kind = numpy.dtype(dtype).kind

    # Nan and infinity are special cases.
    if kind == "f" and (numpy.isnan(value) or numpy.isinf(value)):
        return True

    info = dtype_info_registry[kind](dtype)
    return info.min <= value <= info.max


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
    values = numpy.asanyarray(values)
    min_value = values.min()
    max_value = values.max()

    if values.dtype.kind in {'i', 'u'}:
        if min_value >= 0:
            if max_value <= 255:
                return uint8
            elif max_value <= 65535:
                return uint16
            elif max_value <= 4294967295:
                return uint32
            return uint64
        elif min_value >= -128 and max_value <= 127:
            return int8
        elif min_value >= -32768 and max_value <= 32767:
            return int16
        elif min_value >= -2147483648 and max_value <= 2147483647:
            return int32
        return int64
    else:
        if min_value >= -3.4028235e+38 and max_value <= 3.4028235e+38:
            return float32
        return float64


def is_ndarray(array):
    """Check if array is a ndarray."""

    return isinstance(array, numpy.ndarray) or hasattr(array, '__array__')


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
    values = numpy.asanyarray(values)

    if values.dtype.name == _getnpdtype(dtype).name:
        return True

    elif values.dtype.kind == 'f':
        return numpy.allclose(values, values.astype(dtype), equal_nan=True)

    else:
        return numpy.array_equal(values, values.astype(dtype))


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
    values = numpy.asanyarray(values)

    return (values.dtype.name in valid_dtypes or
            get_minimum_dtype(values) in valid_dtypes)


def _is_complex_int(dtype):
    return isinstance(dtype, str) and dtype.startswith("complex_int")


def _getnpdtype(dtype):
    if _is_complex_int(dtype):
        return numpy.dtype("complex64")
    else:
        return numpy.dtype(dtype)
