"""Unittests for $ rio merge"""


import os
import sys
import textwrap

import affine
from click.testing import CliRunner
import numpy as np
from pytest import fixture
import pytest

import rasterio
from rasterio import Path
from rasterio.enums import Resampling
from rasterio.merge import merge
from rasterio.rio.main import main_group
from rasterio.transform import Affine

from .conftest import requires_gdal22, gdal_version


# Fixture to create test datasets within temporary directory
@fixture(scope='function')
def test_data_dir_1(tmpdir):
    kwargs = {
        "crs": {'init': 'epsg:4326'},
        "transform": affine.Affine(0.2, 0, -114,
                                   0, -0.2, 46),
        "count": 1,
        "dtype": rasterio.uint8,
        "driver": "GTiff",
        "width": 10,
        "height": 10,
        "nodata": 1
    }

    with rasterio.open(str(tmpdir.join('b.tif')), 'w', **kwargs) as dst:
        data = np.ones((10, 10), dtype=rasterio.uint8)
        data[0:6, 0:6] = 255
        dst.write(data, indexes=1)

    with rasterio.open(str(tmpdir.join('a.tif')), 'w', **kwargs) as dst:
        data = np.ones((10, 10), dtype=rasterio.uint8)
        data[4:8, 4:8] = 254
        dst.write(data, indexes=1)

    return tmpdir


@fixture(scope='function')
def test_data_dir_2(tmpdir):
    kwargs = {
        "crs": {'init': 'epsg:4326'},
        "transform": affine.Affine(0.2, 0, -114,
                                   0, -0.2, 46),
        "count": 1,
        "dtype": rasterio.uint8,
        "driver": "GTiff",
        "width": 10,
        "height": 10
        # these files have undefined nodata.
    }

    with rasterio.open(str(tmpdir.join('b.tif')), 'w', **kwargs) as dst:
        data = np.zeros((10, 10), dtype=rasterio.uint8)
        data[0:6, 0:6] = 255
        dst.write(data, indexes=1)

    with rasterio.open(str(tmpdir.join('a.tif')), 'w', **kwargs) as dst:
        data = np.zeros((10, 10), dtype=rasterio.uint8)
        data[4:8, 4:8] = 254
        dst.write(data, indexes=1)

    return tmpdir


@fixture(scope='function')
def test_data_dir_3(tmpdir):
    kwargs = {
        "crs": {'init': 'epsg:4326'},
        "transform": affine.Affine(0.2, 0, -114,
                                   0, -0.2, 46),
        "count": 2,  # important: band count > 1
        "dtype": rasterio.uint8,
        "driver": "GTiff",
        "width": 10,
        "height": 10,
        "nodata": 1
    }

    with rasterio.open(str(tmpdir.join('b.tif')), 'w', **kwargs) as dst:
        data = np.ones((2, 10, 10), dtype=rasterio.uint8)
        data[:, 0:6, 0:6] = 255
        dst.write(data)

    with rasterio.open(str(tmpdir.join('a.tif')), 'w', **kwargs) as dst:
        data = np.ones((2, 10, 10), dtype=rasterio.uint8)
        data[:, 4:8, 4:8] = 254
        dst.write(data)

    return tmpdir


def test_merge_with_colormap(test_data_dir_1, runner):
    outputname = str(test_data_dir_1.join('merged.tif'))
    inputs = [str(x) for x in test_data_dir_1.listdir()]
    inputs.sort()

    for inputname in inputs:
        with rasterio.open(inputname, 'r+') as src:
            src.write_colormap(1, {0: (255, 0, 0, 255), 255: (0, 0, 0, 255)})

    result = runner.invoke(main_group, ['merge'] + inputs + [outputname])
    assert result.exit_code == 0
    assert os.path.exists(outputname)

    with rasterio.open(outputname) as out:
        cmap = out.colormap(1)
        assert cmap[0] == (255, 0, 0, 255)
        assert cmap[255] == (0, 0, 0, 255)


