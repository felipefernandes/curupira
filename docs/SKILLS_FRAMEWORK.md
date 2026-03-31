# Framework de Criação de Skills (Curupira MCP-Lite)

Este documento define o padrão oficial para a criação de novas _Skills_ (habilidades) no Curupira. Ele serve como guia definitivo tanto para desenvolvedores humanos quanto para Assistentes de Código Baseados em IA (Agentes).

O Curupira utiliza uma arquitetura apelidada de **MCP-Lite**, inspirada no Model Context Protocol, porém focada em **altíssima eficiência, baixo consumo de memória e latência mínima**, garantindo que o bot rode de forma lisa em hardwares limitados (ex: Raspberry Pi 3 com ZRAM).

---

## 1. O Manifesto Curupira para Skills

Antes de escrever qualquer linha de código, uma skill deve respeitar os seguintes princípios:

1. **Eficiência e Leveza**: O Curupira roda em dispositivos restritos. Evite carregar bibliotecas pesadas se uma requisição HTTP simples via `httpx` resolver o problema. Cuidado com dependências de ML pesadas.
2. **Separação de Preocupações (SoC)**: A skill **NUNCA** decide como o usuário vai ler os dados. A skill faz a lógica, recupera a informação e devolve um JSON puro e amigável. Quem constrói a frase final em linguagem natural é o cérebro (LLM) do Curupira.
3. **Descrições Cirúrgicas**: O LLM decide qual skill chamar lendo sua `description`. Descrições prolixas confundem os modelos menores e os deixam lentos. Seja curto, direto e orientado à ação ("Retorna a previsão do tempo para uma cidade" ao invés de "Esta habilidade serve para conectar na API X e pegar dados meteorológicos que o usuário pode querer saber sobre onde ele mora").
4. **Resiliência Passiva / Isolamento**: Se a API de terceiros cair, a skill deve retornar um erro amigável envelopado via método interno (`self.error()`). Nenhuma skill tem permissão para quebrar o Agent Loop ou causar _crash_ na main thread (utilize `asyncio.to_thread` para I/O bloqueante obrigatório).

---

## 2. Herança Obrigatória (`BaseSkill`)

Toda nova skill deve estar na pasta `skills/` e herdar obrigatoriamente de `skills.base.BaseSkill`.
A classe base fornece (a partir da v0.11) os métodos estruturais de padronização de retorno: `success()` e `error()`.

### Estrutura Base de uma Skill

```python
from typing import Any, Dict
from skills.base import BaseSkill
import logging
# Importe apenas o que for usar

class MinhaNovaSkill(BaseSkill):
    def __init__(self):
        self.logger = logging.getLogger("MinhaNovaSkill")
        # Inicialize clientes HTTP, URLs e states locais aqui.

    @property
    def name(self) -> str:
        # Padrão snake_case, nome da função pro LLM. Ex: "get_weather", "list_reminders"
        return "minha_nova_skill"

    @property
    def display_name(self) -> str:
        # Nome amigável com um Emoji para a interface (TUI, logs, comandos Telegram).
        return "🚀 Minha Nova Skill"

    @property
    def description(self) -> str:
        # CURTO. DIRETO. Diz ao Groq/Gemini exatamento QUANDO chamar essa function.
        return "Busca informações importantes na API XYZ e retorna o status atual."

    @property
    def parameters(self) -> Dict[str, Any]:
        # JSON Schema padrão do OpenAI Function Calling.
        # Defina APENAS os argumentos extritamente necessários para funcionar.
        return {
            "type": "object",
            "properties": {
                "param_obrigatorio": {
                    "type": "string",
                    "description": "O nome da cidade, por exemplo."
                },
                "param_opcional": {
                    "type": "integer",
                    "description": "Quantidade máxima de resultados."
                }
            },
            "required": ["param_obrigatorio"]
        }

    async def execute(self, context: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        Ponto de entrada nativo quando o AgentBrain aciona a ferramenta.
        
        Args:
            context: Dicionário contendo o contexto global do bot (user_id, job_queue, config, etc).
            **kwargs: Chaves correspondentes ao declaradas em `parameters`.
        """
        param_obrigatorio = kwargs.get("param_obrigatorio")
        param_opcional = kwargs.get("param_opcional", 5)

        try:
            # Sua Lógica de negócio aqui (requests, I/O, BD...)
            resultado = await algun_cliente_http(param_obrigatorio, param_opcional)
            
            # Se a busca não der erro, MAS os dados não existirem ou forem inconclusivos,
            # devolva self.success() explicando o motivo para o LLM gerar a resposta correta.
            if not resultado:
                return self.success({"info": "Nenhum resultado encontrado"}, message="Sem dados para os parâmetros fornecidos.")
            
            # Formatação leve dos resultados
            payload = {
                "chave1": resultado.valorA,
                "chave2": resultado.valorB
            }

            # Retorno padronizado de Sucesso. NUNCA retorne a classe da API inteira!
            return self.success(payload)

        except Exception as e:
            self.logger.error(f"Erro ao consultar API XYZ: {e}")
            # Em caso de falha de exceção, utilize self.error()!
            return self.error(f"Falha ao conectar com o provedor de dados: {str(e)}")
```

