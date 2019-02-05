"""Tests of ground control points"""

import numpy
import pytest

import rasterio
from rasterio.control import GroundControlPoint


def test_gcp_empty():
    with pytest.raises(ValueError):
        GroundControlPoint()


def test_gcp():
    gcp = GroundControlPoint(1.0, 1.5, 100.0, 1000.0, z=0.0)
    assert gcp.row == 1.0
    assert gcp.col == 1.5
    assert gcp.x == 100.0
    assert gcp.y == 1000.0
    assert gcp.z == 0.0
    assert isinstance(gcp.id, str)


def test_gcp_repr():
    gcp = GroundControlPoint(1.0, 1.5, 100.0, 1000.0, id='foo', info='bar')
    copy = eval(repr(gcp))
    for attr in ('id', 'info', 'row', 'col', 'x', 'y', 'z'):
        assert getattr(copy, attr) == getattr(gcp, attr)


def test_gcp_dict():
    gcp = GroundControlPoint(1.0, 1.5, 100.0, 1000.0, id='foo', info='bar')
    assert gcp.asdict()['row'] == 1.0
    assert gcp.asdict()['col'] == 1.5
    assert gcp.asdict()['x'] == 100.0


def test_gcp_geo_interface():
    gcp = GroundControlPoint(1.0, 1.5, 100.0, 1000.0, id='foo', info='bar')
    assert gcp.__geo_interface__['geometry']['coordinates'] == (100.0, 1000.0)
    assert gcp.__geo_interface__['type'] == 'Feature'
    assert gcp.__geo_interface__['id'] == 'foo'
    assert gcp.__geo_interface__['properties']['info'] == 'bar'
    assert gcp.__geo_interface__['properties']['row'] == 1.0
    assert gcp.__geo_interface__['properties']['col'] == 1.5


def test_gcp_geo_interface_z():
    gcp = GroundControlPoint(1.0, 1.5, 100.0, 1000.0, z=0.0)
    assert gcp.__geo_interface__['geometry']['coordinates'] == (100.0, 1000.0, 0.0)


def test_write_read_gcps(tmpdir):
    tiffname = str(tmpdir.join('test.tif'))
    gcps = [GroundControlPoint(1, 1, 100.0, 1000.0, z=0.0)]

    with rasterio.open(tiffname, 'w', driver='GTiff', dtype='uint8', count=1,
                       width=10, height=10, crs='epsg:4326', gcps=gcps) as dst:
        pass

    with rasterio.open(tiffname, 'r+') as dst:
        gcps, crs = dst.gcps
        assert crs.to_epsg() == 4326
        assert len(gcps) == 1
        point = gcps[0]
        assert (1, 1) == (point.row, point.col)
        assert (100.0, 1000.0, 0.0) == (point.x, point.y, point.z)

        dst.gcps = [
            GroundControlPoint(1, 1, 100.0, 1000.0, z=0.0),
            GroundControlPoint(2, 2, 200.0, 2000.0, z=0.0)], crs

        gcps, crs = dst.gcps

        assert crs.to_epsg() == 4326
        assert len(gcps) == 2
        point = gcps[1]
        assert (2, 2) == (point.row, point.col)
        assert (200.0, 2000.0, 0.0) == (point.x, point.y, point.z)


def test_write_read_gcps_buffereddatasetwriter(tmpdir):
    filename = str(tmpdir.join('test.jpg'))
    gcps = [GroundControlPoint(1, 1, 100.0, 1000.0, z=0.0)]

    with rasterio.open(filename, 'w', driver='JPEG', dtype='uint8', count=3,
                       width=10, height=10, crs='epsg:4326', gcps=gcps) as dst:
        dst.write(numpy.ones((3, 10, 10), dtype='uint8'))

    with rasterio.open(filename, 'r+') as dst:
        gcps, crs = dst.gcps
        assert crs.to_epsg() == 4326
        assert len(gcps) == 1
        point = gcps[0]
        assert (1, 1) == (point.row, point.col)
        assert (100.0, 1000.0, 0.0) == (point.x, point.y, point.z)

        dst.gcps = [
            GroundControlPoint(1, 1, 100.0, 1000.0, z=0.0),
            GroundControlPoint(2, 2, 200.0, 2000.0, z=0.0)], crs

        gcps, crs = dst.gcps

        assert crs.to_epsg() == 4326
        assert len(gcps) == 2
        point = gcps[1]
        assert (2, 2) == (point.row, point.col)
        assert (200.0, 2000.0, 0.0) == (point.x, point.y, point.z)


def test_read_vrt_gcps(tmpdir):
    vrtfile = tmpdir.join('test.vrt')
    vrtfile.write("""
<VRTDataset rasterXSize="512" rasterYSize="512">
<GCPList Projection="EPSG:4326">
  <GCP Id="1" Info="a" Pixel="0.5" Line="0.5" X="0.0" Y="0.0" Z="0.0" />
  <GCP Id="2" Info="b" Pixel="13.5" Line="23.5" X="1.0" Y="2.0" Z="0.0" />
</GCPList>
  <GeoTransform>440720.0, 60.0, 0.0, 3751320.0, 0.0, -60.0</GeoTransform>
  <VRTRasterBand dataType="Byte" band="1">
    <ColorInterp>Gray</ColorInterp>
    <SimpleSource>
      <SourceFilename relativeToVRT="0">tests/data/RGB.byte.tif</SourceFilename>
      <SourceBand>1</SourceBand>
      <SrcRect xOff="0" yOff="0" xSize="512" ySize="512"/>
      <DstRect xOff="0" yOff="0" xSize="512" ySize="512"/>
    </SimpleSource>
  </VRTRasterBand>
</VRTDataset>""")
    with rasterio.open(str(vrtfile)) as src:
        gcps, crs = src.gcps
        assert crs.to_epsg() == 4326
        assert len(gcps) == 2
        assert [(0.5, 0.5), (13.5, 23.5)] == [(p.col, p.row) for p in gcps]
        assert ['1', '2'] == [p.id for p in gcps]
        assert ['a', 'b'] == [p.info for p in gcps]
