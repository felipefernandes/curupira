import asyncio
import psutil
import logging
from typing import Dict, Any
from .base import BaseSkill

class HardwareMonitoringSkill(BaseSkill):
    def __init__(self):
        self.logger = logging.getLogger("HardwareMonitoringSkill")

    @property
    def name(self) -> str:
        return "hardware_monitoring"

    @property
    def description(self) -> str:
        return "Returns current system hardware status (CPU, RAM, Disk, Temperature)."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {"type": "object", "properties": {}}

    async def execute(self, context: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        Retrieves hardware metrics.
        Runs blocking psutil calls in a separate thread to avoid freezing the bot.
        """
        try:
            # Run blocking I/O in thread
            metrics = await asyncio.to_thread(self._get_metrics)
            
            # Format output with emojis
            summary = (
                f"🌡️ **Status do Sistema**\n\n"
                f"🧠 **RAM:** {metrics['ram_used']}/{metrics['ram_total']} ({metrics['ram_percent']}%)\n"
                f"⚙️ **CPU:** {metrics['cpu_percent']}%\n"
                f"💾 **Disco:** {metrics['disk_free']} livres\n"
            )
            
            if metrics['temp'] != "N/A":
                summary += f"🌡️ **Temp:** {metrics['temp']}°C"
                
            return {
                "metrics": metrics,
                "summary": summary
            }
        except Exception as e:
            self.logger.error(f"Error monitoring hardware: {e}")
            return {"error": str(e)}

    def _get_metrics(self) -> Dict[str, Any]:
        """Blocking helper function to fetch metrics via psutil."""
        # RAM
        mem = psutil.virtual_memory()
        ram_total = f"{mem.total / (1024**3):.1f}GB"
        ram_used = f"{mem.used / (1024**2):.0f}MB"
        
        # Disk
        disk = psutil.disk_usage('/')
        disk_free = f"{disk.free / (1024**3):.1f}GB"
        
        # CPU (blocking 1s)
        cpu = psutil.cpu_percent(interval=1)
        
        # Temp (Cross-platform handling)
        temp = "N/A"
        if hasattr(psutil, "sensors_temperatures"):
            try:
                temps = psutil.sensors_temperatures()
                if temps:
                    # Generic logic: grab first available sensor
                    # For RPi, usually 'cpu_thermal'
                    for name, entries in temps.items():
                        if entries:
                            temp = entries[0].current
                            break
            except Exception:
                pass
                
        return {
            "ram_total": ram_total,
            "ram_used": ram_used,
            "ram_percent": mem.percent,
            "disk_free": disk_free,
            "cpu_percent": cpu,
            "temp": temp
        }