@requires_gdal22(
    reason="This test is sensitive to pixel values and requires GDAL 2.2+")
def test_merge_with_nodata(test_data_dir_1, runner):
    outputname = str(test_data_dir_1.join('merged.tif'))
    inputs = [str(x) for x in test_data_dir_1.listdir()]
    inputs.sort()
    result = runner.invoke(main_group, ['merge'] + inputs + [outputname])
    assert result.exit_code == 0
    assert os.path.exists(outputname)
    with rasterio.open(outputname) as out:
        assert out.count == 1
        data = out.read(1, masked=False)
        expected = np.ones((10, 10), dtype=rasterio.uint8)
        expected[0:6, 0:6] = 255
        expected[4:8, 4:8] = 254
        assert np.all(data == expected)


@pytest.mark.filterwarnings("ignore:Input file's nodata value")
def test_merge_error(test_data_dir_1, runner):
    """A nodata value outside the valid range results in an error"""
    outputname = str(test_data_dir_1.join('merged.tif'))
    inputs = [str(x) for x in test_data_dir_1.listdir()]
    inputs.sort()
    result = runner.invoke(
        main_group, ['merge'] + inputs + [outputname] + ['--nodata', '-1'])
    assert result.exit_code


def test_merge_bidx(test_data_dir_3, runner):
    outputname = str(test_data_dir_3.join('merged.tif'))
    inputs = [str(x) for x in test_data_dir_3.listdir()]
    inputs.sort()
    result = runner.invoke(
        main_group, ['merge'] + inputs + [outputname] + ['--bidx', '1'])
    assert result.exit_code == 0
    assert os.path.exists(outputname)
    with rasterio.open(inputs[0]) as src:
        assert src.count > 1
    with rasterio.open(outputname) as out:
        assert out.count == 1


@requires_gdal22(
    reason="This test is sensitive to pixel values and requires GDAL 2.2+")
def test_merge_without_nodata(test_data_dir_2, runner):
    outputname = str(test_data_dir_2.join('merged.tif'))
    inputs = [str(x) for x in test_data_dir_2.listdir()]
    inputs.sort()
    result = runner.invoke(main_group, ['merge'] + inputs + [outputname])
    assert result.exit_code == 0
    assert os.path.exists(outputname)
    with rasterio.open(outputname) as out:
        assert out.count == 1
        data = out.read(1, masked=False)
        expected = np.zeros((10, 10), dtype=rasterio.uint8)
        expected[0:6, 0:6] = 255
        expected[4:8, 4:8] = 254
        assert np.all(data == expected)


def test_merge_output_exists(tmpdir, runner):
    outputname = str(tmpdir.join('merged.tif'))
    result = runner.invoke(
        main_group, ['merge', 'tests/data/RGB.byte.tif', outputname])
    assert result.exit_code == 0
    result = runner.invoke(
        main_group, ['merge', 'tests/data/RGB.byte.tif', outputname])
    assert os.path.exists(outputname)
    with rasterio.open(outputname) as out:
        assert out.count == 3


def test_merge_output_exists_without_nodata_fails(test_data_dir_2, runner):
    """Fails without --overwrite"""
    result = runner.invoke(
        main_group, [
            'merge', str(test_data_dir_2.join('a.tif')),
            str(test_data_dir_2.join('b.tif'))])
    assert result.exit_code == 1


def test_merge_output_exists_without_nodata(test_data_dir_2, runner):
    """Succeeds with --overwrite"""
    result = runner.invoke(
        main_group, [
            'merge', '--overwrite', str(test_data_dir_2.join('a.tif')),
            str(test_data_dir_2.join('b.tif'))])
    assert result.exit_code == 0


def test_merge_err(runner):
    result = runner.invoke(
        main_group, ['merge', 'tests'])
    assert result.exit_code == 1


