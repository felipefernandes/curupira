
import logging
import json
import asyncio
from typing import Dict, Any, List, Optional
import config
from skills.base import BaseSkill

# Provider Imports
try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None

try:
    from groq import Groq
except ImportError:
    Groq = None

class AgentBrain:
    def __init__(self, provider: str, api_key: str, model_name: str):
        self.logger = logging.getLogger("AgentBrain")
        self.provider = provider
        self.model_name = model_name
        self.skills: Dict[str, BaseSkill] = {}
        self.client = None

        if provider == 'gemini':
            if not genai:
                self.logger.error("Google GenAI library not installed.")
            else:
                self.client = genai.Client(api_key=api_key)
        
        elif provider == 'groq':
            if not Groq:
                self.logger.error("Groq library not installed.")
            else:
                self.client = Groq(api_key=api_key)
        
        else:
            self.logger.error(f"Unknown provider: {provider}")

    def register_skill(self, skill: BaseSkill):
        """Registers a skill to be used by the agent."""
        self.skills[skill.name] = skill
        self.logger.info(f"Registered skill: {skill.name}")

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
            
        declarations = []
        for skill in self.skills.values():
             declarations.append(
                 types.FunctionDeclaration(
                     name=skill.name,
                     description=skill.description,
                     parameters=skill.parameters
                 )
             )
        
        # In the new SDK, tools is usually a list of Tool objects or dicts
        # We wrap all functions in one Tool object usually
        return [types.Tool(function_declarations=declarations)]

    async def process(self, user_msg: str, context: Dict[str, Any], chat_history: str = "") -> str:
        """
        Main Agent Loop:
        1. Prepare prompt
        2. Call LLM with tools
        3. If tool call -> Execute -> Recursion
        4. If text -> Return
        """
        
        # Construct System Prompt
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

        messages = []
        # Note: Handling history format differences between providers is tricky.
        # For now, we prepend history to the user message or system prompt for simplicity,
        # or we rely on the `chat_history` string passed in.
        # Given "Lightweight", appending to prompt is efficient enough for short context.
        
        full_prompt = f"{system_prompt}\n\nUsuário: {user_msg}"
        
        # --- LOOP CONTROL ---
        max_turns = 5
        current_turn = 0
        
        # We need to maintain a conversation state for the loop
        # For Groq: messages array
        # For Gemini: chat session or content list
        
        groq_messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Histórico:\n{chat_history}\n\nMensagem Atual: {user_msg}"}
        ]
        
        # Gemini logic is slightly different (contents list)
        
        while current_turn < max_turns:
            current_turn += 1
            
            try:
                if self.provider == 'groq':
                    tools = self._get_groq_tools()
                    response = self.client.chat.completions.create(
                        model=self.model_name,
                        messages=groq_messages,
                        tools=tools if tools else None,
                        tool_choice="auto" if tools else None,
                        max_tokens=1024
                    )
                    
                    msg = response.choices[0].message
                    groq_messages.append(msg) # Add assistant response to history
                    
                    if msg.tool_calls:
                        # Handle Tool Calls
                        for tool_call in msg.tool_calls:
                            fn_name = tool_call.function.name
                            fn_args = json.loads(tool_call.function.arguments)
                            
                            self.logger.info(f"Invoking tool: {fn_name} with {fn_args}")
                            
                            skill = self.skills.get(fn_name)
                            if skill:
                                try:
                                    result = await skill.execute(context, **fn_args)
                                    result_str = json.dumps(result, ensure_ascii=False)
                                except Exception as e:
                                    result_str = json.dumps({"error": str(e)})
                            else:
                                result_str = json.dumps({"error": f"Tool {fn_name} not found"})

                            # Append Tool Result
                            groq_messages.append({
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "name": fn_name,
                                "content": result_str
                            })
                        
                        # Loop continues to next iteration to get AI response for the result
                        continue
                    else:
                        # Final text response
                        return msg.content

                elif self.provider == 'gemini':
                    # Simplified single-turn for now (Gemini SDK handles history via ChatSession usually)
                    # For Tool use manual loop with generate_content:
                    
                    # Gemini New SDK logic:
                    # config=types.GenerateContentConfig(tools=...)
                    
                    gemini_tools = self._get_gemini_tools()
                    
                    # Problem: We need to feed the previous turns into Gemini.
                    # 'contents' parameter accepts a list of Content objects.
                    # We need to construct 'contents' matching the loop state.
                   
                    # Initial content
                    if current_turn == 1:
                        # First turn
                        contents = [f"{system_prompt}\n\nContexto:\n{chat_history}\n\nUsuário: {user_msg}"]
                    else:
                        # Subsequent turns, we rely on the client maintaining state? No, we use `contents` list.
                        # But `groq_messages` structure is specific to OpenAI.
                        # We need a generic `conversation_state` list for Gemini.
                        pass # Need separate state tracking for Gemini if we want multi-turn tool use.
                        
                    # Let's use a simplified approach for Gemini: ChatSession
                    if current_turn == 1:
                        self.chat = self.client.chats.create(
                            model=self.model_name,
                            config=types.GenerateContentConfig(
                                tools=gemini_tools,
                                temperature=0.7
                            )
                        )
                        # We inject system prompt behavior via the first message or system_instruction if supported
                        # 2.0 Flash supports system_instruction
                        self.chat = self.client.chats.create(
                            model=self.model_name,
                            config=types.GenerateContentConfig(
                                tools=gemini_tools,
                                system_instruction=system_prompt
                            )
                        )
                        
                        response = self.chat.send_message(f"Histórico:\n{chat_history}\n\nMensagem Atual: {user_msg}")
                    else:
                        # Result from previous turn is already sent? 
                        # No, in standard loop we send result.
                        # With ChatSession, we send the result as a message.
                        # Logic:
                        # 1. response = chat.send_message(user_input)
                        # 2. while response.function_calls: ...
                        # Actually the updated SDKs often handle automatic function calling!
                        # But we want manual control or we need to implement the execution callback.
                        # `google-genai` automatic function calling:
                        # client.chats.create(..., config=..., tools=...)
                        # If we provide the tool FUNCTIONS (callables), it auto-executes.
                        # But our skills are keys in a dict.
                        # We can create a map of callables: { s.name: functools.partial(s.execute, context) ... }
                        # BUT s.execute is async! The SDK might not support async callbacks easily or effectively.
                        
                        # Manual Loop for Gemini (safest):
                        # 1. generate_content(contents)
                        # 2. check function_calls
                        # 3. append function_response to contents
                        # 4. repeat
                        pass
                        
                    # Re-implementing Manual Loop for Gemini (Stateful list)
                    if current_turn == 1:
                        self.gemini_contents = [
                            types.Content(
                                role="user",
                                parts=[types.Part.from_text(f"{system_prompt}\n\nHistórico:\n{chat_history}\n\nMensagem Atual: {user_msg}")]
                            )
                        ]
                        
                    response = self.client.models.generate_content(
                        model=self.model_name,
                        contents=self.gemini_contents,
                        config=types.GenerateContentConfig(tools=gemini_tools)
                    )
                    
                    # Check for tool calls
                    # response.candidates[0].content.parts ...
                    
                    if not response.candidates:
                         return "Erro: Sem resposta da IA."
                         
                    part = response.candidates[0].content.parts[0]
                    
                    # Append AI response to history
                    self.gemini_contents.append(response.candidates[0].content)
                    
                    if part.function_call:
                        # Execute
                        fn_name = part.function_call.name
                        fn_args = part.function_call.args
                        
                        self.logger.info(f"Invoking tool (Gemini): {fn_name}")
                        
                        skill = self.skills.get(fn_name)
                        result_dict = {}
                        if skill:
                             try:
                                 # Convert args to dict (it's usually a Map)
                                 kwargs = {k: v for k, v in fn_args.items()}
                                 result_dict = await skill.execute(context, **kwargs)
                             except Exception as e:
                                 result_dict = {"error": str(e)}
                        else:
                             result_dict = {"error": "Tool not found"}

                        # Send result back
                        self.gemini_contents.append(
                            types.Content(
                                role="tool",
                                parts=[types.Part.from_function_response(
                                    name=fn_name,
                                    response=result_dict
                                )]
                            )
                        )
                        continue # Loop
                    else:
                        return part.text

            except Exception as e:
                self.logger.error(f"Error in Agent Loop: {e}")
                return "Desculpe, tive um erro ao processar seu pedido."

        return "Desculpe, atingi o limite de tentativas de pensamento."
