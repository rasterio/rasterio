import logging
import os
import re
import sys
import numpy

import rasterio
from rasterio.rio import warp


logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)


def test_warp_no_reproject(runner, tmpdir):
    """ When called without parameters, output should be same as source """
    srcname = 'tests/data/shade.tif'
    outputname = str(tmpdir.join('test.tif'))
    result = runner.invoke(warp.warp, [srcname, outputname])
    assert result.exit_code == 0
    assert os.path.exists(outputname)

    with rasterio.open(srcname) as src:
        with rasterio.open(outputname) as output:
            assert output.count == src.count
            assert output.crs == src.crs
            assert output.nodata == src.nodata
            assert numpy.allclose(output.bounds, src.bounds)
            assert output.affine.almost_equals(src.affine)
            assert numpy.allclose(output.read(1), src.read(1))


def test_warp_no_reproject_dimensions(runner, tmpdir):
    srcname = 'tests/data/shade.tif'
    outputname = str(tmpdir.join('test.tif'))
    result = runner.invoke(warp.warp, [srcname, outputname,
                                       '--dimensions', '100', '100'])
    assert result.exit_code == 0
    assert os.path.exists(outputname)

    with rasterio.open(srcname) as src:
        with rasterio.open(outputname) as output:
            assert output.crs == src.crs
            assert output.width == 100
            assert output.height == 100
            assert numpy.allclose([97.839396, 97.839396],
                                  [output.affine.a, -output.affine.e])


def test_warp_no_reproject_res(runner, tmpdir):
    srcname = 'tests/data/shade.tif'
    outputname = str(tmpdir.join('test.tif'))
    result = runner.invoke(warp.warp, [srcname, outputname,
                                       '--res', '30'])
    assert result.exit_code == 0
    assert os.path.exists(outputname)

    with rasterio.open(srcname) as src:
        with rasterio.open(outputname) as output:
            assert output.crs == src.crs
            assert numpy.allclose([30, 30], [output.affine.a, -output.affine.e])
            assert output.width == 327
            assert output.height == 327


def test_warp_no_reproject_bounds(runner, tmpdir):
    srcname = 'tests/data/shade.tif'
    outputname = str(tmpdir.join('test.tif'))
    out_bounds = [-11850000, 4810000, -11849000, 4812000]
    result = runner.invoke(warp.warp,[srcname, outputname,
                                      '--bounds'] + out_bounds)
    assert result.exit_code == 0
    assert os.path.exists(outputname)

    with rasterio.open(srcname) as src:
        with rasterio.open(outputname) as output:
            assert output.crs == src.crs
            assert numpy.allclose(output.bounds, out_bounds)
            assert numpy.allclose([src.affine.a, src.affine.e],
                                  [output.affine.a, output.affine.e])
            assert output.width == 105
            assert output.height == 210


def test_warp_no_reproject_bounds_res(runner, tmpdir):
    srcname = 'tests/data/shade.tif'
    outputname = str(tmpdir.join('test.tif'))
    out_bounds = [-11850000, 4810000, -11849000, 4812000]
    result = runner.invoke(warp.warp,[srcname, outputname,
                                      '--res', 30, '--bounds', ] + out_bounds)
    assert result.exit_code == 0
    assert os.path.exists(outputname)

    with rasterio.open(srcname) as src:
        with rasterio.open(outputname) as output:
            assert output.crs == src.crs
            assert numpy.allclose(output.bounds, out_bounds)
            assert numpy.allclose([30, 30], [output.affine.a, -output.affine.e])
            assert output.width == 34
            assert output.height == 67


def test_warp_reproject_dst_crs(runner, tmpdir):
    srcname = 'tests/data/RGB.byte.tif'
    outputname = str(tmpdir.join('test.tif'))
    result = runner.invoke(warp.warp, [srcname, outputname,
                                       '--dst-crs', 'EPSG:4326'])
    assert result.exit_code == 0
    assert os.path.exists(outputname)

    with rasterio.open(srcname) as src:
        with rasterio.open(outputname) as output:
            assert output.count == src.count
            assert output.crs == {'init': 'epsg:4326'}
            assert output.width == 824
            assert output.height == 686
            assert numpy.allclose(output.bounds,
                                  [-78.95864996545055, 23.564424693996177,
                                   -76.57259451863895, 25.550873767433984])