---

## 3. O Retorno "MCP-Lite"

O método `execute` deve SEMPRE resultar em um dicionário através das chamadas de encapsulamento da base:

### Retornando Sucesso
`return self.success(data={"temperatura": 25}, message="Tudo ocorreu bem" (opicional))`
Isso garantirá que o LLM receba algo previsível internamente:
`{"status": "success", "data": {"temperatura": 25}, "message": "..."}`

### Retornando Erro
`return self.error("Serviço fora do ar")`
O LLM receberá:
`{"status": "error", "error": "Serviço fora do ar"}`

O intuito deste envelopamento é reduzir o _"temperature noise"_ que faz as LLMs (Llama, Gemini) alucinarem chaves em suas passagens de raciocínio.

### Retornando HTML direto ao Telegram (bypass do LLM)
`return self.success_with_html(data=payload, html="<b>Card formatado</b>", summary="Resumo para o LLM")`

Use quando a skill gera um card visual que **não deve ser reescrito pelo LLM**. O campo `direct_html` é interceptado pelo AgentBrain e enviado direto ao usuário via callback — o LLM recebe apenas o `summary` como contexto e **não gera uma segunda resposta**.

> **Atenção: formatação e pipeline de normalização**
>
> - **`self.success()` / `self.error()`**: o texto gerado pelo LLM passa automaticamente pelo pipeline `TelegramFormatter.normalize()` antes de chegar ao usuário. A skill não precisa fazer nada.
> - **`self.success_with_html()`**: o `direct_html` é enviado diretamente, sem passar pelo pipeline. A skill é responsável por usar apenas as tags permitidas pelo Telegram: `<b>`, `<i>`, `<u>`, `<s>`, `<code>`, `<pre>`, `<a>`, `<tg-spoiler>`. Se precisar converter Markdown para HTML dentro da skill, use `from core.telegram_formatter import TelegramFormatter` e chame `TelegramFormatter.normalize(seu_texto)`.
>
> Skills que usam `direct_html` atualmente: `hardware.py`, `introspection.py`, `reminders.py`.

---

## 4. Skills Multi-Tool (Uma Skill, Múltiplas Ferramentas)

Quando uma skill oferece **múltiplas operações relacionadas**, NÃO crie classes separadas para cada operação. Ao invés disso, use uma **única Skill** com um parâmetro `action` (ou similar) para despachar entre diferentes ferramentas.

### Quando Usar Multi-Tool?
- ✅ Operações relacionadas ao mesmo domínio (ex: Google Calendar: listar, criar, deletar eventos)
- ✅ Compartilham autenticação ou cliente HTTP
- ✅ Operações complementares que formam um "conjunto de funcionalidades"

### Exemplo: Skill com Múltiplas Actions

