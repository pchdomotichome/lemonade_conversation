from __future__ import annotations

import json
import logging
import time
from typing import Any

from homeassistant.components.conversation import (
    AbstractConversationAgent,
    ConversationInput,
    ConversationResult,
    async_set_agent,
    async_unset_agent,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import intent
from homeassistant.util import dt as dt_util

from .const import (
    # Conexión / endpoint / modelo
    CONF_API_KEY,
    CONF_BASE_URL,
    CONF_MODEL,
    CONF_VERIFY_SSL,
    CONF_ENDPOINT,
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
    DEFAULT_SYSTEM_PROMPT,
    # Tools
    CONF_ENABLE_TOOLS,
    CONF_ALLOWED_DOMAINS,
    CONF_TOOL_ITER_LIMIT,
    # Autodetección / seguimiento tools
    CONF_AUTO_TOOL_DETECT,
    CONF_TOOL_FOLLOW_UP_MODE,
    TOOL_FOLLOW_UP_LLM,
    TOOL_FOLLOW_UP_DIRECT,
    CONF_HANDSHAKE_TIMEOUT,
    # Verificación en opciones
    CONF_MODEL_SUPPORTS_TOOLS,
    CONF_FORCE_ENABLE_TOOLS,
    # Defaults (por si faltan en options)
    DEFAULT_AUTO_TOOL_DETECT,
    DEFAULT_TOOL_FOLLOW_UP_MODE,
    DEFAULT_HANDSHAKE_TIMEOUT,
)

from .api import LemonadeClient
from .tools import build_tools_schema, exec_tool_call

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    """Registrar el agente de conversación al cargar la plataforma."""
    agent = LemonadeConversationAgent(hass, entry)
    async_set_agent(hass, entry, agent)
    _LOGGER.debug("LemonadeConversation: agente registrado para entry %s", entry.entry_id)
    entry.async_on_unload(lambda: async_unset_agent(hass, entry))


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Desregistrar el agente al descargar la plataforma."""
    async_unset_agent(hass, entry)
    _LOGGER.debug("LemonadeConversation: agente desregistrado para entry %s", entry.entry_id)


async def async_get_agent(hass: HomeAssistant, entry: ConfigEntry) -> AbstractConversationAgent:
    """API usada por Assist para obtener el agente activo (fallback)."""
    _LOGGER.debug("LemonadeConversation: async_get_agent solicitado para entry %s", entry.entry_id)
    return LemonadeConversationAgent(hass, entry)


class LemonadeConversationAgent(AbstractConversationAgent):
    """Agente de conversación que usa Lemonade Server via OpenAI-compatible API."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry

        data = entry.data
        options = entry.options

        # Config principal
        self._display_name: str = options.get(CONF_AGENT_NAME) or "Lemonade Assistant"
        self.model: str = options.get(CONF_MODEL, data[CONF_MODEL])
        self.base_url: str = data[CONF_BASE_URL]
        self.api_key: str = data.get(CONF_API_KEY, "")
        self.verify_ssl: bool = data.get(CONF_VERIFY_SSL, True)
        self.endpoint: str = options.get(CONF_ENDPOINT, data.get(CONF_ENDPOINT, DEFAULT_ENDPOINT))

        # Parámetros LLM
        self.system_prompt: str = options.get(CONF_SYSTEM_PROMPT, DEFAULT_SYSTEM_PROMPT)
        self.temperature: float = float(options.get(CONF_TEMPERATURE, 0.3))
        self.top_p: float = float(options.get(CONF_TOP_P, 1.0))
        self.max_tokens: int | None = options.get(CONF_MAX_TOKENS)
        self.max_history: int = int(options.get(CONF_MAX_HISTORY, 6))
        self.timeout: int = int(options.get(CONF_TIMEOUT, 45))
        self.stream: bool = bool(options.get(CONF_STREAM, False))

        # Tools
        self.enable_tools: bool = bool(options.get(CONF_ENABLE_TOOLS, True))
        self.allowed_domains: list[str] = list(options.get(CONF_ALLOWED_DOMAINS) or [])
        self.tool_iter_limit: int = int(options.get(CONF_TOOL_ITER_LIMIT, 1))

        # Autodetección / seguimiento tools
        self.model_supports_tools: bool = bool(options.get(CONF_MODEL_SUPPORTS_TOOLS, False))
        self.force_enable_tools: bool = bool(options.get(CONF_FORCE_ENABLE_TOOLS, False))
        self.auto_tool_detect: bool = bool(options.get(CONF_AUTO_TOOL_DETECT, DEFAULT_AUTO_TOOL_DETECT))
        self.tool_follow_up_mode: str = options.get(CONF_TOOL_FOLLOW_UP_MODE, DEFAULT_TOOL_FOLLOW_UP_MODE)
        self.handshake_timeout: int = int(options.get(CONF_HANDSHAKE_TIMEOUT, DEFAULT_HANDSHAKE_TIMEOUT))

        # Cliente HTTP
        self._client = LemonadeClient(
            hass=self.hass,
            base_url=self.base_url,
            api_key=self.api_key,
            verify_ssl=self.verify_ssl,
            timeout=self.timeout,
        )

        # Memoria por conversación y cache de autodetección
        self._history: dict[str, list[dict[str, Any]]] = {}
        self._tools_supported: bool | None = self.model_supports_tools if self.auto_tool_detect else None

        _LOGGER.debug(
            "Agent init: model=%s endpoint=%s tools=%s stream=%s auto_detect=%s follow_up=%s",
            self.model,
            self.endpoint,
            self.enable_tools,
            self.stream,
            self.auto_tool_detect,
            self.tool_follow_up_mode,
        )

    @property
    def name(self) -> str:
        """Nombre mostrado en la UI de Assist."""
        return self._display_name

    @property
    def supported_languages(self) -> list[str]:
        """Lista explícita de idiomas soportados (evita problemas de frontend)."""
        return ["es", "en"]

    @property
    def attribution(self) -> dict[str, Any] | None:
        return {"name": self._display_name, "brand": "Lemonade", "url": self.base_url}

    async def _autodetect_tools(self) -> bool:
        """Intentar una llamada corta para detectar soporte de tool_calls."""
        if self.endpoint != DEFAULT_ENDPOINT:
            _LOGGER.debug("Autodetección omitida: endpoint %s no es chat/completions", self.endpoint)
            return False

        tools = build_tools_schema()
        messages = [
            {"role": "system", "content": "Eres un test. Si existen herramientas, usa 'list_areas'."},
            {"role": "user", "content": "¿Qué áreas hay?"},
        ]
        try:
            t0 = time.monotonic()
            resp = await self._client.async_chat(
                endpoint=self.endpoint,
                model=self.model,
                messages=messages,
                tools=tools,
                tool_choice="auto",
                temperature=0.0,
                top_p=1.0,
                max_tokens=64,
                stream=False,
                request_timeout=self.handshake_timeout,
            )
            dt_ms = (time.monotonic() - t0) * 1000
            tool_calls = None
            if "choices" in resp:
                msg = (resp.get("choices") or [{}])[0].get("message") or {}
                tool_calls = msg.get("tool_calls")
            supported = bool(tool_calls)
            _LOGGER.debug(
                "Autodetección tools: supported=%s en %.0f ms; resp keys=%s",
                supported,
                dt_ms,
                list(resp.keys()),
            )
            return supported
        except Exception as e:  # noqa: BLE001
            _LOGGER.debug("Autodetección tools falló: %s", e)
            return False

    async def async_process(self, user_input: ConversationInput) -> ConversationResult:
        """Procesar una entrada de conversación del pipeline de Assist."""
        response = intent.IntentResponse(language=user_input.language or "es")

        def _set_speech(resp: intent.IntentResponse, text: str) -> None:
            # Compatibilidad con distintas versiones
            if hasattr(resp, "async_set_speech_plain"):
                resp.async_set_speech_plain(text=text or "")
            elif hasattr(resp, "async_set_speech"):
                resp.async_set_speech(text or "")

        try:
            text = (user_input.text or "").strip()
            language = user_input.language or "es"
            conv_id = user_input.conversation_id or "default"
            _LOGGER.debug("Process: conv_id=%s lang=%s text=%s", conv_id, language, text)

            # Determinar si se habilitan tools (modelo + override + autodetección)
            tools_enabled_base = self.enable_tools and (self.force_enable_tools or self.model_supports_tools)
            tools_enabled = tools_enabled_base
            if tools_enabled and self.auto_tool_detect:
                if self._tools_supported is None:
                    self._tools_supported = await self._autodetect_tools()
                tools_enabled = tools_enabled and self._tools_supported

            # Preparar mensajes con memoria acotada
            messages: list[dict[str, Any]] = []
            messages.append({"role": "system", "content": self._compose_system_prompt(user_input)})
            if conv_id in self._history:
                hist = self._history[conv_id][-self.max_history * 2 :]
                messages.extend(hist)
            messages.append({"role": "user", "content": text})

            tools = build_tools_schema() if tools_enabled else None

            # Si hay tools, desactiva streaming para permitir function calling robusto
            use_stream = self.stream and not tools_enabled and self.endpoint == DEFAULT_ENDPOINT

            tool_iterations = 0
            final_text: str | None = None

            while True:
                t0 = time.monotonic()
                resp = await self._client.async_chat(
                    endpoint=self.endpoint,
                    model=self.model,
                    messages=messages,
                    tools=tools,
                    tool_choice="auto" if tools else None,
                    temperature=self.temperature,
                    top_p=self.top_p,
                    max_tokens=self.max_tokens,
                    stream=use_stream,
                )
                dt_ms = (time.monotonic() - t0) * 1000
                _LOGGER.debug(
                    "LLM call completada en %.0f ms (stream=%s, tools=%s)",
                    dt_ms,
                    use_stream,
                    bool(tools),
                )

                tool_calls = None
                assistant_text = None

                if "choices" in resp:
                    msg = (resp.get("choices") or [{}])[0].get("message") or {}
                    tool_calls = msg.get("tool_calls")
                    assistant_text = msg.get("content")
                    messages.append({"role": "assistant", "content": assistant_text or "", "tool_calls": tool_calls})

                elif "output_text" in resp:
                    assistant_text = resp.get("output_text")
                    messages.append({"role": "assistant", "content": assistant_text or ""})

                elif "response" in resp or "output" in resp:
                    response_obj = resp.get("response") or resp.get("output") or {}
                    if isinstance(response_obj, dict) and "output_text" in response_obj:
                        assistant_text = response_obj.get("output_text")
                    else:
                        assistant_text = json.dumps(resp)
                    messages.append({"role": "assistant", "content": assistant_text or ""})

                else:
                    assistant_text = json.dumps(resp)

                # Manejo de tools
                if tools and tool_calls:
                    if tool_iterations >= self.tool_iter_limit:
                        assistant_text = (assistant_text or "") + "\n[Aviso] Límite de iteraciones de herramientas."
                        final_text = assistant_text
                        break

                    # Ejecutar tool calls y decidir seguimiento
                    direct_reply: str | None = None
                    for call in tool_calls:
                        fn = call.get("function", {})
                        name = fn.get("name")
                        arguments = fn.get("arguments")
                        tool_res = await exec_tool_call(
                            self.hass,
                            name,
                            arguments,
                            allowed_domains=self.allowed_domains,
                            context=user_input.context,
                        )
                        messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": call.get("id"),
                                "name": name,
                                "content": tool_res,
                            }
                        )

                        # Modo directo para acelerar acciones y consultas simples
                        if self.tool_follow_up_mode == TOOL_FOLLOW_UP_DIRECT:
                            try:
                                parsed = json.loads(tool_res)
                            except Exception:
                                parsed = {}

                            if "error" in parsed:
                                direct_reply = self._format_error(parsed["error"])
                            elif name == "call_service":
                                direct_reply = self._format_service_ack(parsed)
                            elif name == "get_state":
                                direct_reply = self._format_get_state(parsed)
                            # Para list_areas/list_entities, si quisieras, se puede dar resumen directo

                    tool_iterations += 1

                    if self.tool_follow_up_mode == TOOL_FOLLOW_UP_DIRECT and direct_reply:
                        final_text = direct_reply
                        break

                    # Ronda extra para que el modelo integre resultados
                    use_stream = False
                    continue

                # Sin tools o sin llamadas de tool: usamos la respuesta del asistente
                final_text = assistant_text or ""
                break

            # Guardar memoria y responder
            self._append_history(conv_id, {"role": "user", "content": text})
            self._append_history(conv_id, {"role": "assistant", "content": final_text or ""})

            _set_speech(response, final_text or "")
            return ConversationResult(response=response, conversation_id=conv_id)

        except Exception as err:  # noqa: BLE001
            _LOGGER.exception("Error en LemonadeConversationAgent: %s", err)
            if hasattr(response, "async_set_error"):
                try:
                    response.async_set_error("unknown", "Ocurrió un error procesando tu solicitud")
                except Exception:
                    pass
            # Fallback siempre con speech
            try:
                response.async_set_speech_plain(text="Ocurrió un error procesando tu solicitud.")
            except Exception:
                pass
            return ConversationResult(response=response, conversation_id=user_input.conversation_id or "default")

    def _compose_system_prompt(self, user_input: ConversationInput) -> str:
        """Construir prompt de sistema con contexto temporal y de área."""
        now = dt_util.now()
        area_hint = None
        if getattr(user_input, "device_id", None):
            from homeassistant.helpers import device_registry as dr, area_registry as ar
            dr_reg = dr.async_get(self.hass)
            ar_reg = ar.async_get(self.hass)
            dev = dr_reg.async_get(user_input.device_id)
            if dev and dev.area_id:
                area = ar_reg.async_get_area(dev.area_id)
                if area:
                    area_hint = area.name

        prefix = (
            f"{self.system_prompt}\n\n"
            f"Fecha y hora actual: {now.isoformat()}.\n"
            "Hablas español de forma natural. "
            "Si necesitas ejecutar acciones, usa las herramientas definidas. "
        )
        if area_hint:
            prefix += f"Contexto: el usuario podría estar en el área '{area_hint}'. Prioriza entidades de esa área cuando haya ambigüedad.\n"
        prefix += "Antes de llamar servicios, valida que las entidades existan y estén claras. Evita acciones peligrosas salvo petición explícita.\n"
        return prefix

    def _append_history(self, conv_id: str, msg: dict[str, Any]) -> None:
        """Almacenar historial acotado por conversación."""
        hist = self._history.setdefault(conv_id, [])
        hist.append(msg)
        limit = max(2 * self.max_history, 2)
        if len(hist) > limit:
            del hist[0 : len(hist) - limit]

    # Helpers de formateo

    def _friendly_entity(self, entity_id: str) -> str:
        st = self.hass.states.get(entity_id)
        if st:
            name = st.attributes.get("friendly_name")
            if isinstance(name, str) and name:
                return name
        return entity_id

    def _format_targets(self, target) -> str:
        if not target:
            return "los objetivos indicados"
        if isinstance(target, str):
            names = [self._friendly_entity(target)]
        elif isinstance(target, list):
            names = [self._friendly_entity(e) for e in target]
        elif isinstance(target, dict) and "entity_id" in target:
            ent = target["entity_id"]
            if isinstance(ent, list):
                names = [self._friendly_entity(e) for e in ent]
            else:
                names = [self._friendly_entity(ent)]
        else:
            return "los objetivos indicados"
        if len(names) == 1:
            return names[0]
        return ", ".join(names[:-1]) + " y " + names[-1]

    def _format_service_ack(self, result: dict[str, Any]) -> str:
        domain = result.get("domain")
        service = result.get("service")
        target = result.get("target")
        data = result.get("data") or {}
        tgt_txt = self._format_targets(target)

        mapping = {
            ("light", "turn_on"): f"Encendí {tgt_txt}.",
            ("light", "turn_off"): f"Apagué {tgt_txt}.",
            ("switch", "turn_on"): f"Activé {tgt_txt}.",
            ("switch", "turn_off"): f"Desactivé {tgt_txt}.",
            ("scene", "turn_on"): f"Ejecuté la escena en {tgt_txt}.",
            ("media_player", "volume_set"): f"Ajusté el volumen de {tgt_txt} a {data.get('volume_level')}.",
            ("climate", "set_temperature"): f"Ajusté la temperatura de {tgt_txt} a {data.get('temperature')}°C.",
        }
        text = mapping.get((domain, service))
        if not text:
            text = f"Listo. Ejecuté {domain}.{service} en {tgt_txt}."
        return text

    def _format_get_state(self, result: dict[str, Any]) -> str:
        eid = result.get("entity_id")
        state = result.get("state")
        name = self._friendly_entity(eid) if isinstance(eid, str) else "la entidad"
        if state in ("on", "off"):
            friendly = "encendido" if state == "on" else "apagado"
            return f"{name} está {friendly}."
        return f"{name} está en estado '{state}'."

    def _format_error(self, message: str) -> str:
        return f"Hubo un problema al ejecutar la acción: {message}"
