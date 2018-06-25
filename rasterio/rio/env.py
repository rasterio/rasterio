"""Fetch and edit raster dataset metadata from the command line."""

import json

import click

import rasterio


@click.command(short_help="Print information about the Rasterio environment.")
@click.option('--formats', 'key', flag_value='formats', default=True,
              help="Enumerate the available formats.")
@click.option('--credentials', 'key', flag_value='credentials', default=False,
              help="Print AWS credentials.")
@click.pass_context
def env(ctx, key):
    """Print information about the Rasterio environment."""
    with ctx.obj['env'] as env:
        if key == 'formats':
            for k, v in sorted(env.drivers().items()):
                click.echo("{0}: {1}".format(k, v))
        elif key == 'credentials':
            click.echo(json.dumps({
                'aws_access_key_id': env._creds.access_key,
                'aws_secret_access_key': env._creds.secret_key,
                'aws_session_token': env._creds.token}))
