"""Helper functions for Lemonade Conversation."""
import json
from typing import Dict, List, Any
from homeassistant.core import HomeAssistant
from langdetect import detect, LangDetectException

def detect_language(text: str) -> str:
    """Detect the language of the text."""
    try:
        return detect(text)
    except LangDetectException:
        return "en"

def get_home_assistant_tools() -> List[Dict[str, Any]]:
    """Get the tool definitions for Home Assistant."""
    return [
        {
            "type": "function",
            "function": {
                "name": "get_device_state",
                "description": "Get the state of a specific device or entity.",
                "parameters": {
                    "type": "object",
                    "properties": {"entity_id": {"type": "string", "description": "The ID of the entity."}},
                    "required": ["entity_id"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "turn_on_device",
                "description": "Turn on a device or a group of devices.",
                "parameters": {
                    "type": "object",
                    "properties": {"entity_id": {"type": "string", "description": "The ID of the entity to turn on."}},
                    "required": ["entity_id"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "turn_off_device",
                "description": "Turn off a device or a group of devices.",
                "parameters": {
                    "type": "object",
                    "properties": {"entity_id": {"type": "string", "description": "The ID of the entity to turn off."}},
                    "required": ["entity_id"],
                },
            },
        },
    ]

async def execute_tool_call(hass: HomeAssistant, tool_name: str, arguments: Dict[str, Any]) -> str:
    """Execute a tool call and return the result as a string."""
    try:
        entity_id = arguments.get("entity_id")
        if not entity_id:
            return json.dumps({"error": "entity_id is required"})

        if tool_name == "get_device_state":
            state = hass.states.get(entity_id)
            if state:
                return json.dumps({"entity_id": entity_id, "state": state.state, "attributes": state.attributes})
            return json.dumps({"error": f"Entity {entity_id} not found."})

        elif tool_name == "turn_on_device":
            await hass.services.async_call("homeassistant", "turn_on", {"entity_id": entity_id}, blocking=True)
            return json.dumps({"success": True, "message": f"Device {entity_id} has been turned on."})

        elif tool_name == "turn_off_device":
            await hass.services.async_call("homeassistant", "turn_off", {"entity_id": entity_id}, blocking=True)
            return json.dumps({"success": True, "message": f"Device {entity_id} has been turned off."})

        else:
            return json.dumps({"error": f"Tool {tool_name} is not recognized."})
    except Exception as e:
        return json.dumps({"error": f"Error executing tool {tool_name}: {str(e)}"})