def test_warp_reproject_dst_crs_proj4(runner, tmpdir):
    proj4 = '+proj=longlat +ellps=WGS84 +datum=WGS84'
    srcname = 'tests/data/shade.tif'
    outputname = str(tmpdir.join('test.tif'))
    result = runner.invoke(warp.warp, [srcname, outputname,
                                       '--dst-crs', proj4])
    assert result.exit_code == 0
    assert os.path.exists(outputname)

    with rasterio.open(outputname) as output:
        assert output.crs == {'init': 'epsg:4326'}  # rasterio converts to EPSG


def test_warp_reproject_res(runner, tmpdir):
    srcname = 'tests/data/shade.tif'
    outputname = str(tmpdir.join('test.tif'))
    result = runner.invoke(warp.warp, [srcname, outputname,
                                       '--dst-crs', 'EPSG:4326',
                                       '--res', '0.01'])
    assert result.exit_code == 0
    assert os.path.exists(outputname)

    with rasterio.open(outputname) as output:
        assert output.crs == {'init': 'epsg:4326'}
        assert numpy.allclose([0.01, 0.01], [output.affine.a, -output.affine.e])
        assert output.width == 9
        assert output.height == 7


def test_warp_reproject_dimensions(runner, tmpdir):
    srcname = 'tests/data/shade.tif'
    outputname = str(tmpdir.join('test.tif'))
    result = runner.invoke(warp.warp, [srcname, outputname,
                                       '--dst-crs', 'EPSG:4326',
                                       '--dimensions', '100', '100'])
    assert result.exit_code == 0
    assert os.path.exists(outputname)

    with rasterio.open(srcname) as src:
        with rasterio.open(outputname) as output:
            assert output.crs == {'init': 'epsg:4326'}
            assert output.width == 100
            assert output.height == 100
            assert numpy.allclose([0.0008789062498762235, 0.0006771676143921468],
                                  [output.affine.a, -output.affine.e])


def test_warp_reproject_bounds_no_res(runner, tmpdir):
    srcname = 'tests/data/shade.tif'
    outputname = str(tmpdir.join('test.tif'))
    out_bounds = [-11850000, 4810000, -11849000, 4812000]
    result = runner.invoke(warp.warp, [srcname, outputname,
                                       '--dst-crs', 'EPSG:4326',
                                       '--bounds', ] + out_bounds)
    assert result.exit_code == 2


def test_warp_reproject_bounds_res(runner, tmpdir):
    srcname = 'tests/data/shade.tif'
    outputname = str(tmpdir.join('test.tif'))
    out_bounds = [-11850000, 4810000, -11849000, 4812000]
    result = runner.invoke(warp.warp, [srcname, outputname,
                                       '--dst-crs', 'EPSG:4326',
                                       '--res', 0.001, '--bounds', ]
                                       + out_bounds)
    assert result.exit_code == 0
    assert os.path.exists(outputname)

    with rasterio.open(srcname) as src:
        with rasterio.open(outputname) as output:
            assert output.crs == {'init': 'epsg:4326'}
            assert numpy.allclose(output.bounds[:],
                                  [-106.45036, 39.6138, -106.44136, 39.6278])
            assert numpy.allclose([0.001, 0.001],
                                  [output.affine.a, -output.affine.e])
            assert output.width == 9
            assert output.height == 14


def test_warp_reproject_like(runner, tmpdir):
    likename = str(tmpdir.join('like.tif'))
    kwargs = {
        "crs": {'init': 'epsg:4326'},
        "transform": (-106.523, 0.001, 0, 39.6395, 0, -0.001),
        "count": 1,
        "dtype": rasterio.uint8,
        "driver": "GTiff",
        "width": 10,
        "height": 10,
        "nodata": 0
    }

    with rasterio.drivers():
        with rasterio.open(likename, 'w', **kwargs) as dst:
            data = numpy.zeros((10, 10), dtype=rasterio.uint8)
            dst.write_band(1, data)

    srcname = 'tests/data/shade.tif'
    outputname = str(tmpdir.join('test.tif'))
    result = runner.invoke(warp.warp, [srcname, outputname,
                                       '--like', likename])
    assert result.exit_code == 0
    assert os.path.exists(outputname)

    with rasterio.open(outputname) as output:
        assert output.crs == {'init': 'epsg:4326'}
        assert numpy.allclose([0.001, 0.001], [output.affine.a, -output.affine.e])
        assert output.width == 10
        assert output.height == 10