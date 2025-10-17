from __future__ import annotations

import time
from typing import Any, List, Dict

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store


class ICLStore:
    """Almacenamiento simple de ejemplos ICL por entry."""

    def __init__(self, hass: HomeAssistant, entry_id: str, *, max_store: int = 200) -> None:
        self.hass = hass
        self.entry_id = entry_id
        self.max_store = max_store
        self._store = Store(hass, 1, f"lemonade_conversation_icl_{entry_id}.json")
        self._loaded = False
        self._data: dict[str, Any] = {"examples": []}

    async def async_ensure_loaded(self) -> None:
        if self._loaded:
            return
        data = await self._store.async_load()
        if isinstance(data, dict) and "examples" in data and isinstance(data["examples"], list):
            self._data = data
        self._loaded = True

    async def async_add_example(
        self,
        *,
        user_text: str,
        assistant_text: str,
        tools_used: list[str] | None = None,
        tags: list[str] | None = None,
    ) -> None:
        await self.async_ensure_loaded()
        ex = {
            "ts": time.time(),
            "user": user_text,
            "assistant": assistant_text,
            "tools": tools_used or [],
            "tags": tags or [],
        }
        self._data["examples"].append(ex)
        # recortar
        if len(self._data["examples"]) > self.max_store:
            self._data["examples"] = self._data["examples"][-self.max_store :]
        await self._store.async_save(self._data)

    async def async_clear(self) -> None:
        self._data = {"examples": []}
        await self._store.async_save(self._data)

    async def async_get_examples(self, query_text: str, k: int) -> list[dict[str, str]]:
        """Retorna hasta k ejemplos. Estrategia simple: más recientes.
        Si querés algo mejor, se puede hacer keyword overlap sin dependencias.
        """
        await self.async_ensure_loaded()
        exs = list(self._data.get("examples", []))
        exs.sort(key=lambda e: e.get("ts", 0), reverse=True)
        # devolver como pares chat-style
        out: list[dict[str, str]] = []
        for e in exs[: max(k, 0)]:
            u = str(e.get("user", "")).strip()
            a = str(e.get("assistant", "")).strip()
            if u and a:
                out.append({"user": u, "assistant": a})
        return out
