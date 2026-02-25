"""Tests for skills/introspection.py IntrospectionSkill."""

import os
import sys
import pytest
from unittest.mock import MagicMock, PropertyMock

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from skills.introspection import IntrospectionSkill


def _make_mock_skill(name, description, display_name=None, parameters=None):
    """Helper to create a mock skill with properties."""
    skill = MagicMock()
    type(skill).name = PropertyMock(return_value=name)
    type(skill).display_name = PropertyMock(return_value=display_name or name)
    type(skill).description = PropertyMock(return_value=description)
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
        
        assert data["total"] == 2  # Excludes itself
        skill_names = [s["name"] for s in data["skills"]]
        assert "get_weather" in skill_names
        assert "github_list_issues" in skill_names
        assert "describe_capabilities" not in skill_names  # Self excluded

        # Verify display_name is present
        for s in data["skills"]:
            assert "display_name" in s

    @pytest.mark.asyncio
    async def test_describe_specific_skill(self):
        """Test describing a specific skill."""
        result = await self.skill.execute({}, skill_name="get_weather")

        assert result["status"] == "success"
        data = result["data"]

        assert data["name"] == "get_weather"
        assert data["display_name"] == "🌦️ Previsão do Tempo"
        assert "weather" in data["description"].lower()
        assert len(data["parameters"]) == 1
        assert data["parameters"][0]["name"] == "city"
        assert data["parameters"][0]["required"] is True

    @pytest.mark.asyncio
    async def test_describe_skill_with_multiple_params(self):
        """Test describing a skill with multiple parameters."""
        result = await self.skill.execute({}, skill_name="github_list_issues")

        assert result["status"] == "success"
        data = result["data"]

        assert data["name"] == "github_list_issues"
        assert len(data["parameters"]) == 2
        
        param_names = [p["name"] for p in data["parameters"]]
        assert "repo_name" in param_names
        assert "state" in param_names

        # Check required flag
        for p in data["parameters"]:
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
        assert "get_weather" in result["error"]
        assert "describe_capabilities" not in result["error"]  # Self excluded
