import pytest
from click.testing import CliRunner
from pydantic import ValidationError

from bot.core import config
from bot.core.cli import main
from bot.core.settings import Settings


def test_settings_load_env_with_environment_precedence(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("TELEGRAM_CHANNEL=@file\nTELEGRAM_API_HASH=secret\n")
    monkeypatch.setenv("TELEGRAM_CHANNEL", "@environment")
    settings = Settings()
    assert settings.TELEGRAM_CHANNEL == "@environment"
    assert "secret" not in repr(settings)


@pytest.mark.parametrize("value", ["0", "-1", "bad"])
def test_settings_reject_invalid_signal_age(value, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("MAX_SIGNAL_AGE_SECONDS", value)
    with pytest.raises(ValidationError):
        Settings()


def test_cli_reports_missing_channel(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TELEGRAM_CHANNEL", "")
    monkeypatch.setattr(config, "settings", Settings())
    result = CliRunner().invoke(main, ["telegram-monitor"])
    assert result.exit_code == 1
    assert "TELEGRAM_CHANNEL" in result.output


def test_cli_lists_commands():
    result = CliRunner().invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "telegram-login" in result.output
    assert "telegram-monitor" in result.output
