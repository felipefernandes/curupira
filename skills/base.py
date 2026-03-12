from abc import ABC, abstractmethod
from typing import Any, Dict

class BaseSkill(ABC):
    """
    Abstract Base Class for all Curupira Skills.
    Enforces a standard interface for integration with the Agent Brain.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """The unique name of the skill (e.g., 'get_weather')."""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """A clear description of what the skill does, used by the LLM to choose it."""
        pass
    
    @property
    def display_name(self) -> str:
        """Human-friendly name for display to users (e.g., '🌦️ Previsão do Tempo').
        Defaults to the technical name. Override in subclasses for friendlier labels."""
        return self.name

    @property
    def skill_group(self) -> str:
        """Group identifier for this skill tool (e.g., 'github', 'reminders').
        Tools sharing the same group are condensed into one entry in the capabilities summary.
        Defaults to the tool's own name (no grouping)."""
        return self.name

    @property
    def skill_group_emoji(self) -> str:
        """Emoji representing this skill group in the capabilities summary.
        Defaults to a generic wrench emoji."""
        return "🔧"
    
    @property
    @abstractmethod
    def parameters(self) -> Dict[str, Any]:
        """
        JSON Schema defining the parameters this skill accepts.
        Must follow OpenAI Function Calling / MCP Tool format.
        """
        pass
    
    @abstractmethod
    async def execute(self, context: Dict[str, Any], **kwargs) -> Any:
        """
        Executes the skill logic.
        
        Args:
            context: A dictionary containing execution context (e.g., user_id).
            **kwargs: The arguments provided by the LLM, matching the parameters schema.
            
        Returns:
            Any: The result of the execution, which will be serialized back to the LLM.
        """
        pass

    def success(self, data: Any, message: str = None) -> Dict[str, Any]:
        """
        Formats a successful skill execution into a standard MCP-Lite JSON output.
        
        Args:
            data: The main payload or results of the skill execution.
            message: Optional display message or operational context.
            
        Returns:
            Dict[str, Any]: A structured success response.
        """
        response = {
            "status": "success",
            "data": data
        }
        if message:
            response["message"] = message
        return response

    def error(self, error_message: str) -> Dict[str, Any]:
        """
        Formats a failed skill execution into a standard MCP-Lite JSON output.
        
        Args:
            error_message: The description of what went wrong.
            
        Returns:
            Dict[str, Any]: A structured error response.
        """
        return {
            "status": "error",
            "error": error_message
        }
