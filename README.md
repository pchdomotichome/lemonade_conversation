# Lemonade Conversation for Home Assistant

Integración personalizada que permite conectar Home Assistant con tu servidor local Lemonade, compatible con OpenAI API.

## Características

- ✅ Comunicación con Lemonade Server local
- ✅ Soporte para múltiples agentes
- ✅ Historial de conversaciones
- ✅ Plantillas avanzadas de prompts
- ✅ Detección automática de idioma
- ✅ Soporte completo para Tool Calling
- ✅ Compatible con HACS

## Instalación

### Via HACS (recomendado)

1. Añade este repositorio como custom repository en HACS
2. Busca "Lemonade Conversation" e instálalo
3. Reinicia Home Assistant
4. Ve a Settings > Devices & Services > Add Integration > Lemonade Conversation

### Manual

1. Descarga el ZIP
2. Extrae en `<config>/custom_components/lemonade_conversation/`
3. Reinicia Home Assistant
4. Configura desde la UI

## Configuración

Necesitarás:
- URL base de tu servidor Lemonade (ej: `http://192.168.1.100:8765`)
- API Key (si requiere autenticación)
- Modelo a utilizar (por defecto `gpt-3.5-turbo`)

## Licencia

MIT