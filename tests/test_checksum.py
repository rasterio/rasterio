import rasterio


def test_checksum_band():
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        checksums = [src.checksum(i) for i in src.indexes]
        assert checksums == [25420, 29131, 37860]


def test_checksum_band_window():
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        window = ((0, src.height), (0, src.width))
        checksums = [src.checksum(i, window=window) for i in src.indexes]
        assert checksums == [25420, 29131, 37860]


def test_checksum_band_window_min():
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        window = ((0, 1), (0, 1))
        checksums = [src.checksum(i, window=window) for i in src.indexes]
        assert checksums == [0, 0, 0]


def test_checksum_band_window_quarter():
    """A quarter window's checksum is different from the full image's"""
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        window = ((0, src.height//2), (0, src.width//2))
        checksums = [src.checksum(i, window=window) for i in src.indexes]
        assert checksums != [25420, 29131, 37860]


def test_checksum_band_window_too_tall():
    """Windows get truncated to maximum extent"""
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        window = ((0, 10000), (0, src.width))
        checksums = [src.checksum(i, window=window) for i in src.indexes]
        assert checksums == [25420, 29131, 37860]


def test_checksum_band_window_too_short():
    """Negative values in windows get evaluated properly"""
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        window = ((0, -1), (0, src.width))
        checksums = [src.checksum(i, window=window) for i in src.indexes]
        assert checksums == [25420, 29131, 37860]
