import click

from rasterio import __version__ as rio_version


def print_version(ctx, param, value):
    if not value or ctx.resilient_parsing:
        return
    click.echo(rio_version)
    ctx.exit()


version = click.option('--version', is_flag=True, callback=print_version,
                       expose_value=False, is_eager=True,
                       help="Print Rasterio version.")
