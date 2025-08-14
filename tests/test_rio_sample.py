import logging
import sys
import subprocess
from rasterio.rio.main import main_group


logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)


def test_sample_err(runner):
    result = runner.invoke(
        main_group,
        ['sample', 'bogus.tif'],
        "[220650.0, 2719200.0]")
    assert result.exit_code == 1


def test_sample_stdin_subprocess():
    input_coords = "[220650.0, 2719200.0]\n[220650.0, 2719200.0]\n"
    expected_output = '[18, 25, 14]\n[18, 25, 14]'

    proc = subprocess.run(
        ["rio", "sample", "tests/data/RGB.byte.tif"],
        input=input_coords,
        capture_output=True,
        text=True  # enables universal newline mode (\r\n -> \n)
    )

    output = proc.stdout.strip()
    assert proc.returncode == 0
    assert output == expected_output, f"Got unexpected output: {repr(output)}"



def test_sample_arg(runner):
    result = runner.invoke(
        main_group,
        ['sample', 'tests/data/RGB.byte.tif', "[220650.0, 2719200.0]"],
        catch_exceptions=False)
    assert result.exit_code == 0
    assert result.output.strip() == '[18, 25, 14]'


def test_sample_bidx(runner):
    result = runner.invoke(
        main_group,
        ['sample', 'tests/data/RGB.byte.tif', '--bidx', '1,2', "[220650.0, 2719200.0]"],
        catch_exceptions=False)
    assert result.exit_code == 0
    assert result.output.strip() == '[18, 25]'


def test_sample_bidx2(runner):
    result = runner.invoke(
        main_group,
        ['sample', 'tests/data/RGB.byte.tif', '--bidx', '1..2', "[220650.0, 2719200.0]"],
        catch_exceptions=False)
    assert result.exit_code == 0
    assert result.output.strip() == '[18, 25]'


def test_sample_bidx3(runner):
    result = runner.invoke(
        main_group,
        ['sample', 'tests/data/RGB.byte.tif', '--bidx', '..2', "[220650.0, 2719200.0]"],
        catch_exceptions=False)
    assert result.exit_code == 0
    assert result.output.strip() == '[18, 25]'


def test_sample_bidx4(runner):
    result = runner.invoke(
        main_group,
        ['sample', 'tests/data/RGB.byte.tif', '--bidx', '3', "[220650.0, 2719200.0]"],
        catch_exceptions=False)
    assert result.exit_code == 0
    assert result.output.strip() == '[14]'
