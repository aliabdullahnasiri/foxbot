import subprocess
import sys


def test_queue_worker_requires_broker(tmp_path, monkeypatch):
    monkeypatch.delenv("CELERY_BROKER_URL", raising=False)
    monkeypatch.delenv("CELERY_BROKER_READ_URL", raising=False)
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "celery",
            "-A",
            "bot.core.celery:celery_app",
            "worker",
            "--pool=solo",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 1
    assert "FoxBot needs CELERY_BROKER_URL" in result.stderr
    assert "uv run bot telegram-monitor" in result.stderr
