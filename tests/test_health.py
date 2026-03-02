import sys
import os
import pytest
from unittest.mock import patch, mock_open

from core import health
from core import config

@pytest.fixture
def mock_config():
    with patch("core.health.config") as mock:
        yield mock

def test_check_memory_zram_not_linux():
    with patch("os.path.exists", return_value=False):
        ok, msg = health.check_memory_zram()
        assert ok
        assert "não é Linux" in msg

def test_check_memory_zram_enough_ram():
    fake_meminfo = "MemTotal:        4000000 kB\n"
    with patch("os.path.exists", return_value=True):
        with patch("builtins.open", mock_open(read_data=fake_meminfo)):
            ok, msg = health.check_memory_zram()
            assert ok
            assert "OK" in msg

def test_check_memory_zram_low_ram_with_zram():
    fake_meminfo = "MemTotal:        1000000 kB\n"
    fake_swaps = "Filename\t\t\t\tType\t\tSize\t\tUsed\t\tPriority\n/dev/zram0                              partition\t995116\t\t2124\t\t100\n"
    
    with patch("os.path.exists", return_value=True):
        m = mock_open()
        m.side_effect = [
            mock_open(read_data=fake_meminfo).return_value,
            mock_open(read_data=fake_swaps).return_value
        ]
        with patch("builtins.open", m):
            ok, msg = health.check_memory_zram()
            assert ok
            assert "zram está ativo" in msg

def test_check_memory_zram_low_ram_no_swap():
    fake_meminfo = "MemTotal:        1000000 kB\n"
    fake_swaps = "Filename\t\t\t\tType\t\tSize\t\tUsed\t\tPriority\n"
    
    with patch("os.path.exists", return_value=True):
        m = mock_open()
        m.side_effect = [
            mock_open(read_data=fake_meminfo).return_value,
            mock_open(read_data=fake_swaps).return_value
        ]
        with patch("builtins.open", m):
            ok, msg = health.check_memory_zram()
            assert not ok
            assert "Risco de Out Of Memory" in msg

def test_check_env_secrets_groq(mock_config):
    mock_config.TELEGRAM_TOKEN = "1234567890_abcdef"
    mock_config.AI_PROVIDER = "groq"
    mock_config.GROQ_API_KEY = None
    
    ok, missing = health.check_env_secrets()
    assert not ok
    assert "GROQ_API_KEY" in missing
    
    mock_config.GROQ_API_KEY = "g_1234567890_abcdef"
    ok, missing = health.check_env_secrets()
    assert ok

def test_check_env_secrets_gemini(mock_config):
    mock_config.TELEGRAM_TOKEN = "1234567890_abcdef"
    mock_config.AI_PROVIDER = "gemini"
    mock_config.GEMINI_API_KEY = None
    
    ok, missing = health.check_env_secrets()
    assert not ok
    assert "GEMINI_API_KEY" in missing

def test_check_system_dependencies():
    with patch("shutil.which", return_value=None):
        ok, missing = health.check_system_dependencies()
        assert not ok
        assert "ffmpeg" in missing

    with patch("shutil.which", return_value="/usr/bin/ffmpeg"):
        ok, missing = health.check_system_dependencies()
        assert ok

def test_check_connectivity_ok(mock_config):
    mock_config.AI_PROVIDER = "groq"
    with patch("urllib.request.urlopen") as mock_url:
        ok, failures = health.check_connectivity()
        assert ok
        assert len(failures) == 0

def test_check_connectivity_fail(mock_config):
    mock_config.AI_PROVIDER = "groq"
    with patch("urllib.request.urlopen", side_effect=Exception("Timeout")):
        ok, failures = health.check_connectivity()
        assert not ok
        assert len(failures) > 0
        assert "Timeout" in failures[0]

def test_check_git_ok():
    from unittest.mock import Mock
    mock_branch = Mock(stdout="main\n")
    mock_status = Mock(stdout="")
    
    with patch("subprocess.run", side_effect=[mock_branch, mock_status]):
        status, msg = health.check_git()
        assert status == "ok"
        assert "limpa" in msg

def test_run_full_diagnostic():
    with patch("core.health.check_memory_zram", return_value=(True, "OK")), \
         patch("core.health.check_env_secrets", return_value=(True, [])), \
         patch("core.health.check_system_dependencies", return_value=(True, [])), \
         patch("core.health.check_connectivity", return_value=(True, [])), \
         patch("core.health.check_git", return_value=("ok", "Clean")):
         
         report = health.run_full_diagnostic()
         assert report["status"] == "ok"
         assert len(report["issues"]) == 0
