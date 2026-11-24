import asyncio
import logging

import click

from .mt5 import mt5


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


main.add_command(mt5)
