import os

from click.testing import CliRunner
import numpy as np
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
            assert np.allclose(out.bounds, template_ds.bounds)


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


# Tests: format and type conversion, --format and --dtype

def test_format(tmpdir, runner):
    outputname = str(tmpdir.join('test.jpg'))
    result = runner.invoke(
        main_group,
        ['convert', 'tests/data/RGB.byte.tif', outputname, '--format', 'JPEG'])
    assert result.exit_code == 0
    with rasterio.open(outputname) as src:
        assert src.driver == 'JPEG'


def test_format_short(tmpdir, runner):
    outputname = str(tmpdir.join('test.jpg'))
    result = runner.invoke(
        main_group,
        ['convert', 'tests/data/RGB.byte.tif', outputname, '-f', 'JPEG'])
    assert result.exit_code == 0
    with rasterio.open(outputname) as src:
        assert src.driver == 'JPEG'


@pytest.mark.parametrize("extension, driver", [
    ('TIF', 'GTiff'),
    ('tiff', 'GTiff'),
    ('png', 'PNG'),
    ('jpg', 'JPEG'),
    ('jpeg', 'JPEG'),
])
def test_autodetect_format(tmpdir, runner, extension, driver):
    outputname = str(tmpdir.join("test.{}".format(extension)))
    result = runner.invoke(
        main_group,
        ['convert', 'tests/data/RGB.byte.tif', outputname])
    assert result.exit_code == 0
    with rasterio.open(outputname) as src:
        assert src.driver == driver


def test_output_opt(tmpdir, runner):
    outputname = str(tmpdir.join('test.jpg'))
    result = runner.invoke(
        main_group,
        ['convert', 'tests/data/RGB.byte.tif', '-o', outputname, '-f', 'JPEG'])
    assert result.exit_code == 0
    with rasterio.open(outputname) as src:
        assert src.driver == 'JPEG'


def test_dtype(tmpdir, runner):
    outputname = str(tmpdir.join('test.tif'))
    result = runner.invoke(
        main_group,
        ['convert', 'tests/data/RGB.byte.tif', outputname, '--dtype', 'uint16'])
    assert result.exit_code == 0
    with rasterio.open(outputname) as src:
        assert src.dtypes == tuple(['uint16'] * 3)


def test_dtype_rescaling_uint8_full(tmpdir, runner):
    """Rescale uint8 [0, 255] to uint8 [0, 255]"""
    outputname = str(tmpdir.join('test.tif'))
    result = runner.invoke(
        main_group,
        ['convert', 'tests/data/RGB.byte.tif', outputname, '--scale-ratio', '1.0'])
    assert result.exit_code == 0

    src_stats = [
        {"max": 255.0, "mean": 44.434478650699106, "min": 1.0},
        {"max": 255.0, "mean": 66.02203484105824, "min": 1.0},
        {"max": 255.0, "mean": 71.39316199120559, "min": 1.0}]

    with rasterio.open(outputname) as src:
        for band, expected in zip(src.read(masked=True), src_stats):
            assert round(band.min() - expected['min'], 6) == 0.0
            assert round(band.max() - expected['max'], 6) == 0.0
            assert round(band.mean() - expected['mean'], 6) == 0.0


def test_dtype_rescaling_uint8_half(tmpdir, runner):
    """Rescale uint8 [0, 255] to uint8 [0, 127]"""
    outputname = str(tmpdir.join('test.tif'))
    result = runner.invoke(main_group, [
        'convert', 'tests/data/RGB.byte.tif', outputname, '--scale-ratio', '0.5'])
    assert result.exit_code == 0
    with rasterio.open(outputname) as src:
        for band in src.read():
            assert round(band.min() - 0, 6) == 0.0
            assert round(band.max() - 127, 6) == 0.0


def test_dtype_rescaling_uint16(tmpdir, runner):
    """Rescale uint8 [0, 255] to uint16 [0, 4095]"""
    # NB: 255 * 16 is 4080, we don't actually get to 4095.
    outputname = str(tmpdir.join('test.tif'))
    result = runner.invoke(main_group, [
        'convert', 'tests/data/RGB.byte.tif', outputname, '--dtype', 'uint16',
        '--scale-ratio', '16'])
    assert result.exit_code == 0
    with rasterio.open(outputname) as src:
        for band in src.read():
            assert round(band.min() - 0, 6) == 0.0
            assert round(band.max() - 4080, 6) == 0.0


def test_dtype_rescaling_float64(tmpdir, runner):
    """Rescale uint8 [0, 255] to float64 [-1, 1]"""
    outputname = str(tmpdir.join('test.tif'))
    result = runner.invoke(main_group, [
        'convert', 'tests/data/RGB.byte.tif', outputname, '--dtype', 'float64',
        '--scale-ratio', str(2.0 / 255), '--scale-offset', '-1.0'])
    assert result.exit_code == 0
    with rasterio.open(outputname) as src:
        for band in src.read():
            assert round(band.min() + 1.0, 6) == 0.0
            assert round(band.max() - 1.0, 6) == 0.0


def test_rgb(tmpdir, runner):
    outputname = str(tmpdir.join('test.tif'))
    result = runner.invoke(
        main_group,
        ['convert', 'tests/data/RGB.byte.tif', outputname, '--rgb'])
    assert result.exit_code == 0
    with rasterio.open(outputname) as src:
        assert src.colorinterp[0] == rasterio.enums.ColorInterp.red


def test_convert_overwrite_without_option(runner, tmpdir):
    outputname = str(tmpdir.join('test.tif'))
    result = runner.invoke(
        main_group,
        ['convert', 'tests/data/RGB.byte.tif', '-o', outputname, '-f', 'JPEG'])
    assert result.exit_code == 0

    result = runner.invoke(
        main_group,
        ['convert', 'tests/data/RGB.byte.tif', '-o', outputname, '-f', 'JPEG'])
    assert result.exit_code == 1
    assert '--overwrite' in result.output


def test_convert_overwrite_with_option(runner, tmpdir):
    outputname = str(tmpdir.join('test.tif'))
    result = runner.invoke(
        main_group,
        ['convert', 'tests/data/RGB.byte.tif', '-o', outputname, '-f', 'JPEG'])
    assert result.exit_code == 0

    result = runner.invoke(
        main_group, [
        'convert', 'tests/data/RGB.byte.tif', '-o', outputname, '-f', 'JPEG',
        '--overwrite'])
    assert result.exit_code == 0


def test_convert_no_input(runner, tmpdir):
    """Test fix of issue1985"""
    outputname = str(tmpdir.join("test.tif"))
    result = runner.invoke(main_group, ["convert", "-o", outputname, "-f", "JPEG"])
    assert result.exit_code == 2


def test_convert_no_input_overwrite(runner, tmpdir):
    """Test fix of issue1985"""
    outputname = str(tmpdir.join("test.tif"))
    result = runner.invoke(
        main_group, ["convert", "--overwrite", outputname, "-f", "JPEG"]
    )
    assert result.exit_code == 2
    assert "Insufficient inputs" in result.output
