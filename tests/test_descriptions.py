import rasterio
from rasterio.profiles import default_gtiff_profile


def test_set_band_descriptions(tmpdir):
    """Descriptions can be set when dataset is open"""
    tmptiff = str(tmpdir.join('test.tif'))
    with rasterio.open(
            tmptiff, 'w', count=2, height=256, width=256,
            **default_gtiff_profile) as dst:
        assert dst.descriptions == (None, None)
        dst.set_description(1, "this is a test band")
        dst.set_description(2, "this is another test band")
        assert dst.descriptions == (
            "this is a test band", "this is another test band")
