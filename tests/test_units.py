import rasterio
from rasterio.profiles import default_gtiff_profile


def test_set_units(tmpdir):
    """Units can be set when dataset is open"""
    tmptiff = str(tmpdir.join('test.tif'))
    with rasterio.open(
            tmptiff, 'w', count=2, height=256, width=256,
            **default_gtiff_profile) as dst:
        assert dst.units == ('', '')
        dst.units = ['meters', 'degC']
        assert dst.units == ('meters', 'degC')
