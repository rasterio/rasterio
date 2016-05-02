from rasterio.errors import NodataShadowWarning


def test_nodata_shadow():
    assert str(NodataShadowWarning()) == (
        "The dataset's nodata attribute is shadowing "
        "the alpha band. All masks will be determined "
        "by the nodata attribute")
