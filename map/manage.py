import click

from map.app import create_app
from map.migrations import Migration


app = create_app()


@app.cli.command("sync")
def sync():
    """Load static data idempotently"""
    Migration().upgrade()
    click.echo('sync CLI command complete')