```python
from typing import Any, Dict
from skills.base import BaseSkill
import httpx

class GoogleCalendarSkill(BaseSkill):
    def __init__(self):
        self.logger = logging.getLogger("GoogleCalendarSkill")
        self.client = httpx.AsyncClient()

    @property
    def name(self) -> str:
        return "google_calendar"

    @property
    def display_name(self) -> str:
        return "📅 Google Agenda"

    @property
    def description(self) -> str:
        return "Gerencia eventos no Google Calendar: listar, criar e cancelar eventos."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["list_events", "add_event", "cancel_event"],
                    "description": "Ação a executar: list_events, add_event ou cancel_event"
                },
                "time_range": {
                    "type": "string",
                    "description": "Período para listar (usado com list_events). Ex: 'today', 'tomorrow', 'week'"
                },
                "summary": {
                    "type": "string",
                    "description": "Título do evento (usado com add_event)"
                },
                "event_id": {
                    "type": "string",
                    "description": "ID do evento para cancelar (usado com cancel_event)"
                }
            },
            "required": ["action"]
        }

    async def execute(self, context: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Despacha para o handler apropriado baseado na action."""
        action = kwargs.get("action")

        if not action:
            return self.error("Ação não especificada")

        # Dispatch para métodos internos
        try:
            if action == "list_events":
                return await self._list_events(kwargs.get("time_range", "today"))
            elif action == "add_event":
                return await self._add_event(kwargs.get("summary"), kwargs.get("start_time"))
            elif action == "cancel_event":
                return await self._cancel_event(kwargs.get("event_id"))
            else:
                return self.error(f"Ação desconhecida: {action}")
        except Exception as e:
            self.logger.error(f"Erro em {action}: {e}")
            return self.error(f"Falha ao executar {action}: {str(e)}")

    # Métodos internos (prefixados com _)
    async def _list_events(self, time_range: str) -> Dict[str, Any]:
        """Lista eventos do calendário."""
        # Lógica aqui...
        events = []  # Fetch from API
        return self.success({"events": events, "range": time_range})

    async def _add_event(self, summary: str, start_time: str) -> Dict[str, Any]:
        """Cria novo evento."""
        # Lógica aqui...
        return self.success({"event_id": "123", "summary": summary})

    async def _cancel_event(self, event_id: str) -> Dict[str, Any]:
        """Cancela um evento existente."""
        # Lógica aqui...
        return self.success({"deleted": event_id})
```

### Padrão de Nomenclatura
- Métodos internos (helpers) devem ter prefixo `_` (ex: `_list_events`, `_get_client`, `_validate_token`)
- São privados e não acessíveis ao LLM diretamente
- Ajudam a organizar código complexo e reutilizar lógica

**Exemplo Real**: Veja `skills/system_control.py` que usa este padrão com 11+ actions diferentes.

---

## 5. Usando o Dicionário `context`

O parâmetro `context` fornecido ao `execute()` contém informações globais do bot. Principais chaves disponíveis:

```python
async def execute(self, context: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    # Acessando valores do context
    user_id = context.get("user_id")        # ID do usuário Telegram
    job_queue = context.get("job_queue")    # JobQueue para agendar tarefas
    config = context.get("config")          # Configurações globais do bot

    # Exemplo: Agendar tarefa recorrente
    if job_queue:
        job_queue.run_repeating(
            self._minha_tarefa_periodica,
            interval=3600,
            first=10,
            name=f"task_{user_id}"
        )

    # Exemplo: Acessar configuração
    api_key = config.get("SOME_API_KEY") if config else None
```

### Valores Comuns no Context
| Chave | Tipo | Descrição |
|-------|------|-----------|
| `user_id` | int | ID do usuário Telegram autorizado |
| `job_queue` | JobQueue | Fila de jobs do python-telegram-bot |
| `config` | dict | Variáveis de ambiente/configuração |
| `application` | Application | Instância do Application do telegram |

**⚠️ Importante**: Sempre use `.get()` ao acessar o context para evitar KeyError se alguma chave não existir.

---

## 6. Async Best Practices (I/O e Performance)

### Quando Usar `asyncio.to_thread()`
Use `asyncio.to_thread()` para **operações bloqueantes síncronas** que não têm versão async:

```python
import asyncio

async def execute(self, context: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    # ❌ ERRADO: Bloqueia o event loop
    result = subprocess.run(["ls", "-la"], capture_output=True, text=True)

    # ✅ CORRETO: Executa em thread separada
    result = await asyncio.to_thread(
        subprocess.run,
        ["ls", "-la"],
        capture_output=True,
        text=True,
        timeout=30
    )

    return self.success({"output": result.stdout})
```

### Timeouts Obrigatórios
Sempre defina timeouts para operações externas:

```python
import httpx
import asyncio

async def _fetch_data(self, url: str) -> dict:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.json()
    except httpx.TimeoutException:
        self.logger.error(f"Timeout ao acessar {url}")
        raise
    except httpx.HTTPError as e:
        self.logger.error(f"Erro HTTP: {e}")
        raise
```

### Limites de Memória
Para operações que podem gerar grandes volumes de dados:

