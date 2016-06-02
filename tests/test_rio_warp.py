import logging
import os
import sys

import numpy as np
import pytest

import rasterio
import rasterio.crs
from rasterio.rio import warp
from rasterio.rio.main import main_group


logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)


def test_dst_crs_error(runner, tmpdir):
    """Invalid JSON is a bad parameter."""
    srcname = 'tests/data/RGB.byte.tif'
    outputname = str(tmpdir.join('test.tif'))
    result = runner.invoke(main_group, [
        'warp', srcname, outputname, '--dst-crs', '{foo: bar}'])
    assert result.exit_code == 2
    assert 'for dst_crs: crs appears to be JSON but is not' in result.output


@pytest.mark.xfail(
    os.environ.get('GDALVERSION', 'a.b.c').startswith('1.9'),
                   reason="GDAL 1.9 doesn't catch this error")
def test_dst_crs_error_2(runner, tmpdir):
    """Invalid PROJ.4 is a bad parameter."""
    srcname = 'tests/data/RGB.byte.tif'
    outputname = str(tmpdir.join('test.tif'))
    result = runner.invoke(main_group, [
        'warp', srcname, outputname, '--dst-crs', '{"proj": "foobar"}'])
    assert result.exit_code == 2
    assert 'for dst_crs: Failed to initialize PROJ.4' in result.output


def test_dst_crs_error_epsg(runner, tmpdir):
    """Malformed EPSG string is a bad parameter."""
    srcname = 'tests/data/RGB.byte.tif'
    outputname = str(tmpdir.join('test.tif'))
    result = runner.invoke(main_group, [
        'warp', srcname, outputname, '--dst-crs', 'EPSG:'])
    assert result.exit_code == 2
    assert 'for dst_crs: invalid literal for int()' in result.output


def test_dst_crs_error_epsg_2(runner, tmpdir):
    """Invalid EPSG code is a bad parameter."""
    srcname = 'tests/data/RGB.byte.tif'
    outputname = str(tmpdir.join('test.tif'))
    result = runner.invoke(main_group, [
        'warp', srcname, outputname, '--dst-crs', 'EPSG:0'])
    assert result.exit_code == 2
    assert 'for dst_crs: EPSG codes are positive integers' in result.output


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
            assert np.allclose(output.bounds, src.bounds)
            assert output.affine.almost_equals(src.affine)
            assert np.allclose(output.read(1), src.read(1))


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
            assert np.allclose([97.839396, 97.839396],
                                  [output.affine.a, -output.affine.e])


def test_warp_no_reproject_res(runner, tmpdir):
    srcname = 'tests/data/shade.tif'
    outputname = str(tmpdir.join('test.tif'))
    result = runner.invoke(warp.warp, [srcname, outputname,
                                       '--res', 30])
    assert result.exit_code == 0
    assert os.path.exists(outputname)

    with rasterio.open(srcname) as src:
        with rasterio.open(outputname) as output:
            assert output.crs == src.crs
            assert np.allclose([30, 30], [output.affine.a, -output.affine.e])
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
            assert np.allclose(output.bounds, out_bounds)
            assert np.allclose([src.affine.a, src.affine.e],
                                  [output.affine.a, output.affine.e])
            assert output.width == 105
            assert output.height == 210


def test_warp_no_reproject_bounds_res(runner, tmpdir):
    srcname = 'tests/data/shade.tif'
    outputname = str(tmpdir.join('test.tif'))
    out_bounds = [-11850000, 4810000, -11849000, 4812000]
    result = runner.invoke(warp.warp,[srcname, outputname,
                                      '--res', 30,
                                      '--bounds', ] + out_bounds)
    assert result.exit_code == 0
    assert os.path.exists(outputname)

    with rasterio.open(srcname) as src:
        with rasterio.open(outputname) as output:
            assert output.crs == src.crs
            assert np.allclose(output.bounds, out_bounds)
            assert np.allclose([30, 30], [output.affine.a, -output.affine.e])
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
            assert output.width == 835
            assert output.height == 696
            assert np.allclose(output.bounds,
                                  [-78.95864996545055, 23.564787976164418,
                                   -76.5759177302349, 25.550873767433984])


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
                                       '--res', 0.01])
    assert result.exit_code == 0
    assert os.path.exists(outputname)

    with rasterio.open(outputname) as output:
        assert output.crs == {'init': 'epsg:4326'}
        assert np.allclose([0.01, 0.01], [output.affine.a, -output.affine.e])
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
            assert np.allclose([0.0008789062498762235, 0.0006771676143921468],
                                  [output.affine.a, -output.affine.e])


