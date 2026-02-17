"""Tests for skills/github.py configure() function."""

import os
import sys
import importlib
import pytest
from unittest.mock import patch

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# We must import the module, then reload it to ensure clean state.
# The key insight: skills.github uses `from core.config import MCP_SERVERS`
# so we must access MCP_SERVERS via the SAME reference (skills.github module's copy).
import skills.github as github_module
from core import config


class TestGithubConfigure:
    """Tests for the GitHub skill configuration."""

    def setup_method(self):
        """Clear any existing github config and reload module for clean state."""
        self._original_token = os.environ.get("GITHUB_PERSONAL_ACCESS_TOKEN")
        # Clear from the actual config dict that skills.github references
        config.MCP_SERVERS.pop("github", None)

    def teardown_method(self):
        """Restore original state after each test."""
        config.MCP_SERVERS.pop("github", None)
        if self._original_token is not None:
            os.environ["GITHUB_PERSONAL_ACCESS_TOKEN"] = self._original_token
        else:
            os.environ.pop("GITHUB_PERSONAL_ACCESS_TOKEN", None)

    def test_configure_registers_server(self):
        """configure() should add 'github' to MCP_SERVERS when token is set."""
        os.environ["GITHUB_PERSONAL_ACCESS_TOKEN"] = "ghp_test_token_123"

        with patch.object(github_module, "_SERVER_SCRIPT", "/fake/path/github_server.py"):
            with patch("os.path.exists", return_value=True):
                result = github_module.configure()

        assert result is True
        assert "github" in config.MCP_SERVERS
        assert "args" in config.MCP_SERVERS["github"]

    def test_configure_skips_if_already_configured(self):
        """configure() should be a no-op if 'github' is already in MCP_SERVERS."""
        config.MCP_SERVERS["github"] = {"command": "existing"}

        result = github_module.configure()

        assert result is True
        assert config.MCP_SERVERS["github"]["command"] == "existing"

    def test_configure_skips_without_token(self):
        """configure() should skip and return False when token is missing."""
        os.environ.pop("GITHUB_PERSONAL_ACCESS_TOKEN", None)

        with patch.object(github_module, "_SERVER_SCRIPT", "/fake/path/github_server.py"):
            with patch("os.path.exists", return_value=True):
                result = github_module.configure()

        assert "github" not in config.MCP_SERVERS
        assert result is False

    def test_configure_skips_if_script_missing(self):
        """configure() should skip if github_server.py doesn't exist."""
        os.environ["GITHUB_PERSONAL_ACCESS_TOKEN"] = "ghp_test_token_123"

        with patch.object(github_module, "_SERVER_SCRIPT", "/nonexistent/path.py"):
            with patch("os.path.exists", return_value=False):
                result = github_module.configure()

        assert "github" not in config.MCP_SERVERS
        assert result is False

    def test_configure_warns_on_suspicious_token(self):
        """configure() should log warning for tokens that don't start with 'ghp_'."""
        os.environ["GITHUB_PERSONAL_ACCESS_TOKEN"] = "invalid_format_token"

        with patch.object(github_module, "_SERVER_SCRIPT", "/fake/path/github_server.py"):
            with patch("os.path.exists", return_value=True):
                with patch.object(github_module, "logger") as mock_logger:
                    result = github_module.configure()

        assert result is True
        assert "github" in config.MCP_SERVERS
        mock_logger.warning.assert_called()
