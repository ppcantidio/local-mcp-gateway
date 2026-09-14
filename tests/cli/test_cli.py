from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from local_mcp_gateway.cli import app
from local_mcp_gateway.config import load_config

runner = CliRunner()


def test_keygen_prints_key_and_writes_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["keygen"])
    assert result.exit_code == 0
    key = result.stdout.strip()
    assert len(key) >= 32
    assert list(tmp_path.iterdir()) == []


def test_init_add_ls_rm(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    init = runner.invoke(app, ["init"])
    assert init.exit_code == 0
    assert (tmp_path / "lmg.toml").is_file()
    assert "LMG_API_KEY" in init.stdout

    added = runner.invoke(app, ["add", "other", "http://127.0.0.1:3100"])
    assert added.exit_code == 0
    listed = runner.invoke(app, ["ls"])
    assert listed.exit_code == 0
    assert "paper" in listed.stdout
    assert "other" in listed.stdout

    removed = runner.invoke(app, ["rm", "other"])
    assert removed.exit_code == 0
    cfg = load_config(tmp_path / "lmg.toml")
    assert [item.name for item in cfg.mcp] == ["paper"]


def test_serve_requires_api_key(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("LMG_API_KEY", raising=False)
    runner.invoke(app, ["init"])
    result = runner.invoke(app, ["serve", "--publisher", "local"])
    assert result.exit_code == 1
    combined = result.stdout + (result.stderr or "")
    assert "LMG_API_KEY" in combined
    assert "test-token" not in combined.lower()


def test_init_refuses_overwrite(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    assert runner.invoke(app, ["init"]).exit_code == 0
    second = runner.invoke(app, ["init"])
    assert second.exit_code == 1
