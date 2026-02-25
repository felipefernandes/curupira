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
    def display_name(self) -> str:
        return "🔍 Minhas Capacidades"

    @property
    def description(self) -> str:
        return "Lista as capacidades e parâmetros das ferramentas do sistema."

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
            if skill_name not in self._agent.skills or skill_name == self.name:
                available = [
                    s.name for s in self._agent.skills.values()
                    if s.name != self.name
                ]
                return self.error(f"Skill '{skill_name}' não encontrada. Available: {', '.join(available)}")
            
            desc = self._describe_skill(skill_name)
            return self.success(desc)
        else:
            return self.success(self._list_all_skills())

    def _list_all_skills(self) -> Dict[str, Any]:
        """Returns a summary of all registered skills."""
        skills_list = []
        for sk in self._agent.skills.values():
            # Skip self to avoid circular "I can describe myself"
            if sk.name == self.name:
                continue
            skills_list.append({
                "name": sk.name,
                "display_name": sk.display_name,
                "description": sk.description
            })

        return {
            "total": len(skills_list),
            "skills": skills_list
        }

    def _describe_skill(self, skill_name: str) -> Dict[str, Any]:
        """Returns detailed info for a specific skill."""
        skill = self._agent.skills.get(skill_name)

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
            "display_name": skill.display_name,
            "description": skill.description,
            "parameters": param_details
        }
