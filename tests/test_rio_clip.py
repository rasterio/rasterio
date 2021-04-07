import os

import numpy
import pytest

import rasterio
from rasterio.rio.main import main_group
TEST_BBOX = [-11850000, 4804000, -11840000, 4808000]


def bbox(*args):
    return ' '.join([str(x) for x in args])


@pytest.mark.parametrize("bounds", [bbox(*TEST_BBOX)])
def test_clip_bounds(runner, tmpdir, bounds):
    output = str(tmpdir.join('test.tif'))
    result = runner.invoke(
        main_group, ["clip", "tests/data/shade.tif", output, "--bounds", bounds]
    )
    assert result.exit_code == 0
    assert os.path.exists(output)

    with rasterio.open(output) as out:
        assert out.shape == (419, 173)


@pytest.mark.parametrize("bounds", [bbox(*TEST_BBOX)])
def test_clip_bounds_with_complement(runner, tmpdir, bounds):
    output = str(tmpdir.join("test.tif"))
    result = runner.invoke(
        main_group,
        [
            "clip",
            "tests/data/shade.tif",
            output,
            "--bounds",
            bounds,
            "--with-complement",
        ],
    )
    assert result.exit_code == 0
    assert os.path.exists(output)

    with rasterio.open(output) as out:
        assert out.shape == (419, 1047)
        data = out.read()
        assert (data[420:, :] == 255).all()


def test_clip_bounds_geographic(runner, tmpdir):
    output = str(tmpdir.join('test.tif'))
    result = runner.invoke(
        main_group,
        ['clip', 'tests/data/RGB.byte.tif', output, '--geographic', '--bounds',
         '-78.95864996545055 23.564991210854686 -76.57492370013823 25.550873767433984'])
    assert result.exit_code == 0
    assert os.path.exists(output)

    with rasterio.open(output) as out:
        assert out.shape == (718, 791)


def test_clip_like(runner, tmpdir):
    output = str(tmpdir.join('test.tif'))
    result = runner.invoke(
        main_group, [
            'clip', 'tests/data/shade.tif', output, '--like',
            'tests/data/shade.tif'])
    assert result.exit_code == 0
    assert os.path.exists(output)

    with rasterio.open('tests/data/shade.tif') as template_ds:
        with rasterio.open(output) as out:
            assert out.shape == template_ds.shape
            assert numpy.allclose(out.bounds, template_ds.bounds)


def test_clip_missing_params(runner, tmpdir):
    output = str(tmpdir.join('test.tif'))
    result = runner.invoke(
        main_group, ['clip', 'tests/data/shade.tif', output])
    assert result.exit_code == 2
    assert '--bounds or --like required' in result.output


def test_clip_bounds_disjunct(runner, tmpdir):
    output = str(tmpdir.join('test.tif'))
    result = runner.invoke(
        main_group,
        ['clip', 'tests/data/shade.tif', output, '--bounds', bbox(0, 0, 10, 10)])
    assert result.exit_code == 2
    assert '--bounds' in result.output


def test_clip_like_disjunct(runner, tmpdir):
    output = str(tmpdir.join('test.tif'))
    result = runner.invoke(
        main_group, [
            'clip', 'tests/data/shade.tif', output, '--like',
            'tests/data/RGB.byte.tif'])
    assert result.exit_code == 2
    assert '--like' in result.output


def test_clip_overwrite_without_option(runner, tmpdir):
    output = str(tmpdir.join('test.tif'))
    result = runner.invoke(
        main_group,
        ['clip', 'tests/data/shade.tif', output, '--bounds', bbox(*TEST_BBOX)])
    assert result.exit_code == 0

    result = runner.invoke(
        main_group,
        ['clip', 'tests/data/shade.tif', output, '--bounds', bbox(*TEST_BBOX)])
    assert result.exit_code == 1
    assert '--overwrite' in result.output


def test_clip_overwrite_with_option(runner, tmpdir):
    output = str(tmpdir.join('test.tif'))
    result = runner.invoke(
        main_group,
        ['clip', 'tests/data/shade.tif', output, '--bounds', bbox(*TEST_BBOX)])
    assert result.exit_code == 0

    result = runner.invoke(
        main_group,
        [
            "clip",
            "tests/data/shade.tif",
            output,
            "--bounds",
            bbox(*TEST_BBOX),
            "--overwrite",
        ],
    )
    assert result.exit_code == 0


def test_clip_rotated(runner, tmpdir):
    """Rotated dataset cannot be clipped"""
    output = str(tmpdir.join('test.tif'))
    result = runner.invoke(
        main_group, ['clip', 'tests/data/rotated.tif', output])
    assert result.exit_code == 2
    assert 'Non-rectilinear' in result.output


@pytest.mark.parametrize("bounds", [bbox(31.0, -1.0, 33.0, 1.0)])
def test_clip_bounds_with_complement_nodata(runner, tmpdir, bounds):
    """Show fix of #2084"""
    output = str(tmpdir.join("test.tif"))
    result = runner.invoke(
        main_group,
        [
            "clip",
            "tests/data/green.tif",
            output,
            "--bounds",
            bounds,
            "--with-complement",
            "--nodata",
            "0",
        ],
    )
    assert result.exit_code == 0
    assert os.path.exists(output)

    with rasterio.open(output) as out:
        assert out.shape == (4, 4)
        data = out.read(masked=True)
        assert not data.mask[:, 2:, :2].any()
        assert data.mask[:, :2, :].all()
        assert data.mask[:, :, 2:].all()
