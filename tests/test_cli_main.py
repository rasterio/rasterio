"""Tests CLI command version and entry points."""

import rasterio
from rasterio.rio.main import entry_points, main_group


def test_version(runner):
    result = runner.invoke(main_group, ['--version'])
    assert result.exit_code == 0
    assert rasterio.__version__ in result.output


def test_all_registered():
    # This test makes sure that all of the subcommands defined in the
    # rasterio.rio_commands entry-point are actually registered to the main
    # cli group.
    for ep in entry_points(group="rasterio.rio_commands"):
        assert ep.name in main_group.commands
