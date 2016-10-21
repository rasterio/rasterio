"""Tests of ground control points"""

import rasterio
from rasterio.control import GroundControlPoint


def test_gcp_empty():
    gcp = GroundControlPoint()
    assert gcp.row is None
    assert gcp.col is None
    assert gcp.x is None
    assert gcp.y is None
    assert gcp.z is None


def test_gcp():
    gcp = GroundControlPoint(row=1, col=1, x=100.0, y=1000.0, z=0.0)
    assert gcp.row == 1
    assert gcp.col == 1
    assert gcp.x == 100.0
    assert gcp.y == 1000.0
    assert gcp.z == 0.0


def test_write_read_gcps(tmpdir):
    tiffname = str(tmpdir.join('test.tif'))
    gcps = [GroundControlPoint(row=1, col=1, x=100.0, y=1000.0, z=0.0)]

    with rasterio.open(tiffname, 'w', driver='GTiff', dtype='uint8', count=1,
                       width=10, height=10, crs='epsg:4326', gcps=gcps) as dst:
        pass

    with rasterio.open(tiffname, 'r+') as dst:
        assert len(dst.gcps) == 1
        point = dst.gcps[0]
        assert (1, 1) == (point.row, point.col)
        assert (100.0, 1000.0, 0.0) == (point.x, point.y, point.z)

        dst.gcps = [
            GroundControlPoint(row=1, col=1, x=100.0, y=1000.0, z=0.0),
            GroundControlPoint(row=2, col=2, x=200.0, y=2000.0, z=0.0)]

        assert len(dst.gcps) == 2
        point = dst.gcps[1]
        assert (2, 2) == (point.row, point.col)
        assert (200.0, 2000.0, 0.0) == (point.x, point.y, point.z)
