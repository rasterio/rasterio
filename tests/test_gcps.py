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
        assert len(src.gcps) == 2
        assert [(0.5, 0.5), (13.5, 23.5)] == [(p.col, p.row) for p in src.gcps]
