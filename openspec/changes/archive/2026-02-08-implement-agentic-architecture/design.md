# Architecture Design: Lightweight Agentic Core

## Goals
- **Low Overhead:** Must run on Raspberry Pi 3 (1GB RAM). Avoid heavy frameworks like LangChain/LangGraph.
- **Provider Agnostic:** Logic must work for both Gemini and Groq (LLaMA 3).
- **Extensible:** Adding a skill should be as simple as adding a file.

## Core Components

### 1. `BaseSkill` (Abstract Class)
Standard interface for all tools.
```python
class BaseSkill(ABC):
    @property
    @abstractmethod
    def name(self) -> str: pass
    
    @property
    @abstractmethod
    def description(self) -> str: pass
    
    @property
    @abstractmethod
    def parameters_schema(self) -> dict: pass # JSON Schema
    
    @abstractmethod
    async def execute(self, **kwargs) -> Any: pass
```

### 2. The "Brain" (Agent Loop)
Instead of a complex graph, we use a simple **ReAct-like** loop or native **Tool Use** API.
Since both Gemini and Groq support tool use, we will prefer the **Native Tool Use** approach for reliability.

**Flow:**
1. User Message -> `AgentBrain`
2. `AgentBrain` prepares prompt + Tool Definitions (JSON schemas from enabled Skills).
3. Call LLM (`tools=[...]`).
4. **IF** LLM wants to call a function:
   a. `AgentBrain` executes the corresponding `Skill.execute()`.
   b. `AgentBrain` appends result to history.
   c. Recurring call to LLM (with history + result).
5. **ELSE** (LLM returns text):
   a. Return text to user.

### 3. MCP Compatibility
To support MCP later, we will create an `MCPSkillAdapter` that wraps an MCP Tool into our `BaseSkill` interface.
`BaseSkill.parameters_schema` matches the MCP Tool schema format, ensuring future compatibility.

## Migration Strategy
1. Create `BaseSkill`.
2. Port `WeatherManager` and `ReminderManager` to this new structure.
3. Rewrite `get_ai_response` in `bot.py` to handle the tool execution loop.
4. Remove Regex handlers from `responder()`.
