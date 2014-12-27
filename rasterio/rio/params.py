# Shared arguments and options.

import click

# Common arguments.
files_arg = click.argument(
    'files',
    nargs=-1,
    type=click.Path(resolve_path=True),
    required=True,
    metavar="INPUTS... OUTPUT")

# Common options.
verbose_opt = click.option(
    '--verbose', '-v',
    count=True,
    help="Increase verbosity.")

quiet_opt = click.option(
    '--quiet', '-q',
    count=True,
    help="Decrease verbosity.")

# Format driver option.
format_opt = click.option(
    '-f', '--format', '--driver',
    default='GTiff',
    help="Output format driver")

# JSON formatting options.
indent_opt = click.option(
    '--indent',
    type=int,
    default=None,
    help="Indentation level for JSON output")

compact_opt = click.option(
    '--compact/--no-compact',
    default=False,
    help="Use compact separators (',', ':').")

# Coordinate precision option.
precision_opt = click.option(
    '--precision',
    type=int,
    default=-1,
    help="Decimal precision of coordinates.")

# Geographic (default) or Mercator switch.
geographic_opt = click.option(
    '--geographic',
    'projected',
    flag_value='geographic',
    default=True,
    help="Output in geographic coordinates (the default).")

projected_opt = click.option(
    '--projected',
    'projected',
    flag_value='projected',
    help="Output in dataset's own, projected coordinates.")

mercator_opt = click.option(
    '--mercator',
    'projected',
    flag_value='mercator',
    help="Output in Web Mercator coordinates.")

# Feature collection or feature sequence switch.
collection_opt = click.option(
    '--collection/--sequence',
    default=True,
    help="Write a single JSON text containing a feature collection object "
         "(the default) or write a LF-delimited sequence of texts containing "
         "individual objects.")

rs_opt = click.option(
    '--with-rs/--without-rs',
    'use_rs',
    default=False,
    help="Use RS (0x1E) as a prefix for individual texts in a sequence "
         "as per http://tools.ietf.org/html/draft-ietf-json-text-sequence-13 "
         "(default is False).")

# GeoJSON output mode option.
def collection_mode_opt(default=False):
    return click.option(
        '--collection',
        'output_mode',
        flag_value='collection',
        default=default,
        help="Output as sequence of GeoJSON feature collections.")

def feature_mode_opt(default=False):
    return click.option(
        '--feature',
        'output_mode',
        flag_value='feature',
        default=default,
        help="Output as sequence of GeoJSON features.")

def bbox_mode_opt(default=False):
    return click.option(
        '--bbox',
        'output_mode',
        flag_value='bbox',
        default=default,
        help="Output as a GeoJSON bounding box array.")
