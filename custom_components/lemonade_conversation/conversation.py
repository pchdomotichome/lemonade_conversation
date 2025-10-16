"""Conversation agent for Lemonade Conversation."""
import aiohttp
import json
import logging
from typing import Any, Dict, List
from homeassistant.components.conversation import AbstractConversationAgent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.template import Template
from .const import DOMAIN
from .helpers import detect_language, get_home_assistant_tools, execute_tool_call

_LOGGER = logging.getLogger(__name__)

class LemonadeConversationAgent(AbstractConversationAgent):
    """Lemonade Conversation agent."""

    def __init__(self, hass: HomeAssistant, entry_data: Dict[str, Any]):
        self.hass = hass
        self.base_url = entry_data["base_url"]
        self.api_key = entry_data.get("api_key")
        self.model = entry_data["model"]
        self.prompt_template = Template(entry_data["prompt_template"], self.hass)
        self.max_tokens = entry_data["max_tokens"]
        self.temperature = entry_data["temperature"]
        self.tools_enabled = entry_data["tools_enabled"]
        self.conversation_history: Dict[str, List[Dict]] = {}

    async def async_process(self, text: str, context: dict, conversation_id: str = None) -> dict:
        session = async_get_clientsession(self.hass)
        url = f"{self.base_url.rstrip('/')}/v1/chat/completions"

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        # Initialize history if not present
        if conversation_id not in self.conversation_history:
            self.conversation_history[conversation_id] = []
        
        # Prepare messages, starting with system prompt
        detected_language = detect_language(text)
        system_prompt = self._generate_system_prompt(text, context, detected_language)
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(self.conversation_history[conversation_id])
        messages.append({"role": "user", "content": text})
        
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
        }

        if self.tools_enabled:
            payload["tools"] = get_home_assistant_tools()
            payload["tool_choice"] = "auto"
        
        try:
            _LOGGER.debug("Sending payload to Lemonade: %s", payload)
            async with session.post(url, headers=headers, json=payload, timeout=30) as resp:
                resp.raise_for_status()
                result = await resp.json()
                _LOGGER.debug("Received response from Lemonade: %s", result)

                choice = result["choices"][0]
                message = choice["message"]
                
                # Append user message to history
                self.conversation_history[conversation_id].append({"role": "user", "content": text})

                # Handle tool calls if they exist
                if message.get("tool_calls"):
                    messages.append(message)
                    tool_calls = message["tool_calls"]
                    for tool_call in tool_calls:
                        tool_name = tool_call["function"]["name"]
                        tool_args = json.loads(tool_call["function"]["arguments"])
                        tool_response_content = await execute_tool_call(self.hass, tool_name, tool_args)
                        
                        messages.append({
                            "tool_call_id": tool_call["id"],
                            "role": "tool",
                            "name": tool_name,
                            "content": tool_response_content,
                        })
                    
                    # Make a second API call with the tool responses
                    payload["messages"] = messages
                    payload.pop("tools", None)
                    payload.pop("tool_choice", None)
                    
                    async with session.post(url, headers=headers, json=payload, timeout=30) as resp2:
                        resp2.raise_for_status()
                        result2 = await resp2.json()
                        message = result2["choices"][0]["message"]

                response_content = message.get("content", "").strip()
                self.conversation_history[conversation_id].append({"role": "assistant", "content": response_content})
                
                return {"response": response_content, "success": True}

        except (aiohttp.ClientError, TimeoutError) as e:
            _LOGGER.error("Error communicating with Lemonade Server: %s", e)
            return {"response": f"Sorry, I couldn't connect to the AI service: {e}", "success": False}
        except Exception as e:
            _LOGGER.error("An unexpected error occurred: %s", e)
            return {"response": "Sorry, an unexpected error occurred.", "success": False}

    def _generate_system_prompt(self, user_input: str, context: dict, language: str) -> str:
        """Generate the system prompt using the template."""
        try:
            return self.prompt_template.async_render({
                "user_input": user_input,
                "context": context,
                "language": language,
                "states": self.hass.states
            }, parse_result=False)
        except Exception as e:
            _LOGGER.warning("Error rendering prompt template: %s. Using default.", e)
            return "You are a helpful home assistant."

async def async_setup_entry(hass: HomeAssistant, entry):
    """Set up the Lemonade Conversation agent."""
    agent = LemonadeConversationAgent(hass, entry.data)
    hass.data.setdefault("conversation_agents", {})[entry.entry_id] = agent
    return True
