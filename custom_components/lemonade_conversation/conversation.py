import aiohttp
import json
import logging
from typing import Any, Dict, List, Optional
from homeassistant.components.conversation import AbstractConversationAgent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.template import Template
from .const import DOMAIN
from .helpers import detect_language, get_home_assistant_tools, execute_tool

_LOGGER = logging.getLogger(__name__)

class LemonadeConversationAgent(AbstractConversationAgent):
    def __init__(self, hass: HomeAssistant, entry_data: Dict[str, Any]):
        self.hass = hass
        self.base_url = entry_data["base_url"]
        self.api_key = entry_data.get("api_key")
        self.model = entry_data.get("model", "gpt-3.5-turbo")
        self.prompt_template = entry_data.get("prompt_template", "")
        self.max_tokens = entry_data.get("max_tokens", 150)
        self.temperature = entry_data.get("temperature", 0.7)
        self.tools_enabled = entry_data.get("tools_enabled", True)
        
        # Mantener historial por conversación
        self.conversation_history = {}

    async def async_process(self, text: str, context: dict, conversation_id: str = None) -> dict:
        session = async_get_clientsession(self.hass)
        url = f"{self.base_url.rstrip('/')}/v1/chat/completions"

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        # Detectar idioma
        detected_language = detect_language(text)
        
        # Generar prompt usando template
        prompt = self._generate_prompt(text, context, detected_language)
        
        # Preparar historial
        if conversation_id not in self.conversation_history:
            self.conversation_history[conversation_id] = []
            
        messages = self.conversation_history[conversation_id].copy()
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
        }

        # Agregar herramientas si están habilitadas
        if self.tools_enabled:
            tools = get_home_assistant_tools(self.hass)
            if tools:
                payload["tools"] = tools
                payload["tool_choice"] = "auto"

        try:
            async with session.post(url, headers=headers, json=payload) as resp:
                result = await resp.json()
                
                if "choices" not in result or len(result["choices"]) == 0:
                    raise Exception("Respuesta inválida del servidor")
                    
                choice = result["choices"][0]
                message = choice["message"]
                
                response_text = message.get("content", "")
                
                # Guardar en historial
                self.conversation_history[conversation_id].append({"role": "user", "content": prompt})
                self.conversation_history[conversation_id].append({"role": "assistant", "content": response_text})
                
                # Manejar llamadas a herramientas
                tool_calls = message.get("tool_calls", [])
                if tool_calls and self.tools_enabled:
                    tool_responses = []
                    for tool_call in tool_calls:
                        function_name = tool_call["function"]["name"]
                        function_args = json.loads(tool_call["function"]["arguments"])
                        
                        tool_response = await execute_tool(self.hass, function_name, function_args)
                        tool_responses.append({
                            "tool_call_id": tool_call["id"],
                            "role": "tool",
                            "name": function_name,
                            "content": tool_response,
                        })
                    
                    # Agregar respuestas de herramientas al historial
                    self.conversation_history[conversation_id].extend(tool_responses)
                    
                    # Hacer otra llamada para obtener respuesta final
                    messages.extend(tool_responses)
                    payload["messages"] = messages
                    payload.pop("tools", None)
                    payload.pop("tool_choice", None)
                    
                    async with session.post(url, headers=headers, json=payload) as resp2:
                        result2 = await resp2.json()
                        response_text = result2["choices"][0]["message"].get("content", "")
                        self.conversation_history[conversation_id].append({"role": "assistant", "content": response_text})

                return {
                    "response": response_text.strip(),
                    "success": True,
                    "error": None,
                }
        except Exception as e:
            _LOGGER.error(f"Lemonade request failed: {e}")
            return {
                "response": "",
                "success": False,
                "error": str(e),
            }

    def _generate_prompt(self, user_input: str, context: dict, language: str) -> str:
        """Genera el prompt usando el template proporcionado."""
        try:
            template = Template(self.prompt_template, self.hass)
            return template.async_render({
                "user_input": user_input,
                "context": context,
                "language": language,
                "states": self.hass.states
            })
        except Exception as e:
            _LOGGER.warning(f"Error renderizando template: {e}. Usando entrada directa.")
            return user_input

async def async_setup_entry(hass: HomeAssistant, entry):
    entry_data = hass.data[DOMAIN][entry.entry_id]
    agent = LemonadeConversationAgent(hass, entry_data)
    hass.data.setdefault("conversation_agents", {})[entry.entry_id] = agent
    return True