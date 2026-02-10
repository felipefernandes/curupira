from datetime import datetime
from typing import Dict, Any
from .base import BaseSkill

class GetTimeSkill(BaseSkill):
    @property
    def name(self) -> str:
        return "get_current_time"

    @property
    def description(self) -> str:
        return "Retorna a data e hora atual do sistema. Use quando o usuário perguntar 'que horas são?' ou 'que dia é hoje?'."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {"type": "object", "properties": {}}

    async def execute(self, context: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        now = datetime.now()
        # Formats: 
        # - HH:MM
        # - Day of week
        # - Full date
        weekday_map = {
            0: "Segunda-feira", 1: "Terça-feira", 2: "Quarta-feira", 
            3: "Quinta-feira", 4: "Sexta-feira", 5: "Sábado", 6: "Domingo"
        }
        
        weekday = weekday_map.get(now.weekday(), "")
        time_str = now.strftime("%H:%M")
        date_str = now.strftime("%d/%m/%Y")
        
        info = f"São {time_str} de {weekday}, dia {date_str}."
        
        return {
            "time": time_str,
            "date": date_str,
            "weekday": weekday,
            "info": info
        }
