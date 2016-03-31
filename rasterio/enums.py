
from enum import Enum, IntEnum


class ColorInterp(IntEnum):
    undefined=0
    grey=1
    gray=1
    palette=2
    red=3
    green=4
    blue=5
    alpha=6
    hue=7
    saturation=8
    lightness=9
    cyan=10
    magenta=11
    yellow=12
    black=13
    Y=14
    Cb=15
    Cr=16


class Resampling(Enum):
    nearest='NEAREST'
    gauss='GAUSS'
    cubic='CUBIC'
    average='AVERAGE'
    mode='MODE'
    average_magphase='AVERAGE_MAGPHASE'
    none='NONE'


class Compression(Enum):
    jpeg='JPEG'
    lzw='LZW'
    packbits='PACKBITS'
    deflate='DEFLATE'
    ccittrle='CCITTRLE'
    ccittfax3='CCITTFAX3'
    ccittfax4='CCITTFAX4'
    lzma='LZMA'
    none='NONE'


class Interleaving(Enum):
    pixel='PIXEL'
    line='LINE'
    band='BAND'


class MaskFlags(IntEnum):
    all_valid=1
    per_dataset=2
    alpha=4
    nodata=8


class PhotometricInterp(Enum):
    black='MINISBLACK'
    white='MINISWHITE'
    rgb='RGB'
    cmyk='CMYK'
    ycbcr='YCbCr'
    cielab='CIELAB'
    icclab='ICCLAB'
    itulab='ITULAB'
