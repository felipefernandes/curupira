"""Tests for RemoteUpdateSkill and check_update_sentinel."""

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from skills.remote_update import RemoteUpdateSkill, check_update_sentinel, _SENTINEL_FILE


# ── Fixtures ───────────────────────────────────────────────────────────


@pytest.fixture
def skill():
    return RemoteUpdateSkill()


@pytest.fixture
def valid_context():
    bot = AsyncMock()
    bot.send_message = AsyncMock()
    return {
        "raw_message": "atualizar sistema, pin: testpin",
        "bot": bot,
        "chat_id": 12345,
    }


@pytest.fixture(autouse=True)
def cleanup_sentinel(tmp_path, monkeypatch):
    """Redirect sentinel file to a temp path so tests don't pollute the project root."""
    sentinel = tmp_path / ".update_pending"
    monkeypatch.setattr("skills.remote_update._SENTINEL_FILE", sentinel)
    yield sentinel
    if sentinel.exists():
        sentinel.unlink()


# ── Skill metadata ─────────────────────────────────────────────────────


def test_metadata(skill):
    assert skill.name == "trigger_remote_update"
    assert "Atualização" in skill.display_name
    assert "atualizar sistema" in skill.description.lower()
    assert skill.parameters["type"] == "object"
    assert skill.parameters["required"] == []


# ── Task 4.2 — Wrong PIN is silently ignored ───────────────────────────


@pytest.mark.asyncio
@patch("skills.remote_update.cfg" if False else "core.config.REMOTE_UPDATE_PIN", "testpin", create=True)
async def test_wrong_pin_no_action(skill, valid_context):
    """Wrong PIN → error returned, no subprocess spawned."""
    ctx = dict(valid_context)
    ctx["raw_message"] = "atualizar sistema, pin: wrongpin"

    with patch("core.config.REMOTE_UPDATE_PIN", "testpin"):
        with patch.object(skill, "_run_subprocess", new_callable=AsyncMock) as mock_sub:
            result = await skill.execute(ctx)

    assert result["status"] == "error"
    mock_sub.assert_not_called()


# ── Task 4.2b — No PIN → silently ignored ─────────────────────────────


@pytest.mark.asyncio
async def test_no_pin_no_action(skill, valid_context):
    """Message without pin: → error, no subprocess spawned."""
    ctx = dict(valid_context)
    ctx["raw_message"] = "atualizar sistema"

    with patch("core.config.REMOTE_UPDATE_PIN", "testpin"):
        with patch.object(skill, "_run_subprocess", new_callable=AsyncMock) as mock_sub:
            result = await skill.execute(ctx)

    assert result["status"] == "error"
    mock_sub.assert_not_called()


# ── Task 4.1 — Correct PIN triggers pipeline ──────────────────────────


@pytest.mark.asyncio
async def test_correct_pin_triggers_pipeline(skill, valid_context, cleanup_sentinel):
    """Correct PIN: subprocesses called, sentinel written, os.execv called."""
    with patch("core.config.REMOTE_UPDATE_PIN", "testpin"):
        with patch.object(skill, "_run_subprocess", new_callable=AsyncMock, return_value=(0, "ok")) as mock_sub:
            with patch("os.execv") as mock_execv:
                result = await skill.execute(valid_context)

    # Both subprocesses run (git pull + pip install)
    assert mock_sub.call_count == 2
    # Sentinel written
    assert cleanup_sentinel.exists()
    payload = json.loads(cleanup_sentinel.read_text())
    assert payload["chat_id"] == 12345
    # os.execv called
    mock_execv.assert_called_once()
    # Progress message sent
    valid_context["bot"].send_message.assert_awaited_once()


# ── Task 4.3 — git pull fails → pipeline aborts ───────────────────────


@pytest.mark.asyncio
async def test_git_pull_fails_aborts(skill, valid_context, cleanup_sentinel):
    """git pull non-zero exit → pipeline aborts, no sentinel, no restart."""
    async def mock_sub(cmd, timeout):
        if cmd[0] == "git":
            return (1, "error: merge conflict")
        return (0, "ok")

    with patch("core.config.REMOTE_UPDATE_PIN", "testpin"):
        with patch.object(skill, "_run_subprocess", side_effect=mock_sub):
            with patch("os.execv") as mock_execv:
                result = await skill.execute(valid_context)

    assert result["status"] == "error"
    assert "git pull" in result["error"]
    assert not cleanup_sentinel.exists()
    mock_execv.assert_not_called()


