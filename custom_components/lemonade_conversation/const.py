DOMAIN = "lemonade_conversation"
CONF_BASE_URL = "base_url"
CONF_API_KEY = "api_key"
CONF_MODEL = "model"
CONF_PROMPT_TEMPLATE = "prompt_template"
CONF_MAX_TOKENS = "max_tokens"
CONF_TEMPERATURE = "temperature"
CONF_TOOLS_ENABLED = "tools_enabled"

DEFAULT_MODEL = "gpt-3.5-turbo"
DEFAULT_NAME = "Lemonade Assistant"
DEFAULT_MAX_TOKENS = 150
DEFAULT_TEMPERATURE = 0.7
DEFAULT_PROMPT_TEMPLATE = """Eres un asistente inteligente para el hogar. Responde de forma clara y concisa.
Contexto actual:
{%- for state in states.sensor -%}
{{ state.name }}: {{ state.state }} {{ state.attributes.unit_of_measurement or '' }}
{%- endfor %}

Usuario: {{ user_input }}
Asistente:"""