from __future__ import annotations

from typing import Any

from aiohttp import ClientResponseError
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, OptionsFlow, ConfigEntry
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.selector import (
    TextSelector,
    TextSelectorConfig,
    BooleanSelector,
    NumberSelector,
    NumberSelectorConfig,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)
from homeassistant.helpers import config_validation as cv

from .const import (
    DOMAIN,
    # Conexión / endpoint / modelo
    CONF_BASE_URL,
    CONF_API_KEY,
    CONF_MODEL,
    CONF_VERIFY_SSL,
    CONF_ENDPOINT,
    ENDPOINT_CHAT,
    ENDPOINT_RESPONSES,
    ENDPOINT_COMPLETIONS,
    DEFAULT_ENDPOINT,
    # Agent / LLM
    CONF_AGENT_NAME,
    CONF_SYSTEM_PROMPT,
    CONF_TEMPERATURE,
    CONF_TOP_P,
    CONF_MAX_TOKENS,
    CONF_MAX_HISTORY,
    CONF_TIMEOUT,
    CONF_STREAM,
    CONF_REFRESH_SYSTEM_EVERY_TURN,
    # Tools
    CONF_ENABLE_TOOLS,
    CONF_ALLOWED_DOMAINS,
    CONF_TOOL_ITER_LIMIT,
    CONF_TOOL_FOLLOW_UP_MODE,
    TOOL_FOLLOW_UP_LLM,
    TOOL_FOLLOW_UP_DIRECT,
    # Control mode
    CONF_CONTROL_MODE,
    CONTROL_MODE_NONE,
    CONTROL_MODE_ASSIST,
    CONTROL_MODE_LLM,
    DEFAULT_CONTROL_MODE,
    # Estado manual tools
    CONF_MODEL_SUPPORTS_TOOLS,
    # ICL
    CONF_ENABLE_ICL,
    CONF_ICL_MAX_EXAMPLES,
    CONF_ICL_AUTO_CAPTURE,
    CONF_ICL_CLEAR,
    DEFAULT_ENABLE_ICL,
    DEFAULT_ICL_MAX_EXAMPLES,
    DEFAULT_ICL_AUTO_CAPTURE,
    # Defaults
    DEFAULT_AGENT_NAME,
    DEFAULT_SYSTEM_PROMPT,
    DEFAULT_TEMPERATURE,
    DEFAULT_TOP_P,
    DEFAULT_MAX_TOKENS,
    DEFAULT_MAX_HISTORY,
    DEFAULT_TIMEOUT,
    DEFAULT_STREAM,
    DEFAULT_ENABLE_TOOLS,
    DEFAULT_ALLOWED_DOMAINS,
    DEFAULT_TOOL_ITER_LIMIT,
    DEFAULT_TOOL_FOLLOW_UP_MODE,
    DEFAULT_REFRESH_SYSTEM_EVERY_TURN,
)
from .api import LemonadeClient
from .icl import ICLStore

ENDPOINT_OPTIONS = [ENDPOINT_CHAT, ENDPOINT_RESPONSES, ENDPOINT_COMPLETIONS]


class LemonadeConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._base_url: str | None = None
        self._api_key: str | None = None
        self._verify_ssl: bool = True
        self._endpoint: str = DEFAULT_ENDPOINT
        self._models: list[str] = []
        self._model_labels: dict[str, str] = {}

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            base_url = str(user_input[CONF_BASE_URL]).rstrip("/")
            api_key = user_input.get(CONF_API_KEY) or ""
            verify_ssl = bool(user_input.get(CONF_VERIFY_SSL, True))
            endpoint = user_input.get(CONF_ENDPOINT, DEFAULT_ENDPOINT)

            client = LemonadeClient(self.hass, base_url, api_key, verify_ssl)
            try:
                md = await client.async_list_models_detailed()
                if not md:
                    errors["base"] = "no_models"
                else:
                    self._base_url = base_url
                    self._api_key = api_key
                    self._verify_ssl = verify_ssl
                    self._endpoint = endpoint
                    self._models = [m["id"] for m in md]
                    self._model_labels = {m["id"]: f"{m['id']} — {m.get('recipe','unknown')}" for m in md}
                    return await self.async_step_model()
            except ClientResponseError as e:
                errors["base"] = "auth" if e.status == 401 else "conn"
            except Exception:
                errors["base"] = "conn"

        schema = vol.Schema(
            {
                vol.Required(CONF_BASE_URL, default="http://lemonade_server:8000/api/v1"): TextSelector(TextSelectorConfig(type="text")),
                vol.Optional(CONF_API_KEY): TextSelector(TextSelectorConfig(type="password")),
                vol.Optional(CONF_VERIFY_SSL, default=True): BooleanSelector(),
                vol.Optional(CONF_ENDPOINT, default=DEFAULT_ENDPOINT): SelectSelector(
                    SelectSelectorConfig(options=ENDPOINT_OPTIONS, mode=SelectSelectorMode.DROPDOWN)
                ),
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
                CONF_MODEL: model,
                CONF_AGENT_NAME: DEFAULT_AGENT_NAME,
                CONF_SYSTEM_PROMPT: DEFAULT_SYSTEM_PROMPT,
                CONF_REFRESH_SYSTEM_EVERY_TURN: DEFAULT_REFRESH_SYSTEM_EVERY_TURN,
                CONF_TEMPERATURE: DEFAULT_TEMPERATURE,
                CONF_TOP_P: DEFAULT_TOP_P,
                CONF_MAX_TOKENS: DEFAULT_MAX_TOKENS,
                CONF_MAX_HISTORY: DEFAULT_MAX_HISTORY,
                CONF_TIMEOUT: DEFAULT_TIMEOUT,
                CONF_STREAM: DEFAULT_STREAM,
                CONF_ENDPOINT: self._endpoint,
                CONF_CONTROL_MODE: DEFAULT_CONTROL_MODE,
                CONF_ENABLE_TOOLS: DEFAULT_ENABLE_TOOLS,
                CONF_MODEL_SUPPORTS_TOOLS: False,
                CONF_TOOL_FOLLOW_UP_MODE: DEFAULT_TOOL_FOLLOW_UP_MODE,
                CONF_ALLOWED_DOMAINS: DEFAULT_ALLOWED_DOMAINS,
                CONF_TOOL_ITER_LIMIT: DEFAULT_TOOL_ITER_LIMIT,
                CONF_ENABLE_ICL: DEFAULT_ENABLE_ICL,
                CONF_ICL_MAX_EXAMPLES: DEFAULT_ICL_MAX_EXAMPLES,
                CONF_ICL_AUTO_CAPTURE: DEFAULT_ICL_AUTO_CAPTURE,
            }
            return self.async_create_entry(title=f"Lemonade: {model}", data=data, options=options)

        options = [{"value": mid, "label": self._model_labels.get(mid, mid)} for mid in self._models] or [{"value": "default", "label": "default"}]
        schema = vol.Schema(
            {
                vol.Required(CONF_MODEL): SelectSelector(
                    SelectSelectorConfig(options=options, mode=SelectSelectorMode.DROPDOWN)
                )
            }
        )
        return self.async_show_form(step_id="model", data_schema=schema)

    @staticmethod
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return LemonadeOptionsFlowHandler(config_entry)


class LemonadeOptionsFlowHandler(OptionsFlow):
    def __init__(self, entry: ConfigEntry) -> None:
        self._entry = entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        return self.async_show_menu(
            step_id="init",
            menu_options={
                "general": "General",
                "control": "Control y Tools",
                "icl": "ICL (In-Context Learning)",
                "prompt": "Prompt y Estilo",
                "advanced": "Avanzado",
            },
        )

    async def async_step_general(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        opts = {**self._entry.options}
        data = self._entry.data

        client = LemonadeClient(self.hass, data.get(CONF_BASE_URL), data.get(CONF_API_KEY, ""), data.get(CONF_VERIFY_SSL, True))
        try:
            md = await client.async_list_models_detailed()
            model_options = [{"value": m["id"], "label": f"{m['id']} — {m.get('recipe','unknown')}"} for m in md]
        except Exception:
            model_options = [{"value": opts.get(CONF_MODEL, data.get(CONF_MODEL, "")), "label": opts.get(CONF_MODEL, data.get(CONF_MODEL, ""))}]

        schema = vol.Schema(
            {
                vol.Optional(CONF_MODEL, default=opts.get(CONF_MODEL, data.get(CONF_MODEL, ""))): SelectSelector(
                    SelectSelectorConfig(options=model_options, mode=SelectSelectorMode.DROPDOWN)
                ),
                vol.Optional(CONF_ENDPOINT, default=opts.get(CONF_ENDPOINT, data.get(CONF_ENDPOINT, DEFAULT_ENDPOINT))): SelectSelector(
                    SelectSelectorConfig(options=[ENDPOINT_CHAT, ENDPOINT_RESPONSES, ENDPOINT_COMPLETIONS], mode=SelectSelectorMode.DROPDOWN)
                ),
                vol.Optional(CONF_AGENT_NAME, default=opts.get(CONF_AGENT_NAME, DEFAULT_AGENT_NAME)): TextSelector(TextSelectorConfig(type="text")),
            }
        )
        if user_input is not None:
            new_opts = {**opts, **user_input}
            return self.async_create_entry(title="", data=new_opts)
        return self.async_show_form(step_id="general", data_schema=schema)

    async def async_step_control(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        opts = {**self._entry.options}
        allowed_options = sorted(set(DEFAULT_ALLOWED_DOMAINS + opts.get(CONF_ALLOWED_DOMAINS, [])))

        schema = vol.Schema(
            {
                vol.Optional(CONF_CONTROL_MODE, default=opts.get(CONF_CONTROL_MODE, DEFAULT_CONTROL_MODE)): SelectSelector(
                    SelectSelectorConfig(options=[CONTROL_MODE_NONE, CONTROL_MODE_ASSIST, CONTROL_MODE_LLM], mode=SelectSelectorMode.DROPDOWN)
                ),
                vol.Optional(CONF_ENABLE_TOOLS, default=opts.get(CONF_ENABLE_TOOLS, True)): BooleanSelector(),
                vol.Optional(CONF_MODEL_SUPPORTS_TOOLS, default=opts.get(CONF_MODEL_SUPPORTS_TOOLS, False)): BooleanSelector(),
                vol.Optional(CONF_TOOL_FOLLOW_UP_MODE, default=opts.get(CONF_TOOL_FOLLOW_UP_MODE, DEFAULT_TOOL_FOLLOW_UP_MODE)): SelectSelector(
                    SelectSelectorConfig(options=[TOOL_FOLLOW_UP_LLM, TOOL_FOLLOW_UP_DIRECT], mode=SelectSelectorMode.DROPDOWN)
                ),
                vol.Optional(CONF_ALLOWED_DOMAINS, default=opts.get(CONF_ALLOWED_DOMAINS, DEFAULT_ALLOWED_DOMAINS)): SelectSelector(
                    SelectSelectorConfig(options=allowed_options, multiple=True, mode=SelectSelectorMode.DROPDOWN)
                ),
                vol.Optional(CONF_TOOL_ITER_LIMIT, default=opts.get(CONF_TOOL_ITER_LIMIT, DEFAULT_TOOL_ITER_LIMIT)): NumberSelector(
                    NumberSelectorConfig(min=1, max=5, step=1, mode="slider")
                ),
            }
        )
        if user_input is not None:
            new_opts = {**opts, **user_input}
            return self.async_create_entry(title="", data=new_opts)
        return self.async_show_form(step_id="control", data_schema=schema)

    async def async_step_icl(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        opts = {**self._entry.options}

        schema = vol.Schema(
            {
                vol.Optional(CONF_ENABLE_ICL, default=opts.get(CONF_ENABLE_ICL, False)): BooleanSelector(),
                vol.Optional(CONF_ICL_MAX_EXAMPLES, default=opts.get(CONF_ICL_MAX_EXAMPLES, 4)): NumberSelector(
                    NumberSelectorConfig(min=0, max=20, step=1, mode="slider")
                ),
                vol.Optional(CONF_ICL_AUTO_CAPTURE, default=opts.get(CONF_ICL_AUTO_CAPTURE, False)): BooleanSelector(),
                vol.Optional(CONF_ICL_CLEAR, default=False): BooleanSelector(),
            }
        )
        if user_input is not None:
            new_opts = {**opts, **user_input}
            if user_input.get(CONF_ICL_CLEAR):
                try:
                    store = ICLStore(self.hass, self._entry.entry_id)
                    await store.async_clear()
                except Exception:
                    pass
                new_opts[CONF_ICL_CLEAR] = False
            return self.async_create_entry(title="", data=new_opts)
        return self.async_show_form(step_id="icl", data_schema=schema)

    async def async_step_prompt(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        opts = {**self._entry.options}
        schema = vol.Schema(
            {
                vol.Optional(CONF_SYSTEM_PROMPT, default=opts.get(CONF_SYSTEM_PROMPT, DEFAULT_SYSTEM_PROMPT)): TextSelector(
                    TextSelectorConfig(type="text", multiline=True)
                ),
                vol.Optional(CONF_REFRESH_SYSTEM_EVERY_TURN, default=opts.get(CONF_REFRESH_SYSTEM_EVERY_TURN, DEFAULT_REFRESH_SYSTEM_EVERY_TURN)): BooleanSelector(),
            }
        )
        if user_input is not None:
            new_opts = {**opts, **user_input}
            return self.async_create_entry(title="", data=new_opts)
        return self.async_show_form(step_id="prompt", data_schema=schema)

    async def async_step_advanced(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        opts = {**self._entry.options}
        schema = vol.Schema(
            {
                vol.Optional(CONF_TEMPERATURE, default=opts.get(CONF_TEMPERATURE, DEFAULT_TEMPERATURE)): NumberSelector(
                    NumberSelectorConfig(min=0, max=2, step=0.1, mode="slider")
                ),
                vol.Optional(CONF_TOP_P, default=opts.get(CONF_TOP_P, DEFAULT_TOP_P)): NumberSelector(
                    NumberSelectorConfig(min=0, max=1, step=0.05, mode="slider")
                ),
                vol.Optional(CONF_MAX_TOKENS, default=opts.get(CONF_MAX_TOKENS, DEFAULT_MAX_TOKENS)): NumberSelector(
                    NumberSelectorConfig(min=64, max=8192, step=64, mode="box")
                ),
                vol.Optional(CONF_MAX_HISTORY, default=opts.get(CONF_MAX_HISTORY, DEFAULT_MAX_HISTORY)): NumberSelector(
                    NumberSelectorConfig(min=0, max=20, step=1, mode="slider")
                ),
                vol.Optional(CONF_TIMEOUT, default=opts.get(CONF_TIMEOUT, DEFAULT_TIMEOUT)): NumberSelector(
                    NumberSelectorConfig(min=5, max=120, step=5, mode="box")
                ),
                vol.Optional(CONF_STREAM, default=opts.get(CONF_STREAM, DEFAULT_STREAM)): BooleanSelector(),
            }
        )
        if user_input is not None:
            new_opts = {**opts, **user_input}
            return self.async_create_entry(title="", data=new_opts)
        return self.async_show_form(step_id="advanced", data_schema=schema)
