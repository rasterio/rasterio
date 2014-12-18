import click


files_arg = click.argument(
    'files',
    nargs=-1,
    type=click.Path(resolve_path=True),
    required=True,
    metavar="INPUTS... OUTPUT")

format_opt = click.option(
    '-f', '--format', '--driver',
    default='GTiff',
    help="Output format driver")

verbose_opt = click.option(
    '--verbose', '-v',
    count=True,
    help="Increase verbosity.")

quiet_opt = click.option(
    '--quiet', '-q',
    count=True,
    help="Decrease verbosity.")
