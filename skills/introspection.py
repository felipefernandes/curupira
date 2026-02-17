"""
Skill de Introspecção: permite ao bot descrever suas próprias capacidades.
Ref: Issue #55 - https://github.com/felipefernandes/curupira/issues/55
"""

import json
from typing import Any, Dict, Optional
from skills.base import BaseSkill


class IntrospectionSkill(BaseSkill):
    """
    Built-in skill that allows the bot to introspect and describe
    its registered capabilities to the user.
    """

    def __init__(self, agent):
        """
        Args:
            agent: Reference to the AgentBrain instance for accessing
                   the skill registry at runtime.
        """
        self._agent = agent

    @property
    def name(self) -> str:
        return "describe_capabilities"

    @property
    def description(self) -> str:
        return (
            "Lists available skills and their capabilities. "
            "Call without arguments to see all skills, or pass "
            "skill_name to get detailed parameters for a specific skill."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "skill_name": {
                    "type": "string",
                    "description": (
                        "Optional. The name of a specific skill to get "
                        "detailed information about. If omitted, lists all skills."
                    )
                }
            },
            "required": []
        }

    async def execute(self, context: Dict[str, Any], **kwargs) -> Any:
        """
        Executes the introspection logic.

        - No args: returns a summary list of all skills.
        - skill_name provided: returns detailed info for that skill.
        """
        skill_name: Optional[str] = kwargs.get("skill_name")

        if skill_name:
            return self._describe_skill(skill_name)
        else:
            return self._list_all_skills()

    def _list_all_skills(self) -> Dict[str, Any]:
        """Returns a summary of all registered skills."""
        skills_list = []
        for sk in self._agent.skills.values():
            # Skip self to avoid circular "I can describe myself"
            if sk.name == self.name:
                continue
            skills_list.append({
                "name": sk.name,
                "description": sk.description
            })

        return {
            "total": len(skills_list),
            "skills": skills_list
        }

    def _describe_skill(self, skill_name: str) -> Dict[str, Any]:
        """Returns detailed info for a specific skill."""
        skill = self._agent.skills.get(skill_name)

        if not skill:
            available = [
                s.name for s in self._agent.skills.values()
                if s.name != self.name
            ]
            return {
                "error": f"Skill '{skill_name}' não encontrada.",
                "available_skills": available
            }

        params = skill.parameters
        param_details = []
        properties = params.get("properties", {})
        required = params.get("required", [])

        for param_name, param_schema in properties.items():
            param_details.append({
                "name": param_name,
                "type": param_schema.get("type", "any"),
                "description": param_schema.get("description", ""),
                "required": param_name in required
            })

        return {
            "name": skill.name,
            "description": skill.description,
            "parameters": param_details
        }
