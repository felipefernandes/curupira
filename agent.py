import logging
import json
import os
import asyncio
from typing import Dict, Any, List, Optional
import config
from skills.base import BaseSkill

# NOTE: Providers are lazy-loaded to save memory on Raspberry Pi

class AgentBrain:
    """Agente responsável por gerenciar habilidades e integrações com APIs."""
    
    def __init__(self, provider: str, api_key: Optional[str] = None, model_name: str = "default"):
        """Inicializa o agente com provider e API key.
        
        Args:
            provider: Nome do provider (ex: "groq", "gemini").
            api_key: Chave de API ou None para buscar via ambiente.
            model_name: Nome do modelo a ser utilizado.
        """
        self.logger = logging.getLogger("AgentBrain")
        self.provider = provider.lower()
        self.model_name = model_name
        self.api_key = api_key or os.getenv(f"{provider.upper()}_API_KEY")
        
        if not self.api_key or not self.api_key.strip():
             raise ValueError(f"API key inválida ou ausente para {self.provider}")

        self.skills: Dict[str, BaseSkill] = {}
        self.client = None

    def register_skill(self, skill: BaseSkill):
        """Registers a skill to be used by the agent."""
        if skill.name in self.skills:
             self.logger.warning(f"Overwriting existing skill: {skill.name}")
        self.skills[skill.name] = skill
        self.logger.info(f"Registered skill: {skill.name}")

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
        
        # Lazy import types only when needed
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
            self.logger.info(f"Tool {tool_name} returned: {json.dumps(result, ensure_ascii=False)}")
            return json.dumps(result, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Error executing {tool_name}: {e}")
            return json.dumps({"error": str(e)})

    async def process(self, user_msg: str, context: Dict[str, Any], chat_history: str = "") -> str:
        """
        Main Agent Loop (Async).
        Handles multi-turn reasoning and tool execution.
        """
        if not user_msg:
            return "..."

        system_prompt = f"""
        Você é o Curupira, um assistente virtual (Persona do Folclore Brasileiro) leve e eficiente.
        Seu objetivo é ajudar o usuário: {context.get('user_name', 'Usuário')}.
        
        Instruções:
        1. Responda de forma natural e amigável.
        2. Use as ferramentas disponíveis quando necessário.
        3. Se usar uma ferramenta, use o resultado para formular a resposta final.
        4. NÃO invente informações se a ferramenta retornar erro.
        
        Contexto Atual:
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
                        max_tokens=2048 # Increased to prevent cut-off responses
                    )
                    
                    msg = response.choices[0].message
                    messages.append(msg)
                    
                    if msg.tool_calls:
                        for tool_call in msg.tool_calls:
                            fn_name = tool_call.function.name
                            fn_args = {}
                            
                            # FIX for Groq/Llama3 hallucination: sometimes it puts args in the name
                            # e.g. 'get_weather {"city": "São Paulo"}'
                            if " {" in fn_name:
                                try:
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
                    else:
                        return msg.content or ""
                        
                except Exception as e:
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
                    parts=[types.Part.from_text(f"{system_prompt}\n\nHistórico:\n{chat_history}\n\nMensagem Atual: {user_msg}")]
                )
            ]
            
            while current_turn < max_turns:
                 current_turn += 1
                 try:
                     # Use 'aio' for Async generation
                     response = await client.aio.models.generate_content(
                         model=self.model_name,
                         contents=contents,
                         config=types.GenerateContentConfig(tools=tools)
                     )
                     
                     if not response.candidates:
                         return "Erro: Sem resposta da IA."
                         
                     # Append Agent Response
                     contents.append(response.candidates[0].content)
                     
                     part = response.candidates[0].content.parts[0]
                     
                     if part.function_call:
                         fn_name = part.function_call.name
                         # Convert map to dict
                         fn_args = {k: v for k, v in part.function_call.args.items()}
                         
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
                         return part.text or ""

                 except Exception as e:
                     self.logger.error(f"Gemini API Error: {e}")
                     return "Desculpe, tive um erro ao processar com o Gemini."

        return "Desculpe, o Curupira está confuso e não conseguiu responder."
