
from enum import Enum, IntEnum


class ColorInterp(IntEnum):
    """Raster band color interpretation."""
    undefined = 0
    grey = 1
    gray = 1
    palette = 2
    red = 3
    green = 4
    blue = 5
    alpha = 6
    hue = 7
    saturation = 8
    lightness = 9
    cyan = 10
    magenta = 11
    yellow = 12
    black = 13
    Y = 14
    Cb = 15
    Cr = 16


class Resampling(IntEnum):
    """Available warp resampling algorithms.

    A subset of these (0, 2, 5, 6) are available to band overviews.
    """
    nearest = 0
    bilinear = 1
    cubic = 2
    cubic_spline = 3
    lanczos = 4
    average = 5
    mode = 6
    max = 8
    min = 9
    med = 10
    q1 = 11
    q3 = 12


class Compression(Enum):
    """Available compression algorithms."""
    jpeg = 'JPEG'
    lzw = 'LZW'
    packbits = 'PACKBITS'
    deflate = 'DEFLATE'
    ccittrle = 'CCITTRLE'
    ccittfax3 = 'CCITTFAX3'
    ccittfax4 = 'CCITTFAX4'
    lzma = 'LZMA'
    none = 'NONE'


class Interleaving(Enum):
    pixel = 'PIXEL'
    line = 'LINE'
    band = 'BAND'


class MaskFlags(IntEnum):
    all_valid = 1
    per_dataset = 2
    alpha = 4
    nodata = 8


class PhotometricInterp(Enum):
    black = 'MINISBLACK'
    white = 'MINISWHITE'
    rgb = 'RGB'
    cmyk = 'CMYK'
    ycbcr = 'YCbCr'
    cielab = 'CIELAB'
    icclab = 'ICCLAB'
    itulab = 'ITULAB'
