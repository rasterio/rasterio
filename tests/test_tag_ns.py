# -*- coding: utf-8 -*-

import rasterio


def test_get_tag_item():
    """Should return the correct list of dataset tag namespaces."""
    with rasterio.open('tests/data/cogeo.tif') as src:
        assert src.tag_namespaces() == ['IMAGE_STRUCTURE', 'DERIVED_SUBDATASETS']


def test_get_tag_item():
    """Should return the correct list of band tag namespaces."""
    with rasterio.open('tests/data/cogeo.tif') as src:
        assert src.tag_namespaces(bidx=1) == []
