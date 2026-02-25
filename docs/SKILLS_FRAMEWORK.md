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

---

## 4. Checklist para Inserção da Skill no Bot
Após criar o arquivo `skills/sua_skill.py` e a classe respectiva:

1. **Instanciar o objeto**: Abra o arquivo `core/agent.py` e registre sua Skill no método `__init__` do `AgentBrain`.
   ```python
   from skills.sua_skill import MinhaNovaSkill
   ...
   self.register_skill(MinhaNovaSkill())
   ```
2. **Atualizar Roadmap**: Se a skill foi completada, lembre-se de marcar na seção correspondente do `ROADMAP.md` e testar no hardware local alvo.
