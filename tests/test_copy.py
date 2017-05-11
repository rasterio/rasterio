import rasterio


def test_copy(tmpdir, path_rgb_byte_tif):
    outfile = str(tmpdir.join('test_copy.tif'))
    rasterio.copy(
        path_rgb_byte_tif,
        outfile)
    with rasterio.open(outfile) as src:
        assert src.driver == 'GTiff'
