import rasterio


def test_copy(tmpdir, path_rgb_byte_tif):
    outfile = str(tmpdir.join('test_copy.tif'))
    rasterio.copy(
        path_rgb_byte_tif,
        outfile,
        # Test a mix of boolean, ints, and strings to make sure creation
        # options passed as Python types are properly cast.
        tiled=True,
        blockxsize=512,
        BLOCKYSIZE='256')
    with rasterio.open(outfile) as src:
        assert src.driver == 'GTiff'
        assert set(src.block_shapes) == {(256, 512)}