def test_format_jpeg(tmpdir, runner):
    outputname = str(tmpdir.join('stacked.jpg'))
    result = runner.invoke(
        main_group, [
            'merge', 'tests/data/RGB.byte.tif', outputname,
            '--format', 'JPEG'])
    assert result.exit_code == 0
    assert os.path.exists(outputname)


# Non-coincident datasets test fixture.
# Two overlapping GeoTIFFs, one to the NW and one to the SE.
@fixture(scope='function')
def test_data_dir_overlapping(tmpdir):
    kwargs = {
        "crs": {'init': 'epsg:4326'},
        "transform": affine.Affine(0.2, 0, -114,
                                   0, -0.2, 46),
        "count": 1,
        "dtype": rasterio.uint8,
        "driver": "GTiff",
        "width": 10,
        "height": 10,
        "nodata": 0
    }

    with rasterio.open(str(tmpdir.join('se.tif')), 'w', **kwargs) as dst:
        data = np.ones((10, 10), dtype=rasterio.uint8)
        dst.write(data, indexes=1)

    kwargs['transform'] = affine.Affine(0.2, 0, -113,
                                        0, -0.2, 45)
    with rasterio.open(str(tmpdir.join('nw.tif')), 'w', **kwargs) as dst:
        data = np.ones((10, 10), dtype=rasterio.uint8) * 2
        dst.write(data, indexes=1)

    return tmpdir


def test_merge_overlapping(test_data_dir_overlapping, runner):
    outputname = str(test_data_dir_overlapping.join('merged.tif'))
    inputs = [str(x) for x in test_data_dir_overlapping.listdir()]
    inputs.sort()
    result = runner.invoke(main_group, ['merge'] + inputs + [outputname])
    assert result.exit_code == 0
    assert os.path.exists(outputname)
    with rasterio.open(outputname) as out:
        assert out.count == 1
        assert out.shape == (15, 15)
        assert out.bounds == (-114, 43, -111, 46)
        data = out.read(1, masked=False)
        expected = np.zeros((15, 15), dtype=rasterio.uint8)
        expected[0:10, 0:10] = 1
        expected[5:, 5:] = 2
        assert np.all(data == expected)


def test_merge_overlapping_callable_long(test_data_dir_overlapping, runner):
    inputs = [str(x) for x in test_data_dir_overlapping.listdir()]
    datasets = [rasterio.open(x) for x in inputs]
    test_merge_overlapping_callable_long.index = 0

    def mycallable(old_data, new_data, old_nodata, new_nodata,
                   index=None, roff=None, coff=None):
        assert old_data.shape[0] == 5
        assert new_data.shape[0] == 1
        assert test_merge_overlapping_callable_long.index == index
        test_merge_overlapping_callable_long.index += 1

    merge(datasets, output_count=5, method=mycallable)


def test_custom_callable_merge(test_data_dir_overlapping, runner):
    inputs = ['tests/data/world.byte.tif'] * 3
    datasets = [rasterio.open(x) for x in inputs]
    output_count = 4

    def mycallable(old_data, new_data, old_nodata, new_nodata,
                   index=None, roff=None, coff=None):
        # input data are bytes, test output doesn't overflow
        old_data[index] = (
            index + 1
        ) * 259  # use a number > 255 but divisible by 3 for testing
        # update additional band that we specified in output_count
        old_data[3, :, :] += index

    arr, _ = merge(datasets, output_count=output_count, method=mycallable, dtype=np.uint64)

    np.testing.assert_array_equal(np.mean(arr[:3], axis=0), 518)
    np.testing.assert_array_equal(arr[3, :, :], 3)


