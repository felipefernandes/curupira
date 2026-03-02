import pytest
from unittest.mock import patch
from bot import run_pre_start_checks

@patch("bot.config")
def test_pre_start_missing_token(mock_config):
    mock_config.TELEGRAM_TOKEN = None
    assert not run_pre_start_checks()

@patch("bot.config")
@patch("core.health.run_full_diagnostic")
def test_pre_start_critical_health(mock_diag, mock_config):
    mock_config.TELEGRAM_TOKEN = "123:abc"
    mock_diag.return_value = {
        "status": "critical",
        "issues": ["Falta FFMpeg"]
    }
    assert not run_pre_start_checks()

@patch("bot.config")
@patch("core.health.run_full_diagnostic")
def test_pre_start_warning_health(mock_diag, mock_config):
    mock_config.TELEGRAM_TOKEN = "123:abc"
    mock_diag.return_value = {
        "status": "warning",
        "issues": ["Sem internet pro groq"]
    }
    assert run_pre_start_checks()

@patch("bot.config")
@patch("core.health.run_full_diagnostic")
def test_pre_start_ok_health(mock_diag, mock_config):
    mock_config.TELEGRAM_TOKEN = "123:abc"
    mock_diag.return_value = {
        "status": "ok",
        "issues": []
    }
    assert run_pre_start_checks()
