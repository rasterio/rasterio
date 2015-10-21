# Mapping of GDAL to Numpy data types.
#
# Since 0.13 we are not importing numpy here and data types are strings.
# Happily strings can be used throughout Numpy and so existing code will
# break.
#
# Within Rasterio, to test data types, we use Numpy's dtype() factory to 
# do something like this:
#
#   if np.dtype(destination.dtype) == np.dtype(rasterio.uint8): ...
#

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
    11: complex128 }    # GDT_CFloat64

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
    11: 'CFloat64' }

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
    if dt not in dtype_rev:
        try:
            return dt().dtype.name in dtype_rev
        except:
            return False
    return True


def get_minimum_int_dtype(values):
    """
    Uses range checking to determine the minimum integer data type required
    to represent values.

    :param values: numpy array
    :return: named data type that can be later used to create a numpy dtype
    """

    min_value = values.min()
    max_value = values.max()
    
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


def is_ndarray(array):
    import numpy

    return isinstance(array, numpy.ndarray) or hasattr(array, '__array__')