def test_warp_reproject_bounds_no_res(runner, tmpdir):
    srcname = 'tests/data/shade.tif'
    outputname = str(tmpdir.join('test.tif'))
    out_bounds = [-11850000, 4810000, -11849000, 4812000]
    result = runner.invoke(warp.warp, [srcname, outputname,
                                       '--dst-crs', 'EPSG:4326',
                                       '--bounds', ] + out_bounds)
    assert result.exit_code == 2


def test_warp_reproject_multi_bounds_fail(runner, tmpdir):
    """Mixing --bounds and --x-dst-bounds fails."""
    srcname = 'tests/data/shade.tif'
    outputname = str(tmpdir.join('test.tif'))
    out_bounds = [-11850000, 4810000, -11849000, 4812000]
    result = runner.invoke(warp.warp, [srcname, outputname,
                                       '--dst-crs', 'EPSG:4326',
                                       '--x-dst-bounds'] + out_bounds +
                                       ['--bounds'] + out_bounds)
    assert result.exit_code == 2


def test_warp_reproject_bounds_crossup_fail(runner, tmpdir):
    """Crossed-up bounds raises click.BadParameter."""
    srcname = 'tests/data/shade.tif'
    outputname = str(tmpdir.join('test.tif'))
    out_bounds = [-11850000, 4810000, -11849000, 4812000]
    result = runner.invoke(warp.warp, [srcname, outputname,
                                       '--dst-crs', 'EPSG:4326',
                                       '--res', 0.001, '--x-dst-bounds', ]
                                       + out_bounds)
    assert result.exit_code == 2


def test_warp_reproject_bounds_res_future_warning(runner, tmpdir):
    """Use of --bounds results in a warning from the 1.0 future."""
    srcname = 'tests/data/shade.tif'
    outputname = str(tmpdir.join('test.tif'))
    out_bounds = [-11850000, 4810000, -11849000, 4812000]
    result = runner.invoke(
                warp.warp, [srcname, outputname, '--dst-crs', 'EPSG:4326',
                            '--res', 0.001, '--bounds'] + out_bounds)
    assert "Future Warning" in result.output


def test_warp_reproject_src_bounds_res(runner, tmpdir):
    """--src-bounds option works."""
    srcname = 'tests/data/shade.tif'
    outputname = str(tmpdir.join('test.tif'))
    out_bounds = [-11850000, 4810000, -11849000, 4812000]
    result = runner.invoke(
        warp.warp, [srcname, outputname, '--dst-crs', 'EPSG:4326',
                    '--res', 0.001, '--src-bounds'] + out_bounds)
    assert result.exit_code == 0
    assert os.path.exists(outputname)

    with rasterio.open(srcname) as src:
        with rasterio.open(outputname) as output:
            assert output.crs == {'init': 'epsg:4326'}
            assert np.allclose(output.bounds[:],
                                  [-106.45036, 39.6138, -106.44136, 39.6278])
            assert np.allclose([0.001, 0.001],
                                  [output.affine.a, -output.affine.e])
            assert output.width == 9
            assert output.height == 14