# Fixture to create test datasets within temporary directory
@fixture(scope='function')
def test_data_dir_float(tmpdir):
    kwargs = {
        "crs": {'init': 'epsg:4326'},
        "transform": affine.Affine(0.2, 0, -114,
                                   0, -0.2, 46),
        "count": 1,
        "dtype": rasterio.float64,
        "driver": "GTiff",
        "width": 10,
        "height": 10,
        "nodata": 0
    }

    with rasterio.open(str(tmpdir.join('two.tif')), 'w', **kwargs) as dst:
        data = np.zeros((10, 10), dtype=rasterio.float64)
        data[0:6, 0:6] = 255
        dst.write(data, indexes=1)

    with rasterio.open(str(tmpdir.join('one.tif')), 'w', **kwargs) as dst:
        data = np.zeros((10, 10), dtype=rasterio.float64)
        data[4:8, 4:8] = 254
        dst.write(data, indexes=1)
    return tmpdir


@requires_gdal22(
    reason="This test is sensitive to pixel values and requires GDAL 2.2+")
def test_merge_float(test_data_dir_float, runner):
    outputname = str(test_data_dir_float.join('merged.tif'))
    inputs = [str(x) for x in test_data_dir_float.listdir()]
    inputs.sort()
    result = runner.invoke(
        main_group, ['merge'] + inputs + [outputname] + ['--nodata', '-1.5'])
    assert result.exit_code == 0
    assert os.path.exists(outputname)
    with rasterio.open(outputname) as out:
        assert out.count == 1
        data = out.read(1, masked=False)
        expected = np.ones((10, 10), dtype=rasterio.float64) * -1.5
        expected[0:6, 0:6] = 255
        expected[4:8, 4:8] = 254
        assert np.all(data == expected)


# Test below comes from issue #288. There was an off-by-one error in
# pasting image data into the canvas array.

@fixture(scope='function')
def tiffs(tmpdir):

    data = np.ones((1, 1, 1), 'uint8')

    kwargs = {
        'count': '1',
        'driver': 'GTiff',
        'dtype': 'uint8',
        'height': 1,
        'width': 1}

    kwargs['transform'] = Affine(1, 0, 1,
                                 0, -1, 1)
    with rasterio.open(str(tmpdir.join('a-sw.tif')), 'w', **kwargs) as r:
        r.write(data * 40)

    kwargs['transform'] = Affine(1, 0, 2,
                                 0, -1, 2)
    with rasterio.open(str(tmpdir.join('b-ct.tif')), 'w', **kwargs) as r:
        r.write(data * 60)

    kwargs['transform'] = Affine(2, 0, 3,
                                 0, -2, 4)
    with rasterio.open(str(tmpdir.join('c-ne.tif')), 'w', **kwargs) as r:
        r.write(data * 90)

    kwargs['transform'] = Affine(2, 0, 2,
                                 0, -2, 4)
    with rasterio.open(str(tmpdir.join('d-ne.tif')), 'w', **kwargs) as r:
        r.write(data * 120)

    return tmpdir


def test_merge_tiny_base(tiffs, runner):
    outputname = str(tiffs.join('merged.tif'))
    inputs = [str(x) for x in tiffs.listdir()]
    inputs.sort()
    result = runner.invoke(main_group, ['merge'] + inputs + [outputname])
    assert result.exit_code == 0

    # Output should be
    #
    # [[  0 120  90  90]
    #  [  0 120  90  90]
    #  [  0  60   0   0]
    #  [ 40   0   0   0]]

    with rasterio.open(outputname) as src:
        data = src.read()
        print(data)
        assert (data[0][0:2, 1] == 120).all()
        assert (data[0][0:2, 2:4] == 90).all()
        assert data[0][2][1] == 60
        assert data[0][3][0] == 40


def test_merge_tiny_output_opt(tiffs, runner):
    outputname = str(tiffs.join('merged.tif'))
    inputs = [str(x) for x in tiffs.listdir()]
    inputs.sort()
    result = runner.invoke(main_group, ['merge'] + inputs + ['-o', outputname])
    assert result.exit_code == 0

    # Output should be
    #
    # [[  0 120  90  90]
    #  [  0 120  90  90]
    #  [  0  60   0   0]
    #  [ 40   0   0   0]]

    with rasterio.open(outputname) as src:
        data = src.read()
        assert (data[0][0:2, 1] == 120).all()
        assert (data[0][0:2, 2:4] == 90).all()
        assert data[0][2][1] == 60
        assert data[0][3][0] == 40