# ── Task 4.4 — pip install fails → pipeline aborts ────────────────────


@pytest.mark.asyncio
async def test_pip_install_fails_aborts(skill, valid_context, cleanup_sentinel):
    """pip install non-zero exit → pipeline aborts, no sentinel, no restart."""
    call_count = {"n": 0}

    async def mock_sub(cmd, timeout):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return (0, "Already up to date.")  # git pull ok
        return (1, "ERROR: could not find package")  # pip fails

    with patch("core.config.REMOTE_UPDATE_PIN", "testpin"):
        with patch.object(skill, "_run_subprocess", side_effect=mock_sub):
            with patch("os.execv") as mock_execv:
                result = await skill.execute(valid_context)

    assert result["status"] == "error"
    assert "pip install" in result["error"]
    assert not cleanup_sentinel.exists()
    mock_execv.assert_not_called()


# ── Task 4.5 — Pipeline timeout → no restart ──────────────────────────


@pytest.mark.asyncio
async def test_pipeline_timeout_no_restart(skill, valid_context, cleanup_sentinel):
    """asyncio.TimeoutError during pipeline → error, no sentinel, no restart."""
    import asyncio

    async def mock_sub(cmd, timeout):
        raise asyncio.TimeoutError()

    with patch("core.config.REMOTE_UPDATE_PIN", "testpin"):
        with patch.object(skill, "_run_subprocess", side_effect=mock_sub):
            with patch("os.execv") as mock_execv:
                result = await skill.execute(valid_context)

    assert result["status"] == "error"
    assert "timeout" in result["error"].lower()
    assert not cleanup_sentinel.exists()
    mock_execv.assert_not_called()


# ── Task 4.6 — Startup: recent sentinel → message sent, file deleted ──


@pytest.mark.asyncio
async def test_sentinel_recent_sends_message(cleanup_sentinel):
    """Recent sentinel → sends update message and deletes file."""
    payload = {
        "chat_id": 99999,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    cleanup_sentinel.write_text(json.dumps(payload))

    bot = AsyncMock()
    bot.send_message = AsyncMock()

    await check_update_sentinel(bot, authorized_user_id=99999)

    bot.send_message.assert_awaited_once_with(chat_id=99999, text="✅ Sistema atualizado")
    assert not cleanup_sentinel.exists()


# ── Task 4.7 — Startup: stale sentinel → deleted, no message ──────────


@pytest.mark.asyncio
async def test_sentinel_stale_deleted_no_message(cleanup_sentinel):
    """Stale sentinel (>10 min) → file deleted, no message sent."""
    stale_time = datetime.now(timezone.utc) - timedelta(minutes=15)
    payload = {
        "chat_id": 99999,
        "updated_at": stale_time.isoformat(),
    }
    cleanup_sentinel.write_text(json.dumps(payload))

    bot = AsyncMock()
    bot.send_message = AsyncMock()

    await check_update_sentinel(bot, authorized_user_id=99999)

    bot.send_message.assert_not_awaited()
    assert not cleanup_sentinel.exists()


# ── Task 4.8 — Startup with no sentinel → no side effects ─────────────


@pytest.mark.asyncio
async def test_no_sentinel_no_side_effects(cleanup_sentinel):
    """No sentinel file → check_update_sentinel does nothing."""
    assert not cleanup_sentinel.exists()

    bot = AsyncMock()
    bot.send_message = AsyncMock()

    await check_update_sentinel(bot, authorized_user_id=99999)

    bot.send_message.assert_not_awaited()


# ── REMOTE_UPDATE_PIN not configured ──────────────────────────────────


@pytest.mark.asyncio
async def test_pin_not_configured_returns_error(skill, valid_context):
    """REMOTE_UPDATE_PIN absent → error returned, no subprocess spawned."""
    with patch("core.config.REMOTE_UPDATE_PIN", None):
        with patch.object(skill, "_run_subprocess", new_callable=AsyncMock) as mock_sub:
            result = await skill.execute(valid_context)

    assert result["status"] == "error"
    mock_sub.assert_not_called()
