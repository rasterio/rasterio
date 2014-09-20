import click


verbose = click.option(
    '--verbose', '-v', count=True, help="Increase verbosity.")
quiet = click.option(
    '--quiet', '-q', count=True, help="Decrease verbosity.")