@requires_gdal22(
    reason="This test is sensitive to pixel values and requires GDAL 2.2+")
@pytest.mark.xfail(sys.version_info < (3,),
                   reason="Test is sensitive to rounding behavior")
def test_merge_tiny_res_bounds(tiffs, runner):
    outputname = str(tiffs.join('merged.tif'))
    inputs = [str(x) for x in tiffs.listdir()]
    inputs.sort()
    result = runner.invoke(
        main_group, ['merge'] + inputs + [outputname, '--res', 2, '--bounds', '1, 0, 5, 4'])
    assert result.exit_code == 0

    # Output should be
    # [[[0  90]
    #   [0   0]]]

    with rasterio.open(outputname) as src:
        data = src.read()
        print(data)
        assert data[0, 0, 0] == 0
        assert data[0, 0, 1] == 90
        assert data[0, 1, 0] == 0
        assert data[0, 1, 1] == 0


@pytest.mark.xfail(
    gdal_version.major == 1,
    reason="GDAL versions < 2 do not support data read/write with float sizes and offsets",
)
def test_merge_rgb(tmpdir, runner):
    """Get back original image"""
    outputname = str(tmpdir.join('merged.tif'))
    inputs = [
        'tests/data/rgb1.tif',
        'tests/data/rgb2.tif',
        'tests/data/rgb3.tif',
        'tests/data/rgb4.tif']
    result = runner.invoke(main_group, ['merge'] + inputs + [outputname])
    assert result.exit_code == 0

    with rasterio.open(outputname) as src:
        assert [src.checksum(i) for i in src.indexes] == [33219, 35315, 45188]


def test_merge_tiny_intres(tiffs):
    inputs = [str(x) for x in tiffs.listdir()]
    inputs.sort()
    datasets = [rasterio.open(x) for x in inputs]
    merge(datasets, res=2)


@pytest.mark.xfail(
    gdal_version.major == 1,
    reason="GDAL versions < 2 do not support data read/write with float sizes and offsets",
)
@pytest.mark.parametrize("precision", [[], ["--precision", "9"]])
def test_merge_precision(tmpdir, precision):
    """See https://github.com/mapbox/rasterio/issues/1837"""
    # TDOD move ascii grids to a fixture?

    expected = """\
        ncols        8
        nrows        8
        xllcorner    0.000000000000
        yllcorner    0.000000000000
        cellsize     1.000000000000
         1 2 3 4 1 2 3 4
         3 4 5 6 3 4 5 6
         4 5 6 8 4 5 6 8
         7 9 5 4 7 9 5 4
         1 2 3 4 1 2 3 4
         3 4 5 6 3 4 5 6
         4 5 6 8 4 5 6 8
         7 9 5 4 7 9 5 4
         """

    template = """\
        ncols 4
        nrows 4
        xllcorner {:f}
        yllcorner {:f}
        cellsize 1.0
        1 2 3 4
        3 4 5 6
        4 5 6 8
        7 9 5 4
        """

    names = ["sw.asc", "se.asc", "nw.asc", "ne.asc"]
    corners = [(0.0, 0.0), (4.0, 0.0), (0.0, 4.0), (4.0, 4.0)]

    for name, (minx, miny) in zip(names, corners):
        content = textwrap.dedent(template.format(minx, miny))
        tmpdir.join(name).write(content)

    inputs = [str(tmpdir.join(name)) for name in names]
    outputname = str(tmpdir.join("merged.asc"))

    runner = CliRunner()
    result = runner.invoke(main_group, ["merge", "-f", "AAIGrid"] + precision + inputs + [outputname])
    assert result.exit_code == 0
    assert open(outputname).read() == textwrap.dedent(expected)


