import rasterio


def test_profile_format():
    assert rasterio.default_gtiff_profile()['driver'] == 'GTiff'


def test_profile_interleave():
    assert rasterio.default_gtiff_profile()['interleave'] == 'band'


def test_profile_tiled():
    assert rasterio.default_gtiff_profile()['tiled'] == True


def test_profile_blockxsize():
    assert rasterio.default_gtiff_profile()['blockxsize'] == 256


def test_profile_blockysize():
    assert rasterio.default_gtiff_profile()['blockysize'] == 256


def test_profile_compress():
    assert rasterio.default_gtiff_profile()['compress'] == 'lzw'


def test_profile_nodata():
    assert rasterio.default_gtiff_profile()['nodata'] == 0


def test_profile_dtype():
    assert rasterio.default_gtiff_profile()['dtype'] == rasterio.uint8


def test_profile_other():
    assert rasterio.default_gtiff_profile(count=3)['count'] == 3


def test_open_with_profile(tmpdir):
        tiffname = str(tmpdir.join('foo.tif'))
        with rasterio.open(
                tiffname,
                'w',
                **rasterio.default_gtiff_profile(
                    count=1, width=1, height=1)) as dst:
            data = dst.read()
            assert data.flatten().tolist() == [0]
