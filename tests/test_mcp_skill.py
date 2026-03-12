"""Tests for skills/mcp_skill.py MCPSkill and skills/base.py BaseSkill."""

import os
import sys
import pytest
from unittest.mock import MagicMock, AsyncMock

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from skills.mcp_skill import MCPSkill
from skills.base import BaseSkill


class TestMCPSkillDisplayName:
    """Tests for MCPSkill display_name auto-generation."""

    def test_display_name_humanizes_underscores(self):
        """github_list_repos -> '🔗 Github List Repos'"""
        client = MagicMock()
        tool_def = {"name": "github_list_repos", "description": "List repos"}
        skill = MCPSkill(client, tool_def)

        assert skill.name == "github_list_repos"
        assert skill.display_name == "🔗 Github List Repos"

    def test_display_name_single_word(self):
        """search -> '🔗 Search'"""
        client = MagicMock()
        tool_def = {"name": "search", "description": "Search stuff"}
        skill = MCPSkill(client, tool_def)

        assert skill.display_name == "🔗 Search"

    def test_display_name_with_multiple_underscores(self):
        """github_create_issue -> '🔗 Github Create Issue'"""
        client = MagicMock()
        tool_def = {"name": "github_create_issue", "description": "Create issue"}
        skill = MCPSkill(client, tool_def)

        assert skill.display_name == "🔗 Github Create Issue"

    def test_mcp_skill_properties(self):
        """Test basic MCPSkill properties."""
        client = MagicMock()
        tool_def = {
            "name": "test_tool",
            "description": "A test tool",
            "inputSchema": {
                "type": "object",
                "properties": {"arg1": {"type": "string"}}
            }
        }
        skill = MCPSkill(client, tool_def)

        assert skill.name == "test_tool"
        assert skill.description == "A test tool"
        assert "arg1" in skill.parameters["properties"]

    def test_skill_group_derives_from_prefix(self):
        """github_list_repos -> skill_group == 'github'"""
        client = MagicMock()
        skill = MCPSkill(client, {"name": "github_list_repos"})
        assert skill.skill_group == "github"

    def test_skill_group_no_underscore(self):
        """'search' (no underscore) -> skill_group == 'search'"""
        client = MagicMock()
        skill = MCPSkill(client, {"name": "search"})
        assert skill.skill_group == "search"

    def test_skill_group_emoji_github(self):
        """github tools should use the octopus emoji."""
        client = MagicMock()
        skill = MCPSkill(client, {"name": "github_create_issue"})
        assert skill.skill_group_emoji == "🐙"

    def test_skill_group_emoji_unknown_defaults_to_link(self):
        """Unknown prefixes should fall back to the generic link emoji."""
        client = MagicMock()
        skill = MCPSkill(client, {"name": "notion_create_page"})
        assert skill.skill_group_emoji == "🔗"

    @pytest.mark.asyncio
    async def test_mcp_skill_execute_calls_client(self):
        """Test that execute delegates to client.call_tool."""
        client = MagicMock()
        client.call_tool = AsyncMock(return_value={"result": "ok"})
        tool_def = {"name": "test_tool", "description": "Test"}
        skill = MCPSkill(client, tool_def)

        result = await skill.execute({}, arg1="value1")

        client.call_tool.assert_called_once_with("test_tool", {"arg1": "value1"})
        assert result == {"result": "ok"}


class TestBaseSkillDisplayNameDefault:
    """Tests for BaseSkill.display_name default behavior."""

    def test_display_name_defaults_to_name(self):
        """A skill without display_name override should return its name."""

        class MinimalSkill(BaseSkill):
            @property
            def name(self):
                return "minimal_test"

            @property
            def description(self):
                return "A minimal skill"

            @property
            def parameters(self):
                return {"type": "object", "properties": {}}

            async def execute(self, context, **kwargs):
                return {}

        skill = MinimalSkill()
        assert skill.display_name == "minimal_test"  # Falls back to name
