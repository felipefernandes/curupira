# Proposal: Implement Hardware Monitoring Skill

## Why
As defined in `ROADMAP.md` and `openspec/project.md`, Curupira runs on resource-constrained hardware (Raspberry Pi). Monitoring its own health is crucial for stability. The user explicitly requested an objective response format using emojis.

## What Changes
- Add `HardwareMonitoringSkill` using `psutil`.
- Add `psutil` to `requirements.txt`.
- Register the new skill in `bot.py` and `AgentBrain`.

## Impact
- **Affected specs:** `monitoring` (new capability)
- **Affected code:** `skills/hardware.py`, `bot.py`, `agent.py`, `requirements.txt`

