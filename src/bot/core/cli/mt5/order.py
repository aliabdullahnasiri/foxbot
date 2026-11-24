from collections import deque
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Literal

import click
from rich.console import Group
from rich.live import Live
from rich.table import Table
from rich.text import Text

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
    command = click.option(
        "--tp", multiple=True, required=True, help="Repeat from nearest to final TP."
    )(command)
    command = click.option(
        "--entry",
        help="Optional reference price for entry deviation.",
    )(command)
    return click.option(
        "--submit",
        is_flag=True,
        help="Submit the order. Default is dry run.",
    )(command)


class OrderLog:
    def __init__(self) -> None:
        self.table = Table(title="Order log")
        self.table.add_column("Time (UTC)", style="dim")
        self.table.add_column("Event")
        self.table.add_column("Details")
        self.monitor: Table | None = None
        self.live = Live(
            get_renderable=self.render, console=console, auto_refresh=False
        )

    def render(self) -> Table | Group:
        return (
            Group(self.monitor, self.table) if self.monitor is not None else self.table
        )

    def add(self, event: str, details: str) -> None:
        stamp = datetime.now(UTC).strftime("%H:%M:%S")
        self.table.add_row(stamp, Text(event), Text(details))
        if console.is_terminal:
            self.live.refresh()


@contextmanager
def order_log() -> Iterator[OrderLog]:
    log = OrderLog()
    with log.live:
        try:
            yield log
        except click.ClickException as exc:
            log.add("Error", exc.format_message())
            raise
        except KeyboardInterrupt:
            log.add("Interrupted", "Operator stopped the command")
            raise


def open_market_position(
    side: Literal["buy", "sell"],
    volume: str,
    sl: str,
    tp: tuple[str, ...],
    entry: str | None,
    *,
    submit: bool,
) -> None:
    """Open a fixed-volume market position on the connected MT5 account."""
    with order_log() as log, connection() as (service, settings):
        log.add(
            "Checking order", f"{side.upper()} {volume} lots · {settings.MT5_SYMBOL}"
        )
        result = service.market_order(
            settings.MT5_SYMBOL,
            side,
            Decimal(volume),
            sl=Decimal(sl),
            tp=Decimal(tp[-1]),
            milestones=tuple(Decimal(price) for price in tp[:-1]),
            entry=Decimal(entry) if entry is not None else None,
            submit=submit,
            settings=settings,
        )
        if not submit:
            log.add("Preview", "Broker check passed")
            click.echo(
                f"Preview {side} {volume} lots at {result['price']}, SL {sl}, "
                f"TP {', '.join(tp)}. To submit, add --submit."
            )
            return

        receipt = Table(
            title=f"{settings.MT5_SYMBOL} · {side.upper()} · {result['status']}"
        )
        for heading in ("Deal", "Filled lots", "Fill price", "Initial SL", "Final TP"):
            receipt.add_column(heading, justify="right")
        receipt.add_row(
            str(result["deal"]),
            str(result.get("volume", "—")),
            str(result.get("price", "—")),
            sl,
            tp[-1],
        )
        console.print(receipt)
        log.add(result["status"].capitalize(), f"Deal {result['deal']}")
        quote_side = "bid" if side == "buy" else "ask"
        if len(tp) == 1:
            try:
                tick = service.tick(settings.MT5_SYMBOL)
            except MT5ServiceError as exc:
                log.add("Quote unavailable", str(exc))
            else:
                console.print(f"Latest {quote_side}  {tick[quote_side]}")
            return

        prices: deque[Decimal] = deque(maxlen=40)
        log.add(
            "Monitoring",
            f"Watching {quote_side} for {len(tp) - 1} intermediate targets",
        )

        def update(price: Decimal, stop: Decimal, next_trigger: Decimal | None) -> None:
            prices.append(price)
            table = Table(title="Stop monitor", show_header=False)
            table.add_column(style="dim")
            table.add_column(justify="right")
            table.add_row(f"Current {quote_side}", f"[bold cyan]{price}[/]")
            table.add_row("Active SL", str(stop))
            table.add_row(
                "Next TP trigger", str(next_trigger) if next_trigger else "Complete"
            )
            table.add_section()
            table.add_row("Recent quotes", price_chart(prices))
            table.add_row("Low / high", f"{min(prices)} / {max(prices)}")
            log.monitor = table
            if console.is_terminal:
                log.live.refresh()

        service.trail_targets(
            result,
            side,
            tuple(map(Decimal, tp)),
            settings,
            on_quote=update,
            on_event=log.add,
        )
        log.add("Finished", "Stop monitoring finished")


def price_chart(prices: deque[Decimal]) -> str:
    """Plot the most recent quote samples from oldest to newest."""
    levels = "▁▂▃▄▅▆▇█"
    low = min(prices)
    span = max(prices) - low
    if not span:
        return levels[0] * len(prices)
    return "".join(levels[int((p - low) * (len(levels) - 1) / span)] for p in prices)


def register_side(side: Literal["buy", "sell"]) -> None:
    @order.command(side, help=f"Open a {side} market position.")
    @open_options
    def open_position(
        volume: str,
        sl: str,
        tp: tuple[str, ...],
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