```python
MAX_OUTPUT_SIZE = 10 * 1024  # 10KB

async def _read_large_file(self, path: str) -> str:
    """Lê arquivo com proteção contra OOM."""
    try:
        # Usa tail para limitar output
        result = await asyncio.to_thread(
            subprocess.run,
            ["tail", "-n", "100", path],
            capture_output=True,
            text=True,
            timeout=5
        )

        output = result.stdout
        if len(output) > self.MAX_OUTPUT_SIZE:
            output = output[:self.MAX_OUTPUT_SIZE] + "\n[... truncado ...]"

        return output
    except Exception as e:
        raise
```

---

## 7. Exemplos Reais do Projeto

Consulte estas skills existentes como referência:

| Skill | Arquivo | Padrão Demonstrado |
|-------|---------|-------------------|
| **Weather** | `skills/weather_manager.py` | Skill simples, single-tool, httpx client |
| **System Control** | `skills/system_control.py` | Multi-tool com enum actions, subprocess safety |
| **Reminders** | `skills/reminders.py` | Gerenciamento de estado com banco de dados |
| **Hardware** | `skills/hardware.py` | Monitoramento de sistema com timeouts |
| **Time** | `skills/time.py` | Skill ultra-leve (sem dependências externas) |

---

## 8. Checklist para Inserção da Skill no Bot
Após criar o arquivo `skills/sua_skill.py` e a classe respectiva:

1. **Instanciar o objeto**: Abra o arquivo `core/agent.py` e registre sua Skill no método `__init__` do `AgentBrain`.
   ```python
   from skills.sua_skill import MinhaNovaSkill
   ...
   self.register_skill(MinhaNovaSkill())
   ```
2. **Atualizar Roadmap**: Se a skill foi completada, lembre-se de marcar na seção correspondente do `ROADMAP.md` e testar no hardware local alvo.
3. **Documentar Dependências**: Se adicionar bibliotecas ao `requirements.txt`, comente o porquê e verifique impacto em memória.
4. **Testar em Hardware Alvo**: Execute no Raspberry Pi 3 (ou similar) para garantir que não cause OOM ou latência excessiva.

---

## 7. Suggestion Registry (Sugestões Proativas de Automação)

O `SUGGESTION_REGISTRY` em `skills/pattern_analyzer.py` é o mapa que conecta o nome de uma skill ao texto de sugestão que o Curupira exibe proativamente ao detectar uso frequente.

**Quando adicionar uma entrada?** Sempre que sua skill tiver um uso recorrente natural que poderia ser automatizado — ex: consultas de esportes → alertas de jogos, RSS → digest diário.

### Estrutura de uma entrada

```python
SUGGESTION_REGISTRY: Dict[str, Dict[str, str]] = {
    "nome_da_sua_skill": {           # tool_name exato (skill.name)
        "topic_field": "param_chave",  # campo de tool_args que identifica o tópico
        "template": (
            "Percebi que você usa {topic} com frequência. "
            "Quer que eu configure uma automação?"
        ),
        "generic_template": (          # fallback quando topic_field está ausente nos args
            "Percebi que você usa esta skill com frequência. "
            "Quer configurar uma automação?"
        ),
    },
}
```

### Regras

- **`topic_field`**: deve ser exatamente o nome do parâmetro que sua skill recebe via `kwargs`. Ex: `"team"` para `sports_manager`, `"city"` para `get_weather`.
- **`template`**: use `{topic}` como placeholder — o `PatternAnalyzer` vai substituir pelo valor mais frequente encontrado nos `tool_args` históricos.
- **`generic_template`**: obrigatório — usado quando o usuário chama a skill sem o parâmetro de tópico (ex: consultas gerais sem especificar time ou cidade).
- **Extensão zero-code**: adicionar sua skill ao registry é suficiente. O analisador a detectará automaticamente no próximo ciclo do heartbeat.

### Cooldown e anti-spam

O sistema persiste a data do último envio em `facts` com a chave `suggestion_sent:{tool_name}`. O intervalo padrão é 30 dias, configurável em `config.toml`:

```toml
[pattern_analysis]
suggestion_cooldown_days = 30
```

### Referência de implementação

- Registry: `skills/pattern_analyzer.py` → `SUGGESTION_REGISTRY`
- Agendamento: `bot.py` → job `pattern_check` (padrão idêntico ao `calendar_sync`)
- Config: `core/config.py` → `PATTERN_*` e `default.config.toml` → `[pattern_analysis]`
- Testes: `tests/test_pattern_analyzer.py`
