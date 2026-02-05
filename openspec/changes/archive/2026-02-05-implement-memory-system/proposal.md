# Implement Memory System (Phase 2)

## Summary
Implement a dual-layer memory system (Short-term & Long-term) for the Curupira bot using SQLite. This will allow the bot to remember user preferences, maintain conversation context across restarts, and personalized interactions, adhering to the project's "lite" and "headless" philosophy.

## Rationale
The current bot is stateless. To fulfill the "Personalization" and "Automation" goals of the roadmap, the bot needs to retain information about the user (name, preferences) and the immediate context (conversation history) efficiently on constrained hardware (Raspberry Pi 3).

## Proposed Features
- **Long-term Memory (SQLite):** Storage for user profiles, persistent facts, and system logs.
- **Short-term Memory (Context Window):** Retrieval of recent conversation history to inject into LLM prompts.
- **Memory Manager:** A modular class to handle DB operations and context management.