def test_warp_reproject_dst_bounds(runner, tmpdir):
    """--x-dst-bounds option works."""
    srcname = 'tests/data/shade.tif'
    outputname = str(tmpdir.join('test.tif'))
    out_bounds = [-106.45036, 39.6138, -106.44136, 39.6278]
    result = runner.invoke(
        warp.warp, [srcname, outputname, '--dst-crs', 'EPSG:4326',
                    '--res', 0.001, '--x-dst-bounds'] + out_bounds)
    assert result.exit_code == 0
    assert os.path.exists(outputname)

    with rasterio.open(srcname) as src:
        with rasterio.open(outputname) as output:
            assert output.crs == {'init': 'epsg:4326'}
            assert np.allclose(output.bounds[0::3],
                                  [-106.45036, 39.6278])
            assert np.allclose([0.001, 0.001],
                                  [output.affine.a, -output.affine.e])

            # XXX: an extra row and column is produced in the dataset
            # because we're using ceil instead of floor internally.
            # Not necessarily a bug, but may change in the future.
            assert np.allclose([output.bounds[2]-0.001, output.bounds[1]+0.001],
                                  [-106.44136, 39.6138])
            assert output.width == 10
            assert output.height == 15


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
            data = np.zeros((10, 10), dtype=rasterio.uint8)
            dst.write(data, indexes=1)

    srcname = 'tests/data/shade.tif'
    outputname = str(tmpdir.join('test.tif'))
    result = runner.invoke(warp.warp, [srcname, outputname,
                                       '--like', likename])
    assert result.exit_code == 0
    assert os.path.exists(outputname)

    with rasterio.open(outputname) as output:
        assert output.crs == {'init': 'epsg:4326'}
        assert np.allclose([0.001, 0.001], [output.affine.a, -output.affine.e])
        assert output.width == 10
        assert output.height == 10


def test_warp_reproject_nolostdata(runner, tmpdir):
    srcname = 'tests/data/world.byte.tif'
    outputname = str(tmpdir.join('test.tif'))
    result = runner.invoke(warp.warp, [srcname, outputname,
                                       '--dst-crs', 'EPSG:3857'])
    assert result.exit_code == 0
    assert os.path.exists(outputname)

    with rasterio.open(outputname) as output:
        arr = output.read()
        # 50 column swath on the right edge should have some ones (gdalwarped has 7223)
        assert arr[0, :, -50:].sum() > 7000
        assert output.crs == {'init': 'epsg:3857'}


def test_warp_dst_crs_empty_string(runner, tmpdir):
    """`$ rio warp --dst-crs ''` used to perform a falsey check that would treat
    `--dst-crs ''` as though `--dst-crs` was not supplied at all.  If the user
    gives any value we should let `rasterio.crs.from_string()` handle the
    validation.
    """

    infile = 'tests/data/RGB.byte.tif'
    outfile = str(tmpdir.mkdir('empty_warp_dst_crs.tif').join('test.tif'))

    result = runner.invoke(warp.warp, [
        infile,
        outfile,
        '--dst-crs', ''])

    assert result.exit_code != 0
    assert 'empty or invalid' in result.output


def test_warp_badcrs_dimensions(runner, tmpdir):
    srcname = 'tests/data/shade.tif'
    outputname = str(tmpdir.join('test.tif'))
    result = runner.invoke(warp.warp, [srcname, outputname,
                                       '--dst-crs', '{"init": "epsg:-1"}',
                                       '--dimensions', '100', '100'])
    assert result.exit_code == 2
    assert "Invalid value for dst_crs" in result.output


def test_warp_badcrs_src_bounds(runner, tmpdir):
    srcname = 'tests/data/shade.tif'
    outputname = str(tmpdir.join('test.tif'))
    out_bounds = [-11850000, 4810000, -11849000, 4812000]
    result = runner.invoke(
        warp.warp, [srcname, outputname,
                    '--dst-crs', '{"init": "epsg:-1"}',
                    '--res', 0.001, '--src-bounds'] + out_bounds)
    assert result.exit_code == 2
    assert "Invalid value for dst_crs" in result.output


@pytest.mark.xfail
def test_warp_reproject_check_invert(runner, tmpdir):
    srcname = 'tests/data/world.rgb.tif'
    outputname = str(tmpdir.join('test.tif'))
    result = runner.invoke(warp.warp, [srcname, outputname,
                                       '--check-invert-proj', 'yes',
                                       '--dst-crs', 'EPSG:3759'])
    assert result.exit_code == 0
    assert os.path.exists(outputname)

    with rasterio.open(outputname) as output:
        assert output.crs == {'init': 'epsg:3759'}
        shape1 = output.shape

    output2name = str(tmpdir.join('test2.tif'))
    result = runner.invoke(warp.warp, [srcname, output2name,
                                       '--check-invert-proj', 'no',
                                       '--dst-crs', 'EPSG:3759'])
    assert result.exit_code == 0
    assert os.path.exists(output2name)

    with rasterio.open(output2name) as output:
        assert output.crs == {'init': 'epsg:3759'}
        assert output.shape != shape1
