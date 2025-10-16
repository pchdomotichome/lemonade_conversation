from __future__ import annotations

from typing import Any

from aiohttp import ClientResponseError
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, OptionsFlow, ConfigEntry
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_validation as cv

from .const import (
    DOMAIN,
    CONF_BASE_URL,
    CONF_API_KEY,
    CONF_MODEL,
    CONF_VERIFY_SSL,
    CONF_ENDPOINT,
    ENDPOINT_CHAT,
    ENDPOINT_RESPONSES,
    ENDPOINT_COMPLETIONS,
    DEFAULT_ENDPOINT,
    CONF_AGENT_NAME,
    CONF_SYSTEM_PROMPT,
    CONF_TEMPERATURE,
    CONF_TOP_P,
    CONF_MAX_TOKENS,
    CONF_MAX_HISTORY,
    CONF_ENABLE_TOOLS,
    CONF_ALLOWED_DOMAINS,
    CONF_TOOL_ITER_LIMIT,
    CONF_TIMEOUT,
    CONF_STREAM,
    DEFAULT_AGENT_NAME,
    DEFAULT_SYSTEM_PROMPT,
    DEFAULT_TEMPERATURE,
    DEFAULT_TOP_P,
    DEFAULT_MAX_TOKENS,
    DEFAULT_MAX_HISTORY,
    DEFAULT_ENABLE_TOOLS,
    DEFAULT_TOOL_ITER_LIMIT,
    DEFAULT_ALLOWED_DOMAINS,
    DEFAULT_TIMEOUT,
    DEFAULT_STREAM,
)
from .api import LemonadeClient


ENDPOINTS = [ENDPOINT_CHAT, ENDPOINT_RESPONSES, ENDPOINT_COMPLETIONS]


class LemonadeConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._base_url: str | None = None
        self._api_key: str | None = None
        self._verify_ssl: bool = True
        self._endpoint: str = DEFAULT_ENDPOINT
        self._models: list[str] = []

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            base_url = str(user_input[CONF_BASE_URL]).rstrip("/")
            api_key = user_input.get(CONF_API_KEY) or ""
            verify_ssl = bool(user_input.get(CONF_VERIFY_SSL, True))
            endpoint = user_input.get(CONF_ENDPOINT, DEFAULT_ENDPOINT)

            client = LemonadeClient(self.hass, base_url, api_key, verify_ssl)
            try:
                models = await client.async_list_models()
                if not models:
                    errors["base"] = "no_models"
                else:
                    self._base_url = base_url
                    self._api_key = api_key
                    self._verify_ssl = verify_ssl
                    self._endpoint = endpoint
                    self._models = models
                    return await self.async_step_model()
            except ClientResponseError as e:
                errors["base"] = "auth" if e.status == 401 else "conn"
            except Exception:
                errors["base"] = "conn"

        schema = vol.Schema(
            {
                vol.Required(CONF_BASE_URL, default="http://lemonade_server:8000/api/v1"): str,
                vol.Optional(CONF_API_KEY, default=""): str,
                vol.Optional(CONF_VERIFY_SSL, default=True): cv.boolean,
                vol.Optional(CONF_ENDPOINT, default=DEFAULT_ENDPOINT): vol.In(ENDPOINTS),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_model(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        if user_input is not None:
            model = user_input[CONF_MODEL]
            data = {
                CONF_BASE_URL: self._base_url,
                CONF_API_KEY: self._api_key,
                CONF_VERIFY_SSL: self._verify_ssl,
                CONF_ENDPOINT: self._endpoint,
                CONF_MODEL: model,
            }
            options = {
                CONF_AGENT_NAME: DEFAULT_AGENT_NAME,
                CONF_SYSTEM_PROMPT: DEFAULT_SYSTEM_PROMPT,
                CONF_TEMPERATURE: DEFAULT_TEMPERATURE,
                CONF_TOP_P: DEFAULT_TOP_P,
                CONF_MAX_TOKENS: DEFAULT_MAX_TOKENS,
                CONF_MAX_HISTORY: DEFAULT_MAX_HISTORY,
                CONF_ENABLE_TOOLS: DEFAULT_ENABLE_TOOLS,
                CONF_ALLOWED_DOMAINS: DEFAULT_ALLOWED_DOMAINS,
                CONF_TOOL_ITER_LIMIT: DEFAULT_TOOL_ITER_LIMIT,
                CONF_TIMEOUT: DEFAULT_TIMEOUT,
                CONF_STREAM: DEFAULT_STREAM,
                CONF_ENDPOINT: self._endpoint,
            }
            return self.async_create_entry(title=f"Lemonade: {model}", data=data, options=options)

        # Si Lemonade devuelve muchos modelos, esta lista se mostrará en un select nativo
        schema = vol.Schema({vol.Required(CONF_MODEL): vol.In(self._models or ["Qwen3-4B-Instruct-2507-GGUF"])})
        return self.async_show_form(step_id="model", data_schema=schema)

    @staticmethod
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return LemonadeOptionsFlowHandler(config_entry)


class LemonadeOptionsFlowHandler(OptionsFlow):
    def __init__(self, entry: ConfigEntry) -> None:
        self._entry = entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        opts = {**self._entry.options}
        data = self._entry.data

        if user_input is not None:
            # Normalizar allowed_domains (puede venir como dict desde el multi_select)
            allowed = user_input.get(CONF_ALLOWED_DOMAINS)
            if isinstance(allowed, dict):
                # cv.multi_select puede entregar dict {key: True/False}; convertimos a lista
                user_input[CONF_ALLOWED_DOMAINS] = [k for k, v in allowed.items() if v]
            return self.async_create_entry(title="", data=user_input)

        # Mapa para multi_select: {"light":"light", "switch":"switch", ...}
        allowed_map = {d: d for d in sorted(set(DEFAULT_ALLOWED_DOMAINS + opts.get(CONF_ALLOWED_DOMAINS, [])))}

        schema = vol.Schema(
            {
                vol.Optional(CONF_AGENT_NAME, default=opts.get(CONF_AGENT_NAME, DEFAULT_AGENT_NAME)): str,
                vol.Optional(CONF_SYSTEM_PROMPT, default=opts.get(CONF_SYSTEM_PROMPT, DEFAULT_SYSTEM_PROMPT)): str,
                vol.Optional(CONF_TEMPERATURE, default=opts.get(CONF_TEMPERATURE, DEFAULT_TEMPERATURE)): vol.All(
                    vol.Coerce(float), vol.Range(min=0, max=2)
                ),
                vol.Optional(CONF_TOP_P, default=opts.get(CONF_TOP_P, DEFAULT_TOP_P)): vol.All(
                    vol.Coerce(float), vol.Range(min=0, max=1)
                ),
                vol.Optional(CONF_MAX_TOKENS, default=opts.get(CONF_MAX_TOKENS, DEFAULT_MAX_TOKENS)): vol.All(
                    vol.Coerce(int), vol.Range(min=64, max=8192)
                ),
                vol.Optional(CONF_MAX_HISTORY, default=opts.get(CONF_MAX_HISTORY, DEFAULT_MAX_HISTORY)): vol.All(
                    vol.Coerce(int), vol.Range(min=0, max=20)
                ),
                vol.Optional(CONF_ENABLE_TOOLS, default=opts.get(CONF_ENABLE_TOOLS, DEFAULT_ENABLE_TOOLS)): cv.boolean,
                vol.Optional(CONF_ALLOWED_DOMAINS, default=opts.get(CONF_ALLOWED_DOMAINS, DEFAULT_ALLOWED_DOMAINS)): cv.multi_select(
                    allowed_map
                ),
                vol.Optional(CONF_TOOL_ITER_LIMIT, default=opts.get(CONF_TOOL_ITER_LIMIT, DEFAULT_TOOL_ITER_LIMIT)): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=10)
                ),
                vol.Optional(CONF_TIMEOUT, default=opts.get(CONF_TIMEOUT, DEFAULT_TIMEOUT)): vol.All(
                    vol.Coerce(int), vol.Range(min=5, max=120)
                ),
                vol.Optional(CONF_STREAM, default=opts.get(CONF_STREAM, DEFAULT_STREAM)): cv.boolean,
                vol.Optional(CONF_ENDPOINT, default=opts.get(CONF_ENDPOINT, data.get(CONF_ENDPOINT, DEFAULT_ENDPOINT))): vol.In(
                    ENDPOINTS
                ),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
