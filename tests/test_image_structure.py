import rasterio
from rasterio.enums import Compression, Interleaving


def test_enum_compression_JPEG():
    assert Compression('JPEG').name == 'jpeg'


def test_enum_compression_LZW():
    assert Compression('LZW').name == 'lzw'


def test_enum_compression_PACKBITS():
    assert Compression('PACKBITS').name == 'packbits'


def test_enum_compression_DEFLATE():
    assert Compression('DEFLATE').name == 'deflate'


def test_enum_compression_CCITTRLE():
    assert Compression('CCITTRLE').name == 'ccittrle'


def test_enum_compression_CCITTFAX3():
    assert Compression('CCITTFAX3').name == 'ccittfax3'


def test_enum_compression_CCITTFAX4():
    assert Compression('CCITTFAX4').name == 'ccittfax4'


def test_enum_compression_LZMA():
    assert Compression('LZMA').name == 'lzma'


def test_enum_compression_NONE():
    assert Compression('NONE').name == 'none'


def test_compression_none():
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        assert src.compression is None
        assert 'compress' not in src.profile


def test_compression_deflate():
    with rasterio.open('tests/data/rgb_deflate.tif') as src:
        assert src.compression.name == 'deflate'
        assert src.compression.value == 'DEFLATE'
        assert src.profile['compress'] == 'deflate'


def test_enum_interleaving_BAND():
    assert Interleaving('BAND').name == 'band'


def test_enum_interleaving_PIXEL():
    assert Interleaving('PIXEL').name == 'pixel'


def test_interleaving_pixel():
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        assert src.interleaving.name == 'pixel'
        assert src.interleaving.value == 'PIXEL'
        assert src.profile['interleave'] == 'pixel'


def test_interleaving_pixel():
    with rasterio.open('tests/data/rgb_deflate.tif') as src:
        assert src.interleaving.name == 'band'
        assert src.interleaving.value == 'BAND'
        assert src.profile['interleave'] == 'band'
