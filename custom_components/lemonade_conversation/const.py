DOMAIN = "lemonade_conversation"

# Conexión
CONF_BASE_URL = "base_url"
CONF_API_KEY = "api_key"
CONF_VERIFY_SSL = "verify_ssl"

# Selección de endpoint OpenAI compatible
CONF_ENDPOINT = "endpoint"
ENDPOINT_CHAT = "chat_completions"
ENDPOINT_RESPONSES = "responses"
ENDPOINT_COMPLETIONS = "completions"
DEFAULT_ENDPOINT = ENDPOINT_CHAT

# Modelo
CONF_MODEL = "model"

# Opciones LLM
CONF_AGENT_NAME = "agent_name"
CONF_SYSTEM_PROMPT = "system_prompt"
CONF_TEMPERATURE = "temperature"
CONF_TOP_P = "top_p"
CONF_MAX_TOKENS = "max_tokens"
CONF_MAX_HISTORY = "max_history"
CONF_TIMEOUT = "timeout"
CONF_STREAM = "stream"

# Tools / seguridad
CONF_ENABLE_TOOLS = "enable_tools"
CONF_ALLOWED_DOMAINS = "allowed_domains"
CONF_TOOL_ITER_LIMIT = "tool_iteration_limit"

DEFAULT_AGENT_NAME = "Lemonade Assistant"
DEFAULT_SYSTEM_PROMPT = (
    "Eres un asistente útil para Home Assistant. "
    "Puedes hablar de forma natural y, cuando corresponda, usar herramientas para: "
    "listar áreas y entidades disponibles, consultar el estado de dispositivos y "
    "llamar servicios de Home Assistant (encender luces, ajustar temperatura, etc.). "
    "Sé claro, conciso y seguro. Si no tienes suficiente contexto, pide aclaraciones. "
    "Cuando llames servicios, confirma el objetivo y evita acciones peligrosas."
)

DEFAULT_TEMPERATURE = 0.3
DEFAULT_TOP_P = 1.0
DEFAULT_MAX_TOKENS = 512
DEFAULT_MAX_HISTORY = 6
DEFAULT_TIMEOUT = 45
DEFAULT_STREAM = False

# Dominios permitidos por defecto (ajustables desde opciones)
DEFAULT_ALLOWED_DOMAINS = [
    "light",
    "switch",
    "climate",
    "fan",
    "cover",
    "media_player",
    "scene",
    "script",
    "button",
    "input_boolean",
    "vacuum",
    "lock"
]

DEFAULT_ENABLE_TOOLS = True
DEFAULT_TOOL_ITER_LIMIT = 4
