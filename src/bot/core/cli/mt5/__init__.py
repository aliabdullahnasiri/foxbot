import click

from .order import order


@click.group()
def mt5() -> None:
    """Work with the connected MetaTrader 5 terminal."""


mt5.add_command(order)
