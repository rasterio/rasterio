"""Tests of ground control points"""

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
