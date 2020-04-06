import click

from map.app import create_app


app = create_app()


@app.cli.command("sync")
def sync():
    """Load static data idempotently"""
    click.echo('sync CLI command complete')
