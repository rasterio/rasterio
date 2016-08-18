import rasterio
from rasterio.profiles import default_gtiff_profile


def test_dataset_description():
    """We get the GDAL default descriptions if nothing else"""
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        assert src.description == 'tests/data/RGB.byte.tif'


def test_band_descriptions_creation(tmpdir):
    """Value in constructor is broadcast to bands"""
    tmptiff = str(tmpdir.join('test.tif'))
    with rasterio.open(
            tmptiff, 'w', count=2, description="this is a test", height=256,
            width=256, **default_gtiff_profile) as dst:
        assert dst.band_descriptions == ("this is a test", "this is a test")


def test_set_band_descriptions(tmpdir):
    """Descriptions can be set when dataset is open"""
    tmptiff = str(tmpdir.join('test.tif'))
    with rasterio.open(
            tmptiff, 'w', count=2, height=256, width=256,
            **default_gtiff_profile) as dst:
        assert dst.band_descriptions == ("", "")
        dst.set_band_description(1, "this is a test band")
        dst.set_band_description(2, "this is another test band")
        assert dst.band_descriptions == (
            "this is a test band", "this is another test band")
