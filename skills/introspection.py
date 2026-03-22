"""
Skill de Introspecção: permite ao bot descrever suas próprias capacidades.
Ref: Issue #55 - https://github.com/felipefernandes/curupira/issues/55
"""

from typing import Any, Dict, List, Optional
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
        return (
            "Lista as capacidades e parâmetros das ferramentas do sistema. "
            "Quando chamada sem argumentos, retorna o campo 'message' com a lista "
            "formatada — apresente-a diretamente ao usuário sem reformatar."
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
            # Check if group or tool exists
            group_tools = [
                sk for sk in self._agent.skills.values()
                if sk.skill_group == skill_name and sk.name != self.name
            ]
            tool_match = self._agent.skills.get(skill_name)
            if not group_tools and (not tool_match or tool_match.name == self.name):
                summary = self._list_all_skills()
                return self.error(
                    f"Skill '{skill_name}' não encontrada.\n\n"
                    + self._format_groups_summary(summary["groups"])
                )
            
            desc = self._describe_skill(skill_name)
            return self.success(desc)
        else:
            data = self._list_all_skills()
            return self.success(data, message=self._format_groups_summary(data["groups"]))

    def _list_all_skills(self) -> Dict[str, Any]:
        """Returns a grouped summary of all registered skills, one entry per skill_group."""
        groups: Dict[str, Dict] = {}
        for sk in self._agent.skills.values():
            if sk.name == self.name:
                continue
            group = sk.skill_group
            if group not in groups:
                groups[group] = {
                    "group": group,
                    "emoji": sk.skill_group_emoji,
                    "descriptions": [],
                }
            groups[group]["descriptions"].append(sk.description)

        summary = []
        for group_data in groups.values():
            # Combine all tool descriptions into one summary per group
            combined = "; ".join(group_data["descriptions"])
            summary.append({
                "group": group_data["group"],
                "emoji": group_data["emoji"],
                "summary": combined,
            })

        return {
            "total_groups": len(summary),
            "groups": summary,
        }

    def _describe_skill(self, skill_name: str) -> Dict[str, Any]:
        """Returns detailed info for all tools in a skill_group (or a single tool by name)."""
        # Primary: match by skill_group
        group_tools = [
            sk for sk in self._agent.skills.values()
            if sk.skill_group == skill_name and sk.name != self.name
        ]
        if not group_tools:
            # Fallback: match by exact tool name (backward compatibility)
            sk = self._agent.skills.get(skill_name)
            if sk:
                group_tools = [sk]

        tools_detail = []
        for skill in group_tools:
            params = skill.parameters
            param_details = []
            properties = params.get("properties", {})
            required = params.get("required", [])
            for param_name, param_schema in properties.items():
                param_details.append({
                    "name": param_name,
                    "type": param_schema.get("type", "any"),
                    "description": param_schema.get("description", ""),
                    "required": param_name in required,
                })
            tools_detail.append({
                "name": skill.name,
                "display_name": skill.display_name,
                "description": skill.description,
                "parameters": param_details,
            })

        return {
            "group": skill_name,
            "emoji": group_tools[0].skill_group_emoji if group_tools else "🔧",
            "tools": tools_detail,
        }

    def _format_groups_summary(self, groups: List[Dict]) -> str:
        """Formats a grouped skills list into a human-readable string using HTML tags."""
        lines = ["Aqui estão as capacidades disponíveis:"]
        for g in groups:
            lines.append(f"{g['emoji']} <b>{g['group'].capitalize()}</b> — {g['summary']}")
        return "\n".join(lines)
