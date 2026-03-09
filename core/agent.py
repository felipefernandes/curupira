import logging
import json
import os
import re
import uuid
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from . import config
import datetime
from datetime import datetime
from skills.base import BaseSkill
from .mcp_client import MCPClient
from skills.mcp_skill import MCPSkill
from skills.introspection import IntrospectionSkill
from skills.rss import RssReadSkill, RssListSkill
from skills.google_calendar import GoogleCalendarSkill
import random

# NOTE: Providers are lazy-loaded to save memory

class AgentBrain:
    """Agente responsável por gerenciar habilidades e integrações com APIs."""

    # Compiled patterns for Llama-3 malformed tool call recovery
    _RE_FUNC_PARENS = re.compile(r'<function=(\w+)\((.*?)\)></function>', re.DOTALL)  # <function=name(args)></function>
    _RE_FUNC_ANGLES = re.compile(r'<function=([a-zA-Z0-9_]+)>(\{.*?\})</function>', re.DOTALL)      # <function=name>{"args":...}</function>
    _RE_FUNC_COLON  = re.compile(r'<function=(\w+)":\s*(.*?)</function>', re.DOTALL)  # <function=name":args</function>

    # Compiled patterns to strip CoT reasoning blocks (Qwen3, DeepSeek-R1, etc.)
    _RE_THINK_BLOCK = re.compile(r'<think>(?:.*?</think>|.*$)', re.DOTALL)
    
    def __init__(self, provider: str, model_name: str = "default"):
        """Inicializa o agente com provider. API Key é obtida de config.
        
        Args:
            provider: Nome do provider (ex: "groq", "gemini").
            model_name: Nome do modelo a ser utilizado.
        """
        self.logger = logging.getLogger("AgentBrain")
        self.provider = provider.lower()
        self.model_name = model_name
        
        # Security: Fetch API Key from config based on provider, avoids passing it around
        if self.provider == 'gemini':
            self.api_key = config.GEMINI_API_KEY
        elif self.provider == 'groq':
            self.api_key = config.GROQ_API_KEY
        else:
            self.api_key = os.getenv(f"{provider.upper()}_API_KEY")
        
        if not self.api_key or not self.api_key.strip():
             raise ValueError(f"API key não configurada para {self.provider} no CONFIG.")

        self.skills: Dict[str, BaseSkill] = {}
        self.mcp_clients: List[MCPClient] = []
        self.client = None

        # Proactive greeting deduplication: only one greeting per calendar day.
        # Stores the last date (datetime.date) a greeting was sent, or None.
        self._last_greeting_date: Optional[datetime.date] = None

        # Built-in skills (always available)
        self.register_skill(IntrospectionSkill(self))
        self.register_skill(RssReadSkill())
        self.register_skill(RssListSkill())
        self.register_skill(GoogleCalendarSkill())

    @staticmethod
    def _sanitize_text(text: str) -> str:
        """Sanitiza texto da LLM, prevenindo injeção de caracteres maliciosos de controle (Performance / Clean code)."""
        if not text:
            return ""
        return "".join(c for c in text if c.isprintable() or c in "\n\r\t")

    def register_skill(self, skill: BaseSkill):
        """Registers a skill to be used by the agent."""
        if skill.name in self.skills:
             self.logger.warning(f"Overwriting existing skill: {skill.name}")
        self.skills[skill.name] = skill
        self.logger.info(f"Registered skill: {skill.name}")

    async def start_mcp_clients(self):
        """Starts configured MCP clients and registers their tools."""
        if not config.MCP_SERVERS:
            self.logger.info("No MCP servers configured.")
            return

        for server_name, server_config in config.MCP_SERVERS.items():
            command = server_config.get("command")
            args = server_config.get("args", [])
            env = server_config.get("env")
            
            if not command:
                self.logger.warning(f"Skipping invalid MCP server config: {server_name}")
                continue
                
            try:
                # Use current python executable if command is 'python' to ensure venv usage
                import sys
                if command == "python":
                    command = sys.executable
                
                client = MCPClient(command, args, env)
                await client.connect()

                self.mcp_clients.append(client)
                
                tools = await client.list_tools()
                for tool_def in tools:
                    skill = MCPSkill(client, tool_def)
                    self.register_skill(skill)
                    
                self.logger.info(f"Connected to MCP Server '{server_name}' and registered {len(tools)} tools.")
                
            except Exception as e:
                self.logger.error(f"Failed to start MCP Server '{server_name}': {e}")

    async def shutdown(self):
        """Closes all MCP clients and resources."""
        for client in self.mcp_clients:
            await client.close()
        self.mcp_clients.clear()

    def _get_groq_client(self):
        """Lazy load and return AsyncGroq client."""
        if self.client:
            return self.client
            
        try:
            from groq import AsyncGroq
            self.client = AsyncGroq(api_key=self.api_key)
            return self.client
        except ImportError:
            self.logger.error("Groq library not installed.")
            return None

    def _get_gemini_client(self):
        """Lazy load and return Google GenAI client."""
        if self.client:
            return self.client
            
        try:
            from google import genai
            self.client = genai.Client(api_key=self.api_key)
            return self.client
        except ImportError:
            self.logger.error("Google GenAI library not installed.")
            return None

    def _get_groq_tools(self) -> List[Dict[str, Any]]:
        """Converts registered skills to Groq/OpenAI tool format."""
        tools = []
        for skill in self.skills.values():
            tools.append({
                "type": "function",
                "function": {
                    "name": skill.name,
                    "description": skill.description,
                    "parameters": skill.parameters
                }
            })
        return tools

    def _get_gemini_tools(self) -> Optional[List[Any]]:
        """Converts registered skills to Gemini tool format."""
        if not self.skills:
            return None
        
        from google.genai import types
        
        declarations = []
        for skill in self.skills.values():
             declarations.append(
                 types.FunctionDeclaration(
                     name=skill.name,
                     description=skill.description,
                     parameters=skill.parameters
                 )
             )
        return [types.Tool(function_declarations=declarations)]

    async def _execute_tool_call(self, tool_name: str, tool_args: Optional[Dict[str, Any]], context: Dict[str, Any]) -> str:
        """
        Executes a tool (skill) by name with provided arguments.
        Catches exceptions to prevent agent crash.
        """
        self.logger.info(f"Invoking tool: {tool_name} with {tool_args}")
        
        skill = self.skills.get(tool_name)
        if not skill:
            return json.dumps({"error": f"Tool {tool_name} not found"})
            
        try:
            # SAFETY: Ensure tool_args is a dictionary
            safe_args = tool_args if isinstance(tool_args, dict) else {}
            
            result = await skill.execute(context, **safe_args)
            result_str = json.dumps(result, ensure_ascii=False)
            
            # Log truncated result for debugging (avoid huge logs)
            log_preview = (result_str[:200] + '...') if len(result_str) > 200 else result_str
            self.logger.info(f"Tool {tool_name} returned: {log_preview}")
            
            return result_str
        except Exception as e:
            self.logger.error(f"Error executing {tool_name}: {e}")
            return json.dumps({"error": str(e)})

    @staticmethod
    def _parse_failed_generation(failed_gen: str) -> Optional[Tuple[str, dict]]:
        """Parse a Groq failed_generation string into (fn_name, fn_args).

        Returns None if the string does not contain a recognisable tool call.
        """
        if not failed_gen or '<function=' not in failed_gen:
            return None

        # <function=name(args)></function>
        match = AgentBrain._RE_FUNC_PARENS.search(failed_gen)
        if not match:
            # <function=name>args</function>
            match = AgentBrain._RE_FUNC_ANGLES.search(failed_gen)
        if not match:
            # <function=name":args</function>  (Llama colon-quote format)
            match = AgentBrain._RE_FUNC_COLON.search(failed_gen)
        if not match:
            return None

        fn_name = match.group(1)
        try:
            fn_args = json.loads(match.group(2))
        except json.JSONDecodeError:
            fn_args = {}

        return fn_name, fn_args

    def _is_retryable_error(self, e: Exception) -> bool:
        """Determines if an exception is a retryable rate limit error."""
        try:
            from google.api_core import exceptions as google_exceptions
            if isinstance(e, google_exceptions.ResourceExhausted):
                return True
        except ImportError:
            pass

        err_str = str(e).lower()
        # More specific checks to avoid false positives
        return "429" in err_str or "resource_exhausted" in err_str or "quota exceeded" in err_str

    async def _generate_with_retry(self, client, model: str, contents: Any, config: Any, retries: Optional[int] = None, initial_delay: Optional[float] = None):
        """
        Generates content with retry logic for 429 Resource Exhausted errors.
        Exponential backoff: 2s, 4s, 8s...
        """
        # Resolve defaults at runtime
        # We access the module-level config imported as 'core_config' to avoid shadowing
        from . import config as core_config
        
        retries = retries if retries is not None else core_config.RETRY_ATTEMPTS
        initial_delay = initial_delay if initial_delay is not None else core_config.RETRY_INITIAL_DELAY

        # Segurança: Validação de Entrada
        if not contents:
            raise ValueError("Conteúdo vazio não permitido para geração.")
        if not model or not isinstance(model, str) or not model.strip():
             raise ValueError("Invalid model name provided.")
        
        allowed_config_types = (dict,)
        try:
            from google.genai import types
            allowed_config_types = (dict, types.GenerateContentConfig)
        except ImportError:
            pass

        if config is not None and not isinstance(config, allowed_config_types):
                 raise ValueError(f"Invalid config type: {type(config)}. Expected dict or GenerateContentConfig.") 
        
        delay = initial_delay
        
        # import random (Moved to top)

        for attempt in range(retries + 1):
            try:
                # Async generation
                response = await client.aio.models.generate_content(
                    model=model,
                    contents=contents,
                    config=config
                )
                return response
            
            except Exception as e:
                if self._is_retryable_error(e):
                    if attempt < retries:
                        # Add Jitter: Random value between 0 and 1 second
                        jitter = random.random()
                        sleep_time = delay + jitter
                        
                        self.logger.warning(f"Gemini 429 Rate Limit hit. Retrying in {sleep_time:.2f}s... (Attempt {attempt+1}/{retries})")
                        await asyncio.sleep(sleep_time)
                        delay = min(delay * 2, 60.0) # Cap at 60s
                        continue # Retry loop
                    else:
                        self.logger.error("Gemini Rate Limit exhausted after retries.")
                        raise e # Re-raise the exact exception
                
                # If it is NOT a rate limit error, we re-raise immediately
                raise e
        



    async def reflect(self, context: Dict[str, Any]) -> Optional[str]:
        """
        Executes a reflection cycle to check if the agent should proactively speak.
        Returns the message string or None if SILENCE.
        """
        if not config.REFLECTION_ENABLED:
            return None

        # Setup Client
        client = None
        use_groq = False

        if config.AI_PROVIDER == 'groq':
             if not config.GROQ_API_KEY:
                 self.logger.warning("AI_PROVIDER is 'groq' but GROQ_API_KEY is missing via reflect.")
                 return None
             # Use explicit key for reflection client
             try:
                 from groq import AsyncGroq
                 client = AsyncGroq(api_key=config.GROQ_API_KEY)
             except ImportError:
                 self.logger.error("Groq library not installed.")
                 return None
             use_groq = True
             model = config.GROQ_MODEL
        elif config.AI_PROVIDER == 'gemini':
             if not config.GEMINI_API_KEY:
                 self.logger.warning("AI_PROVIDER is 'gemini' but GEMINI_API_KEY is missing via reflect.")
                 return None
             # Use explicit key for reflection client
             try:
                 from google import genai
                 client = genai.Client(api_key=config.GEMINI_API_KEY)
             except ImportError:
                 self.logger.error("Google GenAI library not installed.")
                 return None
             model = config.GEMINI_MODEL
        else:
             self.logger.warning(f"Unknown AI_PROVIDER for reflection: {config.AI_PROVIDER}")
             return None
        
        if not model:
            self.logger.error("Model name is empty.")
            return None
        
        if not client:
            return None

        # Resolve greeting window from config
        greeting_start = config.REFLECTION_GREETING_HOUR_START
        greeting_end   = config.REFLECTION_GREETING_HOUR_END
        
        try:
            current_hour = int(context.get("hour", -1))
        except (ValueError, TypeError):
            current_hour = -1

        greeting_allowed = greeting_start <= current_hour < greeting_end

        if 5 <= current_hour < 12:
            period_greeting = "Bom dia"
        elif 12 <= current_hour < 18:
            period_greeting = "Boa tarde"
        else:
            period_greeting = "Boa noite"

        # Construct Prompt
        # /no_think instructs Qwen3 to skip chain-of-thought output
        greeting_rule = (
            f"3. If the current hour is between {greeting_start}:00 and {greeting_end}:00 "
            f"AND you have NOT greeted the user yet today -> Greet the user with a natural and friendly '{period_greeting}' (e.g., 'Olá! {period_greeting}', '{period_greeting}!'). Use the user's name if known."
            if greeting_allowed
            else
            "3. Greetings (Bom dia, Boa tarde, Boa noite, etc.) are FORBIDDEN right now — "
            f"they are only allowed between {greeting_start}:00 and {greeting_end}:00."
        )
        system_prompt = (
            "/no_think\n"
            "You are the Guardian of the System (Curupira). "
            "Analyze the provided context (Time, Hardware, State). "
            "Decide if you MUST say something to the user. "
            "CRITERIA: "
            "1. If everything is normal -> Output 'SILENCE' (strict). "
            "2. If hardware is critical (CPU Temp > 80C or RAM > 90%) -> Warn the user immediately. "
            f"{greeting_rule} "
            "OUTPUT FORMAT: strictly return the message text OR the single word 'SILENCE'. "
            "No JSON. No markdown. No 'Reflexão:' prefix. One greeting per day maximum."
        )

        user_content = f"Context: {json.dumps(context, indent=2, ensure_ascii=False)}"

        try:
            if use_groq:
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ]
                response = await client.chat.completions.create(
                    model=model,
                    messages=messages,
                    max_tokens=400,  # must fit complete <think>...</think> block
                    temperature=config.GROQ_TEMPERATURE_REFLECTION
                )
                result = response.choices[0].message.content.strip()
            else:
                from google.genai import types
                response = await client.aio.models.generate_content(
                    model=model,
                    contents=[types.Content(parts=[types.Part(text=f"{system_prompt}\n\n{user_content}")])],
                    config=types.GenerateContentConfig(temperature=0.0, max_output_tokens=400)
                )
                if response.candidates:
                    result = response.candidates[0].content.parts[0].text.strip()
                else:
                    result = "SILENCE"

            # Filter Logic - Robust Check
            clean_result = result.strip().upper()
            
            # Remove quotes and trailing punctuation
            clean_result = clean_result.replace('"', '').replace("'", "").rstrip('.')
            
            # Expanded Silence Triggers - catches common hallucinations
            silence_triggers = ["SILENCE", "SIL", "SILENCIO", "NOTHING", "NO", "NONE"]
            
            if clean_result in silence_triggers or len(clean_result) < 2:
                self.logger.info(f"Reflection: SILENCE ({clean_result})")
                return None

            # Strip <think>...</think> blocks produced by Qwen3, DeepSeek-R1 and similar CoT models.
            # Pass 1: remove complete pairs (most common case with max_tokens=400)
            # Pass 2: remove truncated open tags (fallback if model is still cut off)
            if not isinstance(result, str):
                self.logger.warning(f"Reflection: unexpected result type {type(result).__name__}, coercing to str")
                result = str(result)

            result = self._RE_THINK_BLOCK.sub('', result)  # strip <think>...</think> blocks from CoT models
            result = result.strip()

            # Re-check for silence after stripping CoT — model may output <think>...</think>SILENCE
            if not result:
                self.logger.info("Reflection: SILENCE (empty after <think> strip)")
                return None

            clean_after = result.upper().replace('"', '').replace("'", "").rstrip('.')
            if clean_after in silence_triggers or len(clean_after) < 2:
                self.logger.info(f"Reflection: SILENCE (post-strip: {clean_after})")
                return None

            # -------------------------------------------------------------------
            # Greeting deduplication: if the message contains a greeting,
            # only allow it once per calendar day (regardless of LLM decision).
            # -------------------------------------------------------------------
            # Use regex for performance instead of linear list search
            if not hasattr(self, '_greeting_regex'):
                self._greeting_regex = re.compile(
                    r'\b(bom dia|boa tarde|boa noite|good morning|good afternoon|good evening|good night|bonjour|buenos días|buenas tardes|buenas noches)\b', 
                    re.IGNORECASE
                )
            
            is_greeting = bool(self._greeting_regex.search(result))

            if is_greeting:
                today = datetime.now().date()
                if self._last_greeting_date == today:
                    self.logger.info(
                        f"Reflection: SILENCE (greeting already sent today: {today})"
                    )
                    return None
                # Record that we sent a greeting today
                self._last_greeting_date = today
                self.logger.info(f"Reflection: greeting approved for {today}, updating _last_greeting_date.")

            return result
            
        except Exception as e:
            self.logger.error(f"Reflection Error: {e}")
            return None

    async def process(self, user_msg: str, context: Dict[str, Any], chat_history: str = "", on_intermediate_reply=None) -> str:
        """
        Main Agent Loop (Async).
        Handles multi-turn reasoning and tool execution.
        """
        # Improve robustness: Ensure context is a dictionary
        if not isinstance(context, dict):
            self.logger.warning(f"Invalid context received: {type(context)}. Defaulting to empty dict.")
            context = {}

        if not user_msg:
            return "..."


        # Dynamic Tool Injection
        available_tools_desc = []
        for skill in self.skills.values():
            available_tools_desc.append(f"- {skill.name}: {skill.description}")

        tools_context = "\n".join(available_tools_desc) if available_tools_desc else "Nenhuma ferramenta disponível no momento."

        user_name = context.get('user_name', 'Usuário')
        current_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Build bot full name — "Curupira" + optional surname set during onboarding
        assistant_surname = context.get('assistant_surname', '').strip()
        bot_full_name = f"Curupira {assistant_surname}".strip() if assistant_surname else "Curupira"

        # Inject persistent user facts (from issue #88)
        user_facts = context.get('user_facts', '')
        facts_section = (
            f"\n{user_facts}"
            if user_facts else "Nenhum fato registrado ainda."
        )

        system_prompt = f"""## IDENTIDADE
Você é o {bot_full_name}, assistente pessoal de {user_name}.
Seu nome completo é "{bot_full_name}". Nunca diga que seu nome é o nome do usuário.
Horário atual: {current_time_str}
Personalidade: direto, leve, ligeiramente místico. Sem ser prolixo. Responda sempre em português brasileiro.

## AMBIENTE DE HARDWARE
Você opera em um Raspberry Pi com recursos limitados de CPU e RAM.
Prefira respostas curtas e objetivas. Nunca mencione "aguardar processamento".

## FATOS PERSISTENTES DO USUÁRIO
Os dados abaixo descrevem o USUÁRIO (não você). Use-os proativamente — nunca peça informações que já estão aqui:
{facts_section}

## FERRAMENTAS DISPONÍVEIS
{tools_context}

## REGRAS DE COMPORTAMENTO
1. **Ferramentas**: Use-as proativamente. Nunca pergunte se deve usar uma ferramenta disponível.
2. **RSS/Notícias**: Identifique o feed mais relevante pelo contexto e busque direto, sem listar opções nem pedir confirmação. Apresente artigos com título e link exatos — nunca resuma genericamente.
3. **Clima**: Se a cidade do usuário estiver nos Fatos Persistentes, use-a diretamente.
4. **Rigidez factual**: Baseie respostas APENAS no retorno das ferramentas. Nunca invente dados não retornados por uma skill.
5. **Diálogo natural**: Continue conversas de forma orgânica, inclusive após mensagens proativas suas.
6. **Memória de longo prazo**: Ao aprender dado relevante (cidade, rotina, preferência), chame `save_user_fact` imediatamente.
7. **Protocolo de ferramentas**: Use JSON válido. O campo `name` deve ser EXATAMENTE o identificador da ferramenta — nunca inclua argumentos no `name`.
8. **Formatação de Texto**: A interface do usuário não suporta Markdown (como `**` ou `*`). Em vez disso, você DEVE DEVE DEVE formatar o texto obrigatoriamente usando tags HTML simples (apenas <b>, <i>, <code>, <pre>). Nunca use asteriscos para listas, use caracteres como • ou -.

## HISTÓRICO RECENTE
{chat_history}
"""


        max_turns = 5
        current_turn = 0
        
        if self.provider == 'groq':
            client = self._get_groq_client()
            if not client: return "Erro: Cliente Groq não inicializado."

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Histórico:\n{chat_history}\n\nMensagem Atual: {user_msg}"}
            ]
            
            while current_turn < max_turns:
                current_turn += 1
                try:
                    tools = self._get_groq_tools()
                    # Async call
                    response = await client.chat.completions.create(
                        model=self.model_name,
                        messages=messages,
                        tools=tools if tools else None,
                        tool_choice="auto" if tools else None,
                        max_tokens=2048,
                        temperature=config.GROQ_TEMPERATURE
                    )
                    
                    msg = response.choices[0].message
                    messages.append(msg)
                    
                    if hasattr(response, 'usage') and response.usage:
                        prompt_tokens = getattr(response.usage, 'prompt_tokens', 0)
                        completion_tokens = getattr(response.usage, 'completion_tokens', 0)
                        mem_mgr = context.get('memory_manager')
                        if mem_mgr:
                            try:
                                await mem_mgr.log_token_usage('groq', self.model_name, prompt_tokens, completion_tokens)
                            except Exception as e:
                                self.logger.warning(f"Erro ao salvar token usage: {e}")
                    
                    if msg.tool_calls:
                        # Check and dispatch preamble text for multi-turn conversational feel
                        if on_intermediate_reply is not None and msg.content:
                            clean_content = self._sanitize_text(msg.content.strip())
                            if clean_content:
                                try:
                                    await on_intermediate_reply(clean_content)
                                except Exception as cb_err:
                                    self.logger.warning(f"Error in on_intermediate_reply (Groq): {cb_err}")

                        for tool_call in msg.tool_calls:
                            fn_name = tool_call.function.name
                            fn_args = {}
                            
                            # FIX for Groq/Llama3 hallucination: sometimes it puts args in the name
                            # e.g. 'get_weather {"city": "São Paulo"}'
                            # FIX for Groq/Llama3 hallucination: sometimes it puts args in the name
                            # e.g. 'get_weather {"city": "São Paulo"}' or 'add_reminder={"..."}'
                            if " {" in fn_name or "={" in fn_name:
                                try:
                                    if "={" in fn_name:
                                        parts = fn_name.split("={", 1)
                                    else:
                                        parts = fn_name.split(" {", 1)
                                        
                                    fn_name = parts[0]
                                    fn_args = json.loads("{" + parts[1])
                                    self.logger.warning(f"Fixed malformed tool call. Name: {fn_name}, Args: {fn_args}")
                                except Exception as e:
                                    self.logger.error(f"Failed to fix malformed tool name: {fn_name} - {e}")

                            try:
                                if not fn_args: # Only parse if not already extracted from name
                                    fn_args = json.loads(tool_call.function.arguments)
                            except json.JSONDecodeError:
                                pass
                                
                            result_str = await self._execute_tool_call(fn_name, fn_args, context)
                            
                            messages.append({
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "name": fn_name,
                                "content": result_str
                            })
                        continue # Re-prompt Agent with tool outputs

                    # Fallback: Check for Llama-3 style <function> XML in content if no tool_calls
                    content = msg.content or ""
                    if "<function=" in content:
                        try:
                            # Regex to capture name and args: <function=name>(args)</function>
                            match = self._RE_FUNC_ANGLES.search(content)
                            if match:
                                fn_name = match.group(1)
                                args_str = match.group(2)
                                self.logger.warning(f"Detected Llama-3 XML tool call in content: {fn_name}")
                                
                                preamble = content[:match.start()].strip()
                                if preamble and on_intermediate_reply:
                                    try:
                                        await on_intermediate_reply(preamble)
                                    except Exception as cb_err:
                                        self.logger.error(f"Error in on_intermediate_reply (Llama XML): {cb_err}")
                                
                                try:
                                    # Try to parse strict JSON first
                                    fn_args = json.loads(args_str)
                                except json.JSONDecodeError:
                                    # Sometimes args are not quoted keys? Just pass empty for safety if complex
                                    self.logger.warning(f"Could not parse args from XML: {args_str}")
                                    fn_args = {}
                                
                                result_str = await self._execute_tool_call(fn_name, fn_args, context)
                                
                                # CRITICAL FIX: Rewrite history to look like a VALID tool call
                                # Groq API rejects <function> tags in content on next turn
                                fake_tool_id = f"call_{uuid.uuid4().hex[:8]}"
                                
                                # Create a synthetic assistant message with proper tool_calls
                                synthetic_msg = {
                                    "role": "assistant",
                                    "content": None, # Hide the ugly XML from history
                                    "tool_calls": [{
                                        "id": fake_tool_id,
                                        "type": "function",
                                        "function": {
                                            "name": fn_name,
                                            "arguments": json.dumps(fn_args)
                                        }
                                    }]
                                }
                                messages.append(synthetic_msg)
                                
                                messages.append({
                                    "role": "tool",
                                    "tool_call_id": fake_tool_id,
                                    "name": fn_name,
                                    "content": result_str
                                })
                                continue # Loop back to get final response
                        except Exception as e:
                            self.logger.error(f"Error parsing XML tool call: {e}")
                    
                    return content
                        
                except Exception as e:
                    # Recover from Groq 400 "tool_use_failed" errors
                    # Llama sometimes generates <function=name(args)></function>
                    # which Groq rejects before returning the response.
                    err_body = getattr(e, 'body', None) or {}
                    failed_gen = err_body.get('error', {}).get('failed_generation', '') if isinstance(err_body, dict) else ''
                    parsed = self._parse_failed_generation(failed_gen)
                    if parsed:
                        fn_name, fn_args = parsed
                        self.logger.warning(f"Recovered tool call from failed_generation: {fn_name}")

                        result_str = await self._execute_tool_call(fn_name, fn_args, context)

                        fake_tool_id = f"call_{uuid.uuid4().hex[:8]}"
                        messages.append({
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [{
                                "id": fake_tool_id,
                                "type": "function",
                                "function": {
                                    "name": fn_name,
                                    "arguments": json.dumps(fn_args)
                                }
                            }]
                        })
                        messages.append({
                            "role": "tool",
                            "tool_call_id": fake_tool_id,
                            "name": fn_name,
                            "content": result_str
                        })
                        continue  # Re-prompt with tool result

                    self.logger.error(f"Groq API Error: {e}")
                    return "Desculpe, tive um problema de conexão com meu cérebro digital."

        elif self.provider == 'gemini':
            client = self._get_gemini_client()
            if not client: return "Erro: Cliente Gemini não inicializado."
            
            # Lazy import types
            from google.genai import types
            
            tools = self._get_gemini_tools()
            
            # Init conversation (Simplified Checkpoint for now)
            # In a real scenario, we'd map 'chat_history' to strict Content objects.
            # Here keeping it "Lightweight" by dumping text into the first prompt.
            contents = [
                types.Content(
                    role="user",
                    parts=[types.Part(text=f"{system_prompt}\n\nHistórico:\n{chat_history}\n\nMensagem Atual: {user_msg}")]
                )
            ]
            
            while current_turn < max_turns:
                 current_turn += 1
                 try:
                     # Use 'aio' for Async generation with retry
                     response = await self._generate_with_retry(
                         client=client,
                         model=self.model_name,
                         contents=contents,
                         config=types.GenerateContentConfig(tools=tools)
                     )
                     
                     if not response.candidates:
                         return "Erro: Sem resposta da IA."
                         
                     # Append Agent Response
                     contents.append(response.candidates[0].content)
                     
                     if hasattr(response, 'usage_metadata') and response.usage_metadata:
                         prompt_tokens = getattr(response.usage_metadata, 'prompt_token_count', 0)
                         completion_tokens = getattr(response.usage_metadata, 'candidates_token_count', 0)
                         mem_mgr = context.get('memory_manager')
                         if mem_mgr:
                             try:
                                 await mem_mgr.log_token_usage('gemini', self.model_name, prompt_tokens, completion_tokens)
                             except Exception as e:
                                 self.logger.warning(f"Erro ao salvar token usage: {e}")
                     
                     text_parts = []
                     function_calls = []
                     text_content = ""
                     
                     for part in response.candidates[0].content.parts:
                         if part.function_call:
                             function_calls.append(part)
                         elif part.text:
                             text_content += part.text
                    
                     # If tools are called, send any preamble text to the user immediately
                     if function_calls and text_content.strip() and on_intermediate_reply is not None:
                         clean_text = self._RE_THINK_BLOCK.sub('', text_content)
                         clean_text = self._sanitize_text(clean_text.strip())
                         if clean_text:
                             try:
                                 await on_intermediate_reply(clean_text)
                             except Exception as cb_err:
                                 self.logger.warning(f"Error in on_intermediate_reply (Gemini): {cb_err}")

                     # Prioritize first function call found
                     part_with_fn = function_calls[0] if function_calls else None

                     if part_with_fn:
                         fn_name = part_with_fn.function_call.name
                         # Convert map to dict
                         fn_args = {k: v for k, v in part_with_fn.function_call.args.items()}
                         
                         result_str = await self._execute_tool_call(fn_name, fn_args, context)
                         
                         # Parse result back to dict for Gemini SDK if expected, or just return text?
                         # Gemini expects a function_response part
                         try:
                             result_dict = json.loads(result_str)
                         except:
                             result_dict = {"output": result_str}

                         contents.append(
                             types.Content(
                                 role="tool",
                                 parts=[types.Part.from_function_response(
                                     name=fn_name,
                                     response=result_dict
                                 )]
                             )
                         )
                         continue
                     else:
                         return text_content or ""

                 except Exception as e:
                     # Try to catch specific Google API errors if available
                     error_type = type(e).__name__
                     self.logger.error(f"Gemini API Error ({error_type}): {e}")
                     
                     # Check for rate limits specifically in string or type
                     if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e) or "ResourceExhausted" in error_type:
                          return "Desculpe, estou temporariamente sobrecarregado. Tente novamente em alguns instantes."
                     
                     return "Desculpe, tive um erro ao processar com o Gemini."

        return "Desculpe, o Curupira está confuso e não conseguiu responder."
