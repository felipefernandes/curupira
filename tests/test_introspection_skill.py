"""Tests for skills/introspection.py IntrospectionSkill."""

import os
import sys
import pytest
from unittest.mock import MagicMock, PropertyMock

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from skills.introspection import IntrospectionSkill


def _make_mock_skill(name, description, display_name=None, parameters=None,
                     skill_group=None, skill_group_emoji="🔧"):
    """Helper to create a mock skill with properties."""
    skill = MagicMock()
    type(skill).name = PropertyMock(return_value=name)
    type(skill).display_name = PropertyMock(return_value=display_name or name)
    type(skill).description = PropertyMock(return_value=description)
    type(skill).skill_group = PropertyMock(return_value=skill_group or name)
    type(skill).skill_group_emoji = PropertyMock(return_value=skill_group_emoji)
    type(skill).parameters = PropertyMock(return_value=parameters or {
        "type": "object",
        "properties": {},
        "required": []
    })
    return skill


class TestIntrospectionSkill:
    """Tests for IntrospectionSkill."""

    def setup_method(self):
        self.mock_agent = MagicMock()
        self.skill = IntrospectionSkill(self.mock_agent)

        # Register some fake skills in the mock agent
        self.weather_skill = _make_mock_skill(
            "get_weather",
            "Gets weather forecast for a city.",
            display_name="🌦️ Previsão do Tempo",
            skill_group="weather",
            skill_group_emoji="🌦️",
            parameters={
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "City name"}
                },
                "required": ["city"]
            }
        )
        self.github_skill = _make_mock_skill(
            "github_list_issues",
            "Lists open issues in a GitHub repository.",
            display_name="🔗 Github List Issues",
            skill_group="github",
            skill_group_emoji="🐙",
            parameters={
                "type": "object",
                "properties": {
                    "repo_name": {"type": "string", "description": "Repository full name"},
                    "state": {"type": "string", "description": "Issue state filter"}
                },
                "required": ["repo_name"]
            }
        )

        self.mock_agent.skills = {
            "describe_capabilities": self.skill,
            "get_weather": self.weather_skill,
            "github_list_issues": self.github_skill
        }

    def test_skill_properties(self):
        """Test skill name, description, display_name, and parameters."""
        assert self.skill.name == "describe_capabilities"
        assert self.skill.display_name == "🔍 Minhas Capacidades"
        assert "capacidades" in self.skill.description.lower()
        assert self.skill.parameters["type"] == "object"
        assert "skill_name" in self.skill.parameters["properties"]

    @pytest.mark.asyncio
    async def test_list_all_skills(self):
        """Test listing all skills (no args)."""
        result = await self.skill.execute({})

        assert result["status"] == "success"
        data = result["data"]

        assert data["total_groups"] == 2  # Excludes itself; 2 groups: weather + github
        group_names = [g["group"] for g in data["groups"]]
        assert "weather" in group_names
        assert "github" in group_names
        assert "describe_capabilities" not in group_names  # Self excluded

        # Verify emoji and summary are present per group
        for g in data["groups"]:
            assert "emoji" in g
            assert "summary" in g

    @pytest.mark.asyncio
    async def test_describe_specific_skill(self):
        """Test describing a skill group by group name."""
        result = await self.skill.execute({}, skill_name="weather")

        assert result["status"] == "success"
        data = result["data"]

        assert data["group"] == "weather"
        assert data["emoji"] == "🌦️"
        assert len(data["tools"]) == 1
        tool = data["tools"][0]
        assert tool["name"] == "get_weather"
        assert tool["display_name"] == "🌦️ Previsão do Tempo"
        assert "weather" in tool["description"].lower()
        assert len(tool["parameters"]) == 1
        assert tool["parameters"][0]["name"] == "city"
        assert tool["parameters"][0]["required"] is True

    @pytest.mark.asyncio
    async def test_describe_skill_with_multiple_params(self):
        """Test describing a skill group that has a tool with multiple parameters."""
        result = await self.skill.execute({}, skill_name="github")

        assert result["status"] == "success"
        data = result["data"]

        assert data["group"] == "github"
        assert len(data["tools"]) == 1
        tool = data["tools"][0]
        assert tool["name"] == "github_list_issues"
        assert len(tool["parameters"]) == 2

        param_names = [p["name"] for p in tool["parameters"]]
        assert "repo_name" in param_names
        assert "state" in param_names

        # Check required flag
        for p in tool["parameters"]:
            if p["name"] == "repo_name":
                assert p["required"] is True
            elif p["name"] == "state":
                assert p["required"] is False

    @pytest.mark.asyncio
    async def test_describe_nonexistent_skill(self):
        """Test error handling for non-existent skill."""
        result = await self.skill.execute({}, skill_name="fly")

        assert result["status"] == "error"
        assert "fly" in result["error"]
        # Error message shows grouped summary (group names are capitalized for display)
        error_lower = result["error"].lower()
        assert "weather" in error_lower
        assert "github" in error_lower
        assert "describe_capabilities" not in result["error"]  # Self excluded

    @pytest.mark.asyncio
    async def test_describe_skill_by_exact_tool_name_fallback(self):
        """Fallback: describe a tool by its exact name when no group name matches."""
        # "get_weather" is an exact tool name; no skill has skill_group == "get_weather"
        result = await self.skill.execute({}, skill_name="get_weather")

        assert result["status"] == "success"
        data = result["data"]
        assert len(data["tools"]) == 1
        assert data["tools"][0]["name"] == "get_weather"

    @pytest.mark.asyncio
    async def test_list_all_skills_shows_full_description(self):
        """Descriptions should be displayed in full without truncation."""
        long_description = "A" * 130
        long_skill = _make_mock_skill(
            "verbose_tool",
            long_description,
            skill_group="verbose",
            skill_group_emoji="🔤",
        )
        self.mock_agent.skills["verbose_tool"] = long_skill

        result = await self.skill.execute({})

        assert result["status"] == "success"
        verbose_group = next(
            g for g in result["data"]["groups"] if g["group"] == "verbose"
        )
        assert verbose_group["summary"] == long_description
        assert not verbose_group["summary"].endswith("...")
