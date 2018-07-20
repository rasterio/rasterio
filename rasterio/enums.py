"""Enumerations."""

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

    The subset of 'nearest', 'cubic', 'average', 'mode', and 'gauss'
    are available in making dataset overviews.

    'max', 'min', 'med', 'q1', 'q3' are only supported in GDAL >= 2.0.0.

    'nearest', 'bilinear', 'cubic', 'cubic_spline', 'lanczos', 'average', 'mode'
    are always available (GDAL >= 1.10).

    Note: 'gauss' is not available to the functions in rio.warp.
    """
    nearest = 0
    bilinear = 1
    cubic = 2
    cubic_spline = 3
    lanczos = 4
    average = 5
    mode = 6
    gauss = 7
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
    zstd = 'ZSTD'
    lerc = 'LERC'


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

class MergeAlg(Enum):
    """Available rasterization algorithms"""
    replace = 'REPLACE'
    add = 'ADD'