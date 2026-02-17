"""Tests for skills/introspection.py IntrospectionSkill."""

import os
import sys
import pytest
from unittest.mock import MagicMock, PropertyMock

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from skills.introspection import IntrospectionSkill


def _make_mock_skill(name, description, parameters=None):
    """Helper to create a mock skill with properties."""
    skill = MagicMock()
    type(skill).name = PropertyMock(return_value=name)
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
            {
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
            {
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
        """Test skill name, description, and parameters."""
        assert self.skill.name == "describe_capabilities"
        assert "capabilities" in self.skill.description.lower()
        assert self.skill.parameters["type"] == "object"
        assert "skill_name" in self.skill.parameters["properties"]

    @pytest.mark.asyncio
    async def test_list_all_skills(self):
        """Test listing all skills (no args)."""
        result = await self.skill.execute({})

        assert result["total"] == 2  # Excludes itself
        skill_names = [s["name"] for s in result["skills"]]
        assert "get_weather" in skill_names
        assert "github_list_issues" in skill_names
        assert "describe_capabilities" not in skill_names  # Self excluded

    @pytest.mark.asyncio
    async def test_describe_specific_skill(self):
        """Test describing a specific skill."""
        result = await self.skill.execute({}, skill_name="get_weather")

        assert result["name"] == "get_weather"
        assert "weather" in result["description"].lower()
        assert len(result["parameters"]) == 1
        assert result["parameters"][0]["name"] == "city"
        assert result["parameters"][0]["required"] is True

    @pytest.mark.asyncio
    async def test_describe_skill_with_multiple_params(self):
        """Test describing a skill with multiple parameters."""
        result = await self.skill.execute({}, skill_name="github_list_issues")

        assert result["name"] == "github_list_issues"
        assert len(result["parameters"]) == 2
        
        param_names = [p["name"] for p in result["parameters"]]
        assert "repo_name" in param_names
        assert "state" in param_names

        # Check required flag
        for p in result["parameters"]:
            if p["name"] == "repo_name":
                assert p["required"] is True
            elif p["name"] == "state":
                assert p["required"] is False

    @pytest.mark.asyncio
    async def test_describe_nonexistent_skill(self):
        """Test error handling for non-existent skill."""
        result = await self.skill.execute({}, skill_name="fly")

        assert "error" in result
        assert "fly" in result["error"]
        assert "available_skills" in result
        assert "get_weather" in result["available_skills"]
        assert "describe_capabilities" not in result["available_skills"]  # Self excluded
