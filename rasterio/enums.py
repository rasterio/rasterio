"""Enumerations."""

from enum import Enum, IntEnum


class ColorInterp(IntEnum):
    """Raster band color interpretation."""
    undefined = 0
    gray = 1
    grey = 1
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

    The first 8, 'nearest', 'bilinear', 'cubic', 'cubic_spline',
    'lanczos', 'average', 'mode', and 'gauss', are available for making
    dataset overviews.

    'max', 'min', 'med', 'q1', 'q3' are only supported in GDAL >= 2.0.0.

    'nearest', 'bilinear', 'cubic', 'cubic_spline', 'lanczos',
    'average', 'mode' are always available (GDAL >= 1.10).

    'sum' is only supported in GDAL >= 3.1.

    'rms' is only supported in GDAL >= 3.3.

    Note: 'gauss' is not available to the functions in rio.warp.
    """
    
    #: Nearest neighbor resampling (default, fastest algorithm, worst interpolation quality).
    nearest = 0
    #: Bilinear resampling.
    bilinear = 1
    #: Cubic resampling.
    cubic = 2
    #: Cubic spline resampling.
    cubic_spline = 3
    #: Lanczos windowed sinc resampling.
    lanczos = 4
    #: Average resampling, computes the weighted average of all non-NODATA contributing pixels.
    average = 5
    #: Mode resampling, selects the value which appears most often of all the sampled points.
    mode = 6
    #: Gaussian resampling, not available to the functions in rio.warp.
    gauss = 7
    #: Maximum resampling, selects the maximum value from all non-NODATA contributing pixels. (GDAL >= 2.2)
    max = 8
    #: Minimum resampling, selects the minimum value from all non-NODATA contributing pixels. (GDAL >= 2.2)
    min = 9
    #: Median resampling, selects the median value of all non-NODATA contributing pixels. (GDAL >= 2.2)
    med = 10
    #: Q1, first quartile resampling, selects the first quartile value of all non-NODATA contributing pixels. (GDAL >= 2.2)
    q1 = 11
    #: Q3, third quartile resampling, selects the third quartile value of all non-NODATA contributing pixels. (GDAL >= 2.2)
    q3 = 12
    #: Sum, compute the weighted sum of all non-NODATA contributing pixels. (GDAL >= 3.3)
    sum = 13
    #: RMS, root mean square / quadratic mean of all non-NODATA contributing pixels. (GDAL >= 3.3)
    rms = 14


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
    webp = 'WEBP'
    jpeg2000 = 'JPEG2000'


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


class WktVersion(Enum):
    """
     .. versionadded:: 1.3.0

    Supported CRS WKT string versions
    """

    #: WKT Version 2 from 2015
    WKT2_2015 = "WKT2_2015"
    #: Alias for latest WKT Version 2
    WKT2 = "WKT2"
    #: WKT Version 2 from 2019
    WKT2_2019 = "WKT2_2018"
    #: WKT Version 1 GDAL Style
    WKT1_GDAL = "WKT1_GDAL"
    #: Alias for WKT Version 1 GDAL Style
    WKT1 = "WKT1"
    #: WKT Version 1 ESRI Style
    WKT1_ESRI = "WKT1_ESRI"


    @classmethod
    def _missing_(cls, value):
        if value == "WKT2_2019":
            # WKT2_2019 alias added in GDAL 3.2, use WKT2_2018 for compatibility
            return WktVersion.WKT2_2019
        raise ValueError(f"Invalid value for WktVersion: {value}")
