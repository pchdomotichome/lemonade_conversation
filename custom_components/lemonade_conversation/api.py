from __future__ import annotations

import json
from typing import Any, Dict, List

from aiohttp import ClientSession, ClientTimeout
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import ENDPOINT_CHAT, ENDPOINT_RESPONSES, ENDPOINT_COMPLETIONS


class LemonadeClient:
    def __init__(
        self,
        hass: HomeAssistant,
        base_url: str,
        api_key: str | None = None,
        verify_ssl: bool = True,
        timeout: int = 45,
    ) -> None:
        self.hass = hass
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or ""
        self.verify_ssl = verify_ssl
        self.timeout = timeout

    @property
    def _headers(self) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _session(self) -> ClientSession:
        return async_get_clientsession(self.hass, verify_ssl=self.verify_ssl)

    async def async_list_models(self) -> list[str]:
        url = f"{self.base_url}/models"
        async with self._session().get(url, headers=self._headers, timeout=ClientTimeout(total=15)) as resp:
            resp.raise_for_status()
            data = await resp.json()
        models: list[str] = []
        if isinstance(data, dict) and "data" in data and isinstance(data["data"], list):
            for item in data["data"]:
                mid = item.get("id")
                if isinstance(mid, str):
                    models.append(mid)
        if not models and isinstance(data, list):
            models = [str(m) for m in data]
        return models

    async def async_list_models_detailed(self) -> List[Dict[str, str]]:
        """Devuelve lista de modelos con id y recipe para mostrar en selector."""
        url = f"{self.base_url}/models"
        async with self._session().get(url, headers=self._headers, timeout=ClientTimeout(total=15)) as resp:
            resp.raise_for_status()
            data = await resp.json()
        models: List[Dict[str, str]] = []
        if isinstance(data, dict) and "data" in data and isinstance(data["data"], list):
            for item in data["data"]:
                mid = item.get("id")
                recipe = item.get("recipe", "unknown")
                if isinstance(mid, str):
                    models.append({"id": mid, "recipe": recipe})
        if not models and isinstance(data, list):
            models = [{"id": str(m), "recipe": "unknown"} for m in data]
        return models

    async def async_chat(
        self,
        *,
        endpoint: str,
        model: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | dict[str, Any] | None = None,
        temperature: float = 0.3,
        top_p: float = 1.0,
        max_tokens: int | None = None,
        stream: bool = False,
        request_timeout: int | None = None,
    ) -> dict[str, Any]:
        timeout = ClientTimeout(total=request_timeout or self.timeout)

        if endpoint == ENDPOINT_RESPONSES:
            url = f"{self.base_url}/responses"
            payload: dict[str, Any] = {
                "model": model,
                "input": messages,
                "temperature": temperature,
                "top_p": top_p,
            }
            if tools:
                payload["tools"] = tools
            if tool_choice is not None:
                payload["tool_choice"] = tool_choice
            if max_tokens is not None:
                payload["max_output_tokens"] = max_tokens

            async with self._session().post(url, headers=self._headers, json=payload, timeout=timeout) as resp:
                resp.raise_for_status()
                return await resp.json()

        if endpoint == ENDPOINT_COMPLETIONS:
            url = f"{self.base_url}/completions"
            prompt = "\n".join(f"{m.get('role','user').upper()}: {m.get('content','')}" for m in messages)
            payload = {"model": model, "prompt": prompt, "temperature": temperature, "top_p": top_p}
            if max_tokens is not None:
                payload["max_tokens"] = max_tokens

            async with self._session().post(url, headers=self._headers, json=payload, timeout=timeout) as resp:
                resp.raise_for_status()
                data = await resp.json()
                text = data.get("choices", [{}])[0].get("text", "")
                return {"choices": [{"message": {"content": text}}]}

        url = f"{self.base_url}/chat/completions"
        payload: dict[str, Any] = {
            "model": model,
            "temperature": temperature,
            "top_p": top_p,
            "messages": messages,
        }
        if tools:
            payload["tools"] = tools
        if tool_choice is not None:
            payload["tool_choice"] = tool_choice
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        if stream:
            payload["stream"] = True

        if not stream:
            async with self._session().post(url, headers=self._headers, json=payload, timeout=timeout) as resp:
                resp.raise_for_status()
                return await resp.json()

        assistant_text = ""
        async with self._session().post(url, headers=self._headers, json=payload, timeout=timeout) as resp:
            resp.raise_for_status()
            async for raw_line in resp.content:
                if not raw_line:
                    continue
                try:
                    line = raw_line.decode("utf-8").strip()
                except Exception:
                    continue
                if not line.startswith("data:"):
                    continue
                data_str = line[5:].strip()
                if not data_str or data_str == "[DONE]":
                    continue
                try:
                    chunk = json.loads(data_str)
                except Exception:
                    continue
                choices = chunk.get("choices") or []
                if not choices:
                    continue
                delta = choices[0].get("delta") or {}
                assistant_text += delta.get("content") or ""

        return {"choices": [{"message": {"content": assistant_text}}]}
