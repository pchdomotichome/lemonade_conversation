import aiohttp
import json
import logging
from typing import Any, Dict, List
from homeassistant.components import conversation
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import langdetect

_LOGGER = logging.getLogger(__name__)

async def process_conversation(
    hass: HomeAssistant, 
    entry_data: Dict[str, Any], 
    user_input: conversation.ConversationInput
) -> conversation.ConversationResult:
    """Process a conversation turn."""
    
    session = async_get_clientsession(hass)
    base_url = entry_data["base_url"]
    api_key = entry_data.get("api_key")
    model = entry_data.get("model", "gpt-3.5-turbo")
    
    url = f"{base_url.rstrip('/')}/v1/chat/completions"
    
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    
    # Detectar idioma
    try:
        language = langdetect.detect(user_input.text)
    except:
        language = "es"  # Por defecto español
    
    # Construir mensaje
    messages = [
        {
            "role": "system",
            "content": f"Eres un asistente de hogar inteligente. Responde en {language}."
        },
        {
            "role": "user", 
            "content": user_input.text
        }
    ]
    
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": 150,
        "temperature": 0.7,
    }
    
    try:
        async with session.post(url, headers=headers, json=payload) as resp:
            if resp.status != 200:
                error_text = await resp.text()
                _LOGGER.error(f"Lemonade API error: {resp.status} - {error_text}")
                return conversation.ConversationResult(
                    response=conversation.IntentResponse(language),
                    conversation_id=user_input.conversation_id
                )
            
            result = await resp.json()
            
            if "choices" not in result or len(result["choices"]) == 0:
                _LOGGER.error("Invalid response from Lemonade server")
                return conversation.ConversationResult(
                    response=conversation.IntentResponse(language),
                    conversation_id=user_input.conversation_id
                )
            
            response_text = result["choices"][0]["message"]["content"].strip()
            
            intent_response = conversation.IntentResponse(language)
            intent_response.async_set_speech(response_text)
            
            return conversation.ConversationResult(
                response=intent_response,
                conversation_id=user_input.conversation_id
            )
            
    except Exception as e:
        _LOGGER.error(f"Lemonade request failed: {e}")
        intent_response = conversation.IntentResponse(language)
        intent_response.async_set_speech("Lo siento, hubo un error al procesar tu solicitud.")
        return conversation.ConversationResult(
            response=intent_response,
            conversation_id=user_input.conversation_id
        )
