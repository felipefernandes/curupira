# Design: Skill Introspection

## Architecture via `IntrospectionSkill`

To avoid polluting the `AgentBrain` logic with introspection details, we will implement this as a standard **Skill**.

### 1. `IntrospectionSkill` Class
- **Location**: `skills/introspection.py`
- **Inheritance**: `BaseSkill`
- **Constructor**: Accepts an `agent_ref` (the `AgentBrain` instance) to access `self.agent.skills` dynamically at runtime. This ensures it always reflects the current state, including newly added MCP skills.

### 2. Tool Definition
- **Name**: `describe_capabilities`
- **Description**: "Lists available skills and their capabilities. Can provide detailed documentation for a specific skill."
- **Parameters**:
  - `skill_name` (optional): The name of the skill to inspect.

### 3. Execution Logic
- **List Mode** (no args):
  - Iterates over `agent.skills.values()`.
  - Returns a formatted string (Markdown) listing:
    - Name
    - Description (first line)
- **Detail Mode** (`skill_name` provided):
  - Looks up skill in `agent.skills`.
  - Returns full description + parameter schema (JSON Schema formatted as readable text).

## Integration
- In `AgentBrain.__init__`, initialize `IntrospectionSkill(self)` and register it.
- This creates a circular reference (`AgentBrain` -> `Skill` -> `AgentBrain`), but Python handles this fine with GC. Alternatively, pass a `get_skills_callback` to avoid direct dependency if preferred, but direct reference is simpler for "internal" skills.

## Security
- `describe_capabilities` exposes what the bot *can* do, not internal secrets.
- Parameter schemas are public API.
- Safe to expose.
