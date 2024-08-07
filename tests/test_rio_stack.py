import rasterio
from rasterio.rio.main import main_group


def test_stack(tmpdir, runner):
    outputname = str(tmpdir.join('stacked.tif'))
    result = runner.invoke(
        main_group, ['stack', 'tests/data/RGB.byte.tif', outputname])
    assert result.exit_code == 0
    with rasterio.open(outputname) as out:
        assert out.count == 3
        assert out.read(1).max() > 0


def test_stack_2(tmpdir, runner):
    outputname = str(tmpdir.join("stacked.tif"))
    result = runner.invoke(
        main_group,
        ["stack", "tests/data/RGB.byte.tif", "tests/data/RGB.byte.tif", outputname],
    )
    assert result.exit_code == 0
    with rasterio.open(outputname) as out:
        assert out.count == 6
        assert out.read(1).max() > 0

        from rasterio.plot import show
        import matplotlib.pyplot as plt
        show(out.read(indexes=[4,5,6]))
        plt.savefig("/app/test_stack_2.png")


def test_stack_list(tmpdir, runner):
    outputname = str(tmpdir.join('stacked.tif'))
    result = runner.invoke(
        main_group, [
            'stack', 'tests/data/RGB.byte.tif', '--bidx', '1,2,3', outputname])
    assert result.exit_code == 0
    with rasterio.open(outputname) as out:
        assert out.count == 3


def test_stack_slice(tmpdir, runner):
    outputname = str(tmpdir.join('stacked.tif'))
    result = runner.invoke(
        main_group, [
            'stack',
            'tests/data/RGB.byte.tif', '--bidx', '..2',
            'tests/data/RGB.byte.tif', '--bidx', '3..',
            outputname])
    assert result.exit_code == 0
    with rasterio.open(outputname) as out:
        assert out.count == 3


def test_stack_single_slice(tmpdir, runner):
    outputname = str(tmpdir.join('stacked.tif'))
    result = runner.invoke(
        main_group, [
            'stack',
            'tests/data/RGB.byte.tif', '--bidx', '1',
            'tests/data/RGB.byte.tif', '--bidx', '2..',
            '--rgb', outputname])
    assert result.exit_code == 0
    with rasterio.open(outputname) as out:
        assert out.count == 3


def test_format_jpeg(tmpdir, runner):
    outputname = str(tmpdir.join('stacked.jpg'))
    result = runner.invoke(
        main_group, [
            'stack', 'tests/data/RGB.byte.tif', outputname,
            '--format', 'JPEG'])
    assert result.exit_code == 0


def test_error(tmpdir, runner):
    outputname = str(tmpdir.join('stacked.tif'))
    result = runner.invoke(
        main_group, [
            'stack', 'tests/data/RGB.byte.tif', outputname,
            '--driver', 'BOGUS'])
    assert result.exit_code == 1
