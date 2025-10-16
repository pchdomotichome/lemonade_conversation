"""Config flow for Lemonade Conversation."""
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from .const import (
    DOMAIN, CONF_BASE_URL, CONF_API_KEY, CONF_MODEL, CONF_PROMPT_TEMPLATE,
    DEFAULT_MODEL, DEFAULT_PROMPT_TEMPLATE, DEFAULT_MAX_TOKENS, DEFAULT_TEMPERATURE,
    CONF_MAX_TOKENS, CONF_TEMPERATURE, CONF_TOOLS_ENABLED
)

class LemonadeConversationConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Lemonade Conversation."""
    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        if user_input is not None:
            return self.async_create_entry(title="Lemonade Assistant", data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_BASE_URL): str,
                vol.Optional(CONF_API_KEY): str,
                vol.Optional(CONF_MODEL, default=DEFAULT_MODEL): str,
                vol.Optional(CONF_PROMPT_TEMPLATE, default=DEFAULT_PROMPT_TEMPLATE): vol.All(str, vol.Length(min=1)),
                vol.Optional(CONF_MAX_TOKENS, default=DEFAULT_MAX_TOKENS): int,
                vol.Optional(CONF_TEMPERATURE, default=DEFAULT_TEMPERATURE): vol.Coerce(float),
                vol.Optional(CONF_TOOLS_ENABLED, default=True): bool,
            })
        )

    @staticmethod
    @callback
    def async_get_options_flow(entry):
        return OptionsFlowHandler(entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, entry):
        self.entry = entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional(CONF_MODEL, default=self.entry.options.get(CONF_MODEL, DEFAULT_MODEL)): str,
                vol.Optional(CONF_PROMPT_TEMPLATE, default=self.entry.options.get(CONF_PROMPT_TEMPLATE, DEFAULT_PROMPT_TEMPLATE)): vol.All(str, vol.Length(min=1)),
                vol.Optional(CONF_MAX_TOKENS, default=self.entry.options.get(CONF_MAX_TOKENS, DEFAULT_MAX_TOKENS)): int,
                vol.Optional(CONF_TEMPERATURE, default=self.entry.options.get(CONF_TEMPERATURE, DEFAULT_TEMPERATURE)): vol.Coerce(float),
                vol.Optional(CONF_TOOLS_ENABLED, default=self.entry.options.get(CONF_TOOLS_ENABLED, True)): bool,
            })
        )