@fixture(scope='function')
def test_data_dir_resampling(tmpdir):
    kwargs = {
        "crs": {'init': 'epsg:4326'},
        "transform": affine.Affine(0.2, 0, 0,
                                   0, -0.2, 0),
        "count": 1,
        "dtype": rasterio.uint8,
        "driver": "GTiff",
        "width": 9,
        "height": 1,
        "nodata": 1
    }

    with rasterio.open(str(tmpdir.join('a.tif')), 'w', **kwargs) as dst:
        data = np.ones((1, 9), dtype=rasterio.uint8)
        data[:, :3] = 100
        data[:, 3:6] = 255
        dst.write(data, indexes=1)

    return tmpdir


@pytest.mark.parametrize(
    "resampling",
    [resamp for resamp in Resampling if resamp < 7] +
    [pytest.param(Resampling.gauss, marks=pytest.mark.xfail)]
)
def test_merge_resampling(test_data_dir_resampling, resampling, runner):
    outputname = str(test_data_dir_resampling.join('merged.tif'))
    inputs = [str(x) for x in test_data_dir_resampling.listdir()]
    with rasterio.open(inputs[0]) as src:
        bounds = src.bounds
        res = src.res[0]
        expected_raster = src.read(
            out_shape=tuple(dim * 2 for dim in src.shape),
            resampling=resampling
        )
    result = runner.invoke(
        main_group, ['merge'] + inputs + [outputname] +
        ['--res', res / 2, '--resampling', resampling.name] +
        ['--bounds', ' '.join(map(str, bounds))])
    assert result.exit_code == 0
    assert os.path.exists(outputname)
    with rasterio.open(outputname) as dst:
        output_raster = dst.read()

    np.testing.assert_array_equal(output_raster, expected_raster)


def test_merge_filenames(tiffs):
    inputs = [str(x) for x in tiffs.listdir()]
    inputs.sort()
    merge(inputs, res=2)


def test_merge_pathlib_path(tiffs):
    inputs = [Path(x) for x in tiffs.listdir()]
    inputs.sort()
    merge(inputs, res=2)


@fixture(scope='function')
def test_data_dir_resampling(tmpdir):
    kwargs = {
        "crs": {'init': 'epsg:4326'},
        "transform": affine.Affine(0.2, 0, 0,
                                   0, -0.2, 0),
        "count": 1,
        "dtype": rasterio.uint8,
        "driver": "GTiff",
        "width": 9,
        "height": 1,
        "nodata": 1
    }

    with rasterio.open(str(tmpdir.join('a.tif')), 'w', **kwargs) as dst:
        data = np.ones((1, 9), dtype=rasterio.uint8)
        data[:, :3] = 100
        data[:, 3:6] = 255
        dst.write(data, indexes=1)

    return tmpdir


@pytest.mark.xfail(
    gdal_version.major == 1, reason="Mode resampling is unreliable for GDAL 1.11"
)
@pytest.mark.parametrize(
    "resampling",
    [resamp for resamp in Resampling if resamp < 7]
    + [pytest.param(Resampling.gauss, marks=pytest.mark.xfail)],
)
def test_merge_resampling(test_data_dir_resampling, resampling, runner):
    outputname = str(test_data_dir_resampling.join('merged.tif'))
    inputs = [str(x) for x in test_data_dir_resampling.listdir()]
    with rasterio.open(inputs[0]) as src:
        bounds = src.bounds
        res = src.res[0]
        expected_raster = src.read(
            out_shape=tuple(dim * 2 for dim in src.shape),
            resampling=resampling
        )
    result = runner.invoke(
        main_group, ['merge'] + inputs + [outputname] +
        ['--res', res / 2, '--resampling', resampling.name] +
        ['--bounds', ' '.join(map(str, bounds))])
    assert result.exit_code == 0
    assert os.path.exists(outputname)
    with rasterio.open(outputname) as dst:
        output_raster = dst.read()

    np.testing.assert_array_equal(output_raster, expected_raster)
