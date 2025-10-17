from __future__ import annotations

import json
from typing import Any

from homeassistant.core import HomeAssistant, Context
from homeassistant.const import ATTR_FRIENDLY_NAME
from homeassistant.helpers import area_registry as ar, device_registry as dr, entity_registry as er


def build_tools_schema() -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": "list_areas",
                "description": "Lista las áreas definidas en Home Assistant.",
                "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "list_entities",
                "description": "Lista entidades con área, dominio, friendly_name y estado.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "domain": {"type": "string", "description": "Filtra por dominio (light, switch, climate, etc.)."},
                        "area": {"type": "string", "description": "Nombre o ID de área para filtrar (opcional)."}
                    },
                    "additionalProperties": False,
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_state",
                "description": "Obtiene el estado y atributos de una entidad.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "entity_id": {"type": "string", "description": "ID de entidad (ej.: light.cocina)"},
                    },
                    "required": ["entity_id"],
                    "additionalProperties": False,
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "call_service",
                "description": "Llama un servicio de Home Assistant sobre entidades o áreas específicas.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "domain": {"type": "string", "description": "Ej.: light, switch, climate."},
                        "service": {"type": "string", "description": "Ej.: turn_on, turn_off, set_temperature."},
                        "entity_id": {"type": "string", "description": "Una entidad o lista separada por comas"},
                        "area_id": {"type": "string", "description": "Area id si aplica"},
                        "area_name": {"type": "string", "description": "Nombre de área (se convertirá a area_id)"},
                        "device_id": {"type": "string", "description": "Device id si aplica"},
                        "data": {"type": "object", "description": "Datos adicionales del servicio"},
                    },
                    "required": ["domain", "service"],
                    "additionalProperties": False,
                },
            },
        },
    ]


def _is_domain_allowed(domain: str, allowed_domains: list[str]) -> bool:
    return domain in allowed_domains


def _split_entities(value: str | None) -> list[str]:
    if not value:
        return []
    return [v.strip() for v in value.split(",") if v.strip()]


async def exec_tool_call(
    hass: HomeAssistant,
    tool_name: str,
    arguments_json: str | dict[str, Any] | None,
    *,
    allowed_domains: list[str],
    context: Context | None = None,
) -> str:
    try:
        args = json.loads(arguments_json) if isinstance(arguments_json, str) else (arguments_json or {})
    except Exception:
        args = {}

    er_reg = er.async_get(hass)
    ar_reg = ar.async_get(hass)
    dr_reg = dr.async_get(hass)

    if tool_name == "list_areas":
        areas = [{"area_id": a.id, "name": a.name} for a in ar_reg.async_list_areas()]
        return json.dumps({"areas": areas}, ensure_ascii=False)

    if tool_name == "list_entities":
        domain_filter = args.get("domain")
        area_filter = args.get("area")
        area_id_filter = None

        if isinstance(area_filter, str) and area_filter:
            area_obj = ar_reg.async_get_area(area_filter)
            if area_obj:
                area_id_filter = area_obj.id
            else:
                for a in ar_reg.async_list_areas():
                    if a.name.lower() == area_filter.lower():
                        area_id_filter = a.id
                        break

        items = []
        for ent in er_reg.entities.values():
            if ent.disabled_by:
                continue
            if domain_filter and ent.domain != domain_filter:
                continue
            state = hass.states.get(ent.entity_id)
            if state is None:
                continue

            ent_area_id = ent.area_id
            if not ent_area_id and ent.device_id:
                device = dr_reg.async_get(ent.device_id)
                if device and device.area_id:
                    ent_area_id = device.area_id

            if area_id_filter and ent_area_id != area_id_filter:
                continue

            area_name = None
            if ent_area_id:
                area = ar_reg.async_get_area(ent_area_id)
                area_name = area.name if area else None

            items.append(
                {
                    "entity_id": ent.entity_id,
                    "domain": ent.domain,
                    "area": area_name,
                    "friendly_name": state.attributes.get(ATTR_FRIENDLY_NAME),
                    "state": state.state,
                }
            )
        return json.dumps({"entities": items}, ensure_ascii=False)

    if tool_name == "get_state":
        entity_id = args.get("entity_id")
        if not isinstance(entity_id, str):
            return json.dumps({"error": "entity_id requerido"})
        st = hass.states.get(entity_id)
        if st is None:
            return json.dumps({"error": f"Entidad no encontrada: {entity_id}"}, ensure_ascii=False)
        return json.dumps(
            {"entity_id": entity_id, "state": st.state, "attributes": st.attributes}, ensure_ascii=False
        )

    if tool_name == "call_service":
        domain = args.get("domain")
        service = args.get("service")
        entity_id = args.get("entity_id")
        area_id = args.get("area_id")
        area_name = args.get("area_name")
        device_id = args.get("device_id")
        data = args.get("data") or {}

        if not domain or not service:
            return json.dumps({"error": "domain y service son requeridos"}, ensure_ascii=False)

        if not _is_domain_allowed(domain, allowed_domains):
            return json.dumps({"error": f"Dominio no permitido: {domain}"}, ensure_ascii=False)

        if area_name and not area_id:
            found = None
            for a in ar_reg.async_list_areas():
                if a.name.lower() == str(area_name).lower():
                    found = a
                    break
            if found:
                area_id = found.id

        target: dict[str, Any] | None = None
        entity_ids = _split_entities(entity_id)
        if entity_ids or area_id or device_id:
            target = {}
            if entity_ids:
                target["entity_id"] = entity_ids if len(entity_ids) > 1 else entity_ids[0]
            if area_id:
                target["area_id"] = area_id
            if device_id:
                target["device_id"] = device_id

        await hass.services.async_call(domain, service, data, blocking=True, target=target, context=context)
        return json.dumps({"result": "ok", "domain": domain, "service": service, "target": target, "data": data}, ensure_ascii=False)

    return json.dumps({"error": f"Tool no soportada: {tool_name}"}, ensure_ascii=False)
