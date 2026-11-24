from collections.abc import Callable, Iterator
from contextlib import contextmanager
from decimal import Decimal, InvalidOperation
from typing import Literal

import click
from rich.table import Table

from bot.core.console import console
from bot.core.settings import Settings
from bot.services.mt5 import MT5Service, MT5ServiceError


@click.group()
def order() -> None:
    """Manage market positions on the configured symbol."""


@contextmanager
def connection() -> Iterator[tuple[MT5Service, Settings]]:
    from bot.core.settings import get_settings

    try:
        settings = get_settings()
        with MT5Service(
            login=settings.MT5_LOGIN,
            password=settings.MT5_PASSWORD.get_secret_value() or None,
            server=settings.MT5_SERVER or None,
            magic=settings.MT5_MAGIC,
        ) as service:
            yield service, settings
    except InvalidOperation as exc:
        raise click.ClickException("Volume and prices must be decimal numbers") from exc
    except (MT5ServiceError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc


def open_options[F: Callable](command: F) -> F:
    command = click.option("--volume", required=True, help="Position size in lots.")(
        command,
    )
    command = click.option("--sl", required=True, help="Stop-loss price.")(command)
    command = click.option("--tp", required=True, help="Take-profit price.")(command)
    command = click.option(
        "--entry",
        help="Optional reference price for entry deviation.",
    )(command)
    return click.option(
        "--submit",
        is_flag=True,
        help="Submit the order. Default is dry run.",
    )(command)


def open_market_position(
    side: Literal["buy", "sell"],
    volume: str,
    sl: str,
    tp: str,
    entry: str | None,
    *,
    submit: bool,
) -> None:
    """Open a fixed-volume market position on the connected MT5 account."""
    with connection() as (service, settings):
        result = service.market_order(
            settings.MT5_SYMBOL,
            side,
            Decimal(volume),
            sl=Decimal(sl),
            tp=Decimal(tp),
            entry=Decimal(entry) if entry is not None else None,
            submit=submit,
            settings=settings,
        )
    if submit:
        click.echo(f"Order {result['status']}, deal {result['deal']}")
    else:
        click.echo(
            f"Preview {side} {volume} lots at {result['price']}, SL {sl}, TP {tp}. "
            "To submit, add --submit.",
        )


def register_side(side: Literal["buy", "sell"]) -> None:
    @order.command(side, help=f"Open a {side} market position.")
    @open_options
    def open_position(
        volume: str,
        sl: str,
        tp: str,
        entry: str | None,
        submit: bool,
    ) -> None:
        open_market_position(side, volume, sl, tp, entry, submit=submit)


register_side("buy")
register_side("sell")


@order.command("list")
@click.option("--ticket", type=click.IntRange(min=1), help="Show one position ticket.")
def list_positions(ticket: int | None) -> None:
    """List open positions on the configured symbol."""
    with connection() as (service, settings):
        rows = service.positions(settings.MT5_SYMBOL, ticket)
        if not rows:
            click.echo("No matching open positions.")
            return
        table = Table(title="Open positions")
        table.add_column("Ticket", justify="right")
        table.add_column("Symbol")
        table.add_column("Side")
        table.add_column("Lots", justify="right")
        for row in rows:
            side = service.position_side(row["type"])
            table.add_row(str(row["ticket"]), row["symbol"], side, str(row["volume"]))
        console.print(table)


@order.command("close")
@click.argument("ticket", type=click.IntRange(min=1))
@click.option("--submit", is_flag=True, help="Submit the checked close request.")
def close_position(ticket: int, submit: bool) -> None:
    """Close the full open volume of position TICKET."""
    with connection() as (service, settings):
        result = service.close_position(ticket, settings, submit=submit)
    if submit:
        click.echo(
            f"Close {result['status']} for ticket {ticket}, deal {result['deal']}",
        )
    else:
        click.echo(
            f"Preview close {ticket}: {result['volume']} lots at {result['price']}. "
            "To submit, add --submit.",
        )
