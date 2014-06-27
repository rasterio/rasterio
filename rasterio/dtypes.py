
import numpy

bool_ = numpy.bool_
ubyte = uint8 = numpy.uint8
uint16 = numpy.uint16
int16 = numpy.int16
uint32 = numpy.uint32
int32 = numpy.int32
float32 = numpy.float32
float64 = numpy.float64
complex_ = numpy.complex_

# Not supported:
#  GDT_CInt16 = 8, GDT_CInt32 = 9, GDT_CFloat32 = 10, GDT_CFloat64 = 11

dtype_fwd = {
    0: None,      # GDT_Unknown
    1: ubyte,     # GDT_Byte
    2: uint16,    # GDT_UInt16
    3: int16,     # GDT_Int16
    4: uint32,    # GDT_UInt32
    5: int32,     # GDT_Int32
    6: float32,   # GDT_Float32
    7: float64,   # GDT_Float64
    8: complex_ } # GDT_CInt16

dtype_rev = dict((v, k) for k, v in dtype_fwd.items())
dtype_rev[uint8] = 1

typename_fwd = {
    0: 'Unknown',
    1: 'Byte',
    2: 'UInt16',
    3: 'Int16',
    4: 'UInt32',
    5: 'Int32',
    6: 'Float32',
    7: 'Float64',
    8: 'CInt16' }

typename_rev = dict((v, k) for k, v in typename_fwd.items())

def _gdal_typename(dtype):
    return typename_fwd[dtype_rev[dtype]]



