from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.components import conversation
from .const import DOMAIN

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Lemonade Conversation component."""
    hass.data[DOMAIN] = {}
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Lemonade Conversation from a config entry."""
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = entry.data
    
    # Registrar el agente de conversación
    conversation.async_set_agent(hass, entry, LemonadeConversationAgent(hass, entry.data))
    
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload Lemonade Conversation config entry."""
    conversation.async_unset_agent(hass, entry)
    
    if DOMAIN in hass.data:
        hass.data[DOMAIN].pop(entry.entry_id)
        if not hass.data[DOMAIN]:
            hass.data.pop(DOMAIN)
    
    return True

class LemonadeConversationAgent:
    """Lemonade Conversation Agent."""
    
    def __init__(self, hass: HomeAssistant, entry_data: dict):
        """Initialize the agent."""
        self.hass = hass
        self.entry_data = entry_data
        
    async def async_process(self, user_input: conversation.ConversationInput) -> conversation.ConversationResult:
        """Process a sentence."""
        from .conversation import process_conversation
        return await process_conversation(self.hass, self.entry_data, user_input)
