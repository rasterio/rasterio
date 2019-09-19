#-*- coding: utf-8 -*-
import logging
import sys

import rasterio

logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)


def test_get_tag_item():
    """Should return the correct list of tag namespaces."""
    with rasterio.open('tests/data/cogeo.tif') as src:
        assert src.get_tag_ns() == ['IMAGE_STRUCTURE', 'DERIVED_SUBDATASETS']

    with rasterio.open('tests/data/cogeo.tif') as src:
        assert src.get_tag_ns(bidx=1) == []
