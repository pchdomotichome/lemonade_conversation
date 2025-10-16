DOMAIN = "lemonade_conversation"
CONF_BASE_URL = "base_url"
CONF_API_KEY = "api_key"
CONF_MODEL = "model"
CONF_PROMPT_TEMPLATE = "prompt_template"
CONF_MAX_TOKENS = "max_tokens"
CONF_TEMPERATURE = "temperature"
CONF_TOOLS_ENABLED = "tools_enabled"

DEFAULT_MODEL = "gpt-3.5-turbo"
DEFAULT_MAX_TOKENS = 256
DEFAULT_TEMPERATURE = 0.7
DEFAULT_PROMPT_TEMPLATE = """You are a helpful and concise home assistant.
The user is speaking {{ language }}.
Current context from Home Assistant:
{%- for state in states.sensor -%}
  {%- if loop.index < 10 %}
    {{ state.name }}: {{ state.state }} {{ state.attributes.unit_of_measurement or '' }}
  {%- endif -%}
{%- endfor %}

User: {{ user_input }}
Assistant:"""
