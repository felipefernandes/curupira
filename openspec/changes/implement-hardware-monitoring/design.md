# Design: Hardware Monitoring Skill

## Overview
Adds a new skill `HardwareMonitoringSkill` to `skills/hardware.py`.

## Architecture
- **Inheritance:** Inherits from `BaseSkill`.
- **Dependency:** `psutil` (needs addition to `requirements.txt`).
- **Integration:** Registered in `bot.py` -> `AgentBrain`.

## Implementation Details

### `metrics` Functionality
- `cpu_percent`: `psutil.cpu_percent(interval=1)`
- `memory`: `psutil.virtual_memory()`
- `disk`: `psutil.disk_usage('/')`
- `temperature`: 
    - Linux (RPi): `psutil.sensors_temperatures()['cpu_thermal'][0].current`
    - Windows: Not natively supported by `psutil` without admin/WMI, often returns empty or requires specific hardware libs. **Fallback:** "N/A" or hide field.

### Output Style
> 📊 **Status do Sistema**
> 
> 🧠 **RAM:** 450MB / 1024MB (45%)
> ⚙️ **CPU:** 12%
> 🌡️ **Temp:** 48.5°C
> 💾 **Disco:** 15GB livres

## Trade-offs
- **Blocking Call:** `psutil.cpu_percent(interval=1)` blocks for 1 second.
- **Mitigation:** Use `interval=None` (non-blocking, returns last interval) OR run in a separate thread/executor to avoid blocking the asyncio loop. Since it's a "User Request" -> "Response" flow, a 1s delay is acceptable, but blocking the main loop affects other users (if any).
- **Decision:** Use `await asyncio.to_thread(psutil.cpu_percent, interval=1)` to ensure the main loop remains responsive.
