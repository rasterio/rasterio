import rasterio


def test_get_tag_namespaces_dataset():
    """Should return the correct list of dataset tag namespaces."""
    with rasterio.open('tests/data/cogeo.tif') as src:
        assert src.tag_namespaces() == ['IMAGE_STRUCTURE', 'DERIVED_SUBDATASETS']


def test_get_tag_namespaces_band():
    """Should return the correct list of band tag namespaces."""
    with rasterio.open('tests/data/cogeo.tif') as src:
        assert src.tag_namespaces(bidx=1) == []
