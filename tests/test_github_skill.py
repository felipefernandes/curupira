"""Tests for skills/github.py configure() function."""

import os
import sys
import importlib
import pytest
from unittest.mock import patch, MagicMock

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import MCP_SERVERS


def _fresh_configure(**env_overrides):
    """
    Reimport skills.github to get a fresh configure() with clean state.
    Patches os.path.exists to always return True for the server script
    (since the actual path varies by OS/CI environment).
    """
    # Remove cached module to force re-evaluation
    if "skills.github" in sys.modules:
        del sys.modules["skills.github"]

    # Set env vars for this call
    original_env = {}
    for key, value in env_overrides.items():
        original_env[key] = os.environ.get(key)
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value

    try:
        import skills.github
        return skills.github.configure
    finally:
        # Restore original env
        for key, orig in original_env.items():
            if orig is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = orig


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
        # Clean cached module
        sys.modules.pop("skills.github", None)

    def test_configure_registers_server(self):
        """configure() should add 'github' to MCP_SERVERS when token is set."""
        os.environ["GITHUB_PERSONAL_ACCESS_TOKEN"] = "ghp_test_token_123"
        sys.modules.pop("skills.github", None)

        with patch("os.path.exists", return_value=True):
            import skills.github
            result = skills.github.configure()

        assert result is True
        assert "github" in MCP_SERVERS
        assert "args" in MCP_SERVERS["github"]

    def test_configure_skips_if_already_configured(self):
        """configure() should be a no-op if 'github' is already in MCP_SERVERS."""
        MCP_SERVERS["github"] = {"command": "existing"}
        sys.modules.pop("skills.github", None)

        import skills.github
        result = skills.github.configure()

        assert result is True  # Already configured = success
        assert MCP_SERVERS["github"]["command"] == "existing"

    def test_configure_skips_without_token(self):
        """configure() should skip and return False when token is missing."""
        os.environ.pop("GITHUB_PERSONAL_ACCESS_TOKEN", None)
        sys.modules.pop("skills.github", None)

        with patch("os.path.exists", return_value=True):
            import skills.github
            result = skills.github.configure()

        assert "github" not in MCP_SERVERS
        assert result is False

    def test_configure_skips_if_script_missing(self):
        """configure() should skip if github_server.py doesn't exist."""
        os.environ["GITHUB_PERSONAL_ACCESS_TOKEN"] = "ghp_test_token_123"
        sys.modules.pop("skills.github", None)

        with patch("os.path.exists", return_value=False):
            import skills.github
            result = skills.github.configure()

        assert "github" not in MCP_SERVERS
        assert result is False

    def test_configure_warns_on_suspicious_token(self):
        """configure() should log warning for tokens that don't start with 'ghp_'."""
        os.environ["GITHUB_PERSONAL_ACCESS_TOKEN"] = "invalid_format_token"
        sys.modules.pop("skills.github", None)

        with patch("os.path.exists", return_value=True):
            import skills.github
            with patch.object(skills.github, "logger") as mock_logger:
                result = skills.github.configure()

        # Should still configure (token format is just a warning)
        assert result is True
        assert "github" in MCP_SERVERS
        mock_logger.warning.assert_called()
