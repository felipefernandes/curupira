"""
Pattern Analyzer — detecta padrões de uso de skills ao longo do tempo
e gera sugestões proativas de automação para o usuário.

Fluxo:
  job_queue (24h) → run_pattern_check() → PatternAnalyzer.get_pending_suggestions()
                  → bot.py envia via _send_proactive_message()

Extensão: adicionar nova entrada em SUGGESTION_REGISTRY para cobrir uma nova skill.
Nenhuma outra mudança de código é necessária.
"""

import logging
from collections import Counter
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger("PatternAnalyzer")

# ---------------------------------------------------------------------------
# Registro de sugestões por skill
# Chave: tool_name exato conforme armazenado em conversations.metadata
# ---------------------------------------------------------------------------
SUGGESTION_REGISTRY: Dict[str, Dict[str, str]] = {
    "sports_manager": {
        "topic_field": "team",
        "template": (
            "Percebi que você me pergunta bastante sobre {topic}. "
            "Quer que eu te avise automaticamente sobre os próximos jogos ou resultados?"
        ),
        "generic_template": (
            "Percebi que você usa bastante as consultas esportivas. "
            "Quer configurar notificações automáticas para times que você acompanha?"
        ),
    },
    "get_weather": {
        "topic_field": "city",
        "template": (
            "Vejo que você consulta o tempo em {topic} com frequência. "
            "Quer receber um resumo do tempo automaticamente toda manhã?"
        ),
        "generic_template": (
            "Vejo que você consulta o tempo com frequência. "
            "Quer receber um resumo automático pela manhã?"
        ),
    },
    "github_skill": {
        "topic_field": "repo",
        "template": (
            "Você consulta bastante o repositório {topic}. "
            "Quer que eu te avise sobre novos PRs ou issues automaticamente?"
        ),
        "generic_template": (
            "Você consulta o GitHub com frequência. "
            "Quer que eu te avise sobre atualizações dos seus repositórios?"
        ),
    },
    "rss": {
        "topic_field": "feed_identifier",
        "template": (
            "Você acompanha bastante o feed {topic}. "
            "Quer receber um resumo das últimas notícias desse feed automaticamente?"
        ),
        "generic_template": (
            "Você lê RSS com frequência. "
            "Quer receber um digest diário de notícias automaticamente?"
        ),
    },
}


class PatternAnalyzer:
    """Analisa histórico de conversas e gera sugestões de automação proativas."""

    def __init__(self, memory_manager, config):
        self._memory = memory_manager
        self._config = config

    async def get_pending_suggestions(self, user_id: int) -> List[Dict[str, Any]]:
        """Retorna lista de sugestões ainda não enviadas (ou fora do cooldown).

        Cada entrada: {"tool_name": str, "call_count": int, "topic": Optional[str], "message": str}
        """
        stats = await self._memory.get_tool_usage_stats(
            user_id, days=self._config.PATTERN_THRESHOLD_DAYS
        )
        suggestions = []

        for stat in stats:
            tool_name = stat["tool_name"]
            call_count = stat["call_count"]

            if call_count < self._config.PATTERN_THRESHOLD_COUNT:
                continue

            if tool_name not in SUGGESTION_REGISTRY:
                continue

            # Verifica cooldown via facts
            sent_at_str = await self._memory.get_fact_value(
                user_id, f"suggestion_sent:{tool_name}"
            )
            if sent_at_str:
                try:
                    sent_at = datetime.fromisoformat(sent_at_str)
                    elapsed_days = (datetime.now() - sent_at).days
                    if elapsed_days < self._config.PATTERN_SUGGESTION_COOLDOWN_DAYS:
                        logger.debug(
                            f"Sugestão para '{tool_name}' já enviada há {elapsed_days}d — skipping"
                        )
                        continue
                except ValueError:
                    pass  # ISO inválido → ignora e permite re-sugestão

            registry = SUGGESTION_REGISTRY[tool_name]
            topic = self._extract_top_topic(
                stat["args_samples"], registry["topic_field"]
            )
            message = self._build_message(tool_name, topic)
            if message is None:
                continue

            suggestions.append({
                "tool_name": tool_name,
                "call_count": call_count,
                "topic": topic,
                "message": message,
            })

        return suggestions

    def _extract_top_topic(
        self, args_samples: List[dict], topic_field: str
    ) -> Optional[str]:
        """Retorna o valor mais frequente de `topic_field` nos args amostrados."""
        values = [
            str(a[topic_field]).strip().lower()
            for a in args_samples
            if a.get(topic_field)
        ]
        if not values:
            return None
        return Counter(values).most_common(1)[0][0]

    def _build_message(self, tool_name: str, topic: Optional[str]) -> Optional[str]:
        """Monta o texto da sugestão a partir do registry."""
        registry = SUGGESTION_REGISTRY.get(tool_name)
        if registry is None:
            return None
        if topic:
            return registry["template"].format(topic=topic.title())
        return registry["generic_template"]


async def run_pattern_check(user_id: int, memory_manager, config) -> List[str]:
    """Entry point para o job_queue do bot.py.

    Sem side effects de I/O além de marcar sugestões enviadas em facts.
    Retorna lista de mensagens — bot.py é responsável pelo envio via Telegram.
    """
    analyzer = PatternAnalyzer(memory_manager, config)
    suggestions = await analyzer.get_pending_suggestions(user_id)

    messages = []
    for s in suggestions:
        await memory_manager.save_fact(
            user_id,
            f"suggestion_sent:{s['tool_name']}",
            datetime.now().isoformat(),
        )
        logger.info(
            f"Sugestão gerada para '{s['tool_name']}' "
            f"(count={s['call_count']}, topic={s['topic']})"
        )
        messages.append(s["message"])

    return messages
