import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from .const import DOMAIN, CONF_BASE_URL, CONF_API_KEY, CONF_MODEL

DEFAULT_MODEL = "gpt-3.5-turbo"

class LemonadeConversationConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    
    async def async_step_user(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="Lemonade Conversation", data=user_input)
            
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_BASE_URL): str,
                vol.Optional(CONF_API_KEY): str,
                vol.Optional(CONF_MODEL, default=DEFAULT_MODEL): str,
            })
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return OptionsFlowHandler(config_entry)

class OptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
            
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional(CONF_BASE_URL, default=self.config_entry.data.get(CONF_BASE_URL)): str,
                vol.Optional(CONF_API_KEY, default=self.config_entry.data.get(CONF_API_KEY, "")): str,
                vol.Optional(CONF_MODEL, default=self.config_entry.data.get(CONF_MODEL, DEFAULT_MODEL)): str,
            })
        )
