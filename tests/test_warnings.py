import logging

import rasterio
from rasterio.errors import NodataShadowWarning, NotGeoreferencedWarning
from affine import Affine
import pytest

log = logging.getLogger(__name__)


def gen_rpcs():
    with rasterio.open('tests/data/RGB.byte.rpc.vrt') as src:
        return src.rpcs


def test_nodata_shadow():
    assert str(NodataShadowWarning()) == (
        "The dataset's nodata attribute is shadowing "
        "the alpha band. All masks will be determined "
        "by the nodata attribute")


def test_notgeoref_warning():
    with rasterio.MemoryFile() as mem:
        with mem.open(driver='GTiff', width=10, height=10, dtype='uint8', count=1) as src:
            pass
        with pytest.warns(NotGeoreferencedWarning):
            with mem.open() as dst:
                pass


@pytest.mark.parametrize('transform, gcps, rpcs', [(Affine.identity() * Affine.scale(2.0), None, None),
                                                   (None, [rasterio.control.GroundControlPoint(0, 0, 0, 0, 0)], None),
                                                   (None, None, gen_rpcs())])
def test_no_notgeoref_warning(transform, gcps, rpcs):
    with rasterio.MemoryFile() as mem:
        with mem.open(driver='GTiff', width=10, height=10, dtype='uint8', count=1, transform=transform) as src:
            if gcps:
                src.gcps = (gcps, rasterio.crs.CRS.from_epsg(4326))
            if rpcs:
                src.rpcs = rpcs

        with pytest.warns(None) as record:
            with mem.open() as dst:
                pass
        
        assert len(record) == 0
