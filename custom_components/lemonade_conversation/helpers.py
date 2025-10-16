import asyncio
from typing import Dict, List, Any
from homeassistant.core import HomeAssistant
from homeassistant.helpers.template import Template
import langdetect

def detect_language(text: str) -> str:
    """Detecta el idioma del texto."""
    try:
        return langdetect.detect(text)
    except:
        return "en"

def get_home_assistant_tools(hass: HomeAssistant) -> List[Dict[str, Any]]:
    """Obtiene las herramientas disponibles en Home Assistant."""
    tools = []
    
    tools.append({
        "type": "function",
        "function": {
            "name": "get_device_state",
            "description": "Obtener el estado de un dispositivo",
            "parameters": {
                "type": "object",
                "properties": {
                    "entity_id": {
                        "type": "string",
                        "description": "ID del dispositivo"
                    }
                },
                "required": ["entity_id"]
            }
        }
    })
    
    tools.append({
        "type": "function",
        "function": {
            "name": "turn_on_device",
            "description": "Encender un dispositivo",
            "parameters": {
                "type": "object",
                "properties": {
                    "entity_id": {
                        "type": "string",
                        "description": "ID del dispositivo"
                    }
                },
                "required": ["entity_id"]
            }
        }
    })
    
    tools.append({
        "type": "function",
        "function": {
            "name": "turn_off_device",
            "description": "Apagar un dispositivo",
            "parameters": {
                "type": "object",
                "properties": {
                    "entity_id": {
                        "type": "string",
                        "description": "ID del dispositivo"
                    }
                },
                "required": ["entity_id"]
            }
        }
    })
    
    return tools

async def execute_tool(hass: HomeAssistant, tool_name: str, arguments: Dict[str, Any]) -> str:
    """Ejecuta una herramienta específica."""
    try:
        if tool_name == "get_device_state":
            entity_id = arguments.get("entity_id")
            state = hass.states.get(entity_id)
            if state:
                return f"Estado de {entity_id}: {state.state}"
            else:
                return f"Dispositivo {entity_id} no encontrado"
                
        elif tool_name == "turn_on_device":
            entity_id = arguments.get("entity_id")
            await hass.services.async_call("homeassistant", "turn_on", {"entity_id": entity_id})
            return f"Dispositivo {entity_id} encendido"
            
        elif tool_name == "turn_off_device":
            entity_id = arguments.get("entity_id")
            await hass.services.async_call("homeassistant", "turn_off", {"entity_id": entity_id})
            return f"Dispositivo {entity_id} apagado"
            
        else:
            return f"Herramienta {tool_name} no reconocida"
    except Exception as e:
        return f"Error ejecutando herramienta: {str(e)}"