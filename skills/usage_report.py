from typing import Any, Dict
from skills.base import BaseSkill
from skills.memory import MemoryManager

# Configurable/Approximate pricing per 1 million tokens (in USD)
PRICING_PER_1M = {
    "groq": {
        "prompt": 0.50, # approx Llama3 70b
        "completion": 0.80
    },
    "gemini": {
        "prompt": 0.075, # approx Gemini 1.5 Flash
        "completion": 0.30
    }
}

class UsageReportSkill(BaseSkill):
    """Skill to report token usage and estimated costs."""

    def __init__(self, memory_manager: MemoryManager):
        self._memory = memory_manager

    @property
    def name(self) -> str:
        return "get_usage_report"

    @property
    def display_name(self) -> str:
        return "📊 Relatório de Consumo"

    @property
    def description(self) -> str:
        return "Consulta o banco de dados e retorna um resumo acumulado do gasto de tokens (prompt e output) e custos estimados separados por provedor de IA."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {},
            "required": []
        }

    async def execute(self, context: Dict[str, Any], **kwargs) -> Any:
        try:
            summary = await self._memory.get_usage_summary()
            
            if not summary:
                return self.success({"message": "Nenhum consumo de tokens registrado no banco de dados até o momento."})
            
            report_lines = []
            total_cost = 0.0

            for provider, usage in summary.items():
                prompt_t = usage.get("prompt_tokens", 0)
                comp_t = usage.get("completion_tokens", 0)
                
                prices = PRICING_PER_1M.get(provider.lower(), {"prompt": 0.0, "completion": 0.0})
                
                cost_p = (prompt_t / 1_000_000) * prices["prompt"]
                cost_c = (comp_t / 1_000_000) * prices["completion"]
                cost_prov = cost_p + cost_c
                total_cost += cost_prov
                
                report_lines.append(f"🔌 Provedor: {provider.upper()}")
                report_lines.append(f"   - Tokens ENVIADOS (Prompt): {prompt_t:,}")
                report_lines.append(f"   - Tokens GERADOS (Output): {comp_t:,}")
                report_lines.append(f"   - Custo parcial USD: ${cost_prov:.5f}\n")
            
            report_lines.append(f"💲 Custo Total Estimado: ${total_cost:.5f} USD")
            
            final_report = "\n".join(report_lines)
            return self.success({"report": final_report}, message="Relatório de uso gerado com sucesso.")

        except Exception as e:
            return self.error(f"Erro ao consultar o banco de dados para consumo: {e}")
