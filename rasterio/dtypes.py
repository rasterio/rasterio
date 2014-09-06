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
