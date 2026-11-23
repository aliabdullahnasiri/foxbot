import asyncio
import logging
from decimal import Decimal, InvalidOperation
from typing import Literal

import click


@click.group(invoke_without_command=True)
@click.pass_context
def main(ctx: click.Context) -> None:
    """FoxBot commands."""
    logging.basicConfig(level=logging.INFO)
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@main.command("telegram-login")
def telegram_login() -> None:
    """Sign in to Telegram and save the local user session."""
    try:
        from bot.core.telegram import sign_in

        asyncio.run(sign_in())
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc


@main.command("telegram-monitor")
def telegram_monitor() -> None:
    """Monitor the configured Telegram channel."""
    try:
        from bot.core.celery import celery_app
        from bot.workers.telegram import TelegramMonitorWorker

        celery_app.tasks[TelegramMonitorWorker.name].apply(throw=True)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc


@main.command("mt5-order")
@click.option("--side", type=click.Choice(("buy", "sell")), required=True)
@click.option("--volume", required=True, help="Position size in lots.")
@click.option("--sl", required=True, help="Stop-loss price.")
@click.option("--tp", required=True, help="Take-profit price.")
@click.option("--entry", help="Optional reference price for entry deviation.")
@click.option("--request-id", help="Stable ID for submission. Generated for previews.")
@click.option("--submit", is_flag=True, help="Submit the order. Default is dry run.")
def mt5_order(
    side: Literal["buy", "sell"],
    volume: str,
    sl: str,
    tp: str,
    entry: str | None,
    request_id: str | None,
    submit: bool,
) -> None:
    """Open a fixed-volume market position on the connected MT5 account."""
    from bot.core.settings import get_settings
    from bot.services.mt5 import MT5Service, MT5ServiceError

    try:
        settings = get_settings()
        with MT5Service(
            login=settings.MT5_LOGIN,
            password=settings.MT5_PASSWORD.get_secret_value() or None,
            server=settings.MT5_SERVER or None,
            magic=settings.MT5_MAGIC,
        ) as mt5:
            result = mt5.market_order(
                settings.MT5_SYMBOL,
                side,
                Decimal(volume),
                sl=Decimal(sl),
                tp=Decimal(tp),
                entry=Decimal(entry) if entry is not None else None,
                request_id=request_id,
                submit=submit,
                settings=settings,
            )
    except InvalidOperation as exc:
        raise click.ClickException("Volume and prices must be decimal numbers") from exc
    except (MT5ServiceError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc
    if submit:
        click.echo(f"Order {result['status']}, deal {result['deal']}")
    else:
        click.echo(
            f"Preview {side} {volume} lots at {result['price']}, SL {sl}, TP {tp}. "
            f"To submit, add --request-id {result['request_id']} --submit."
        )
