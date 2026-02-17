"""Tests for skills/github.py configure() function."""

import os
import sys
import pytest
from unittest.mock import patch, MagicMock

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import MCP_SERVERS


class TestGithubConfigure:
    """Tests for the GitHub skill configuration."""

    def setup_method(self):
        """Clear any existing github config before each test."""
        MCP_SERVERS.pop("github", None)
        self._original_token = os.environ.get("GITHUB_PERSONAL_ACCESS_TOKEN")

    def teardown_method(self):
        """Restore original state after each test."""
        MCP_SERVERS.pop("github", None)
        if self._original_token is not None:
            os.environ["GITHUB_PERSONAL_ACCESS_TOKEN"] = self._original_token
        else:
            os.environ.pop("GITHUB_PERSONAL_ACCESS_TOKEN", None)

    def test_configure_registers_server(self):
        """configure() should add 'github' to MCP_SERVERS when token is set."""
        os.environ["GITHUB_PERSONAL_ACCESS_TOKEN"] = "ghp_test_token_123"
        from skills.github import configure
        result = configure()
        assert "github" in MCP_SERVERS
        assert result is True
        assert "args" in MCP_SERVERS["github"]

    def test_configure_skips_if_already_configured(self):
        """configure() should be a no-op if 'github' is already in MCP_SERVERS."""
        MCP_SERVERS["github"] = {"command": "existing"}
        from skills.github import configure
        result = configure()
        assert result is True  # Already configured = success
        assert MCP_SERVERS["github"]["command"] == "existing"

    def test_configure_skips_without_token(self):
        """configure() should skip and return False when token is missing."""
        os.environ.pop("GITHUB_PERSONAL_ACCESS_TOKEN", None)
        from skills.github import configure
        result = configure()
        assert "github" not in MCP_SERVERS
        assert result is False

    def test_configure_skips_if_script_missing(self):
        """configure() should skip if github_server.py doesn't exist."""
        os.environ["GITHUB_PERSONAL_ACCESS_TOKEN"] = "ghp_test_token_123"
        from skills.github import configure
        with patch("skills.github.os.path.exists", return_value=False):
            result = configure()
        assert "github" not in MCP_SERVERS
        assert result is False

    def test_configure_warns_on_suspicious_token(self):
        """configure() should log warning for tokens that don't start with 'ghp_'."""
        os.environ["GITHUB_PERSONAL_ACCESS_TOKEN"] = "invalid_format_token"
        from skills.github import configure
        with patch("skills.github.logger") as mock_logger:
            result = configure()
        # Should still configure (token format is just a warning)
        assert "github" in MCP_SERVERS
        assert result is True
        mock_logger.warning.assert_called()
