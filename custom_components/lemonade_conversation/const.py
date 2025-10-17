DOMAIN = "lemonade_conversation"

# Conexión
CONF_BASE_URL = "base_url"
CONF_API_KEY = "api_key"
CONF_VERIFY_SSL = "verify_ssl"

# Endpoints OpenAI-compatibles
CONF_ENDPOINT = "endpoint"
ENDPOINT_CHAT = "chat_completions"
ENDPOINT_RESPONSES = "responses"
ENDPOINT_COMPLETIONS = "completions"
DEFAULT_ENDPOINT = ENDPOINT_CHAT

# Modelo
CONF_MODEL = "model"

# Parámetros del agente / LLM
CONF_AGENT_NAME = "agent_name"
CONF_SYSTEM_PROMPT = "system_prompt"
CONF_TEMPERATURE = "temperature"
CONF_TOP_P = "top_p"
CONF_MAX_TOKENS = "max_tokens"
CONF_MAX_HISTORY = "max_history"
CONF_TIMEOUT = "timeout"
CONF_STREAM = "stream"
CONF_REFRESH_SYSTEM_EVERY_TURN = "refresh_system_every_turn"

# Tools / seguridad
CONF_ENABLE_TOOLS = "enable_tools"
CONF_ALLOWED_DOMAINS = "allowed_domains"
CONF_TOOL_ITER_LIMIT = "tool_iteration_limit"
CONF_TOOL_FOLLOW_UP_MODE = "tool_follow_up_mode"
TOOL_FOLLOW_UP_LLM = "llm"
TOOL_FOLLOW_UP_DIRECT = "direct"

# Control mode (inspirado en home-llm)
CONF_CONTROL_MODE = "control_mode"
CONTROL_MODE_NONE = "none"          # sin control (charla)
CONTROL_MODE_ASSIST = "assist"      # deja control al pipeline local si aplica
CONTROL_MODE_LLM = "llm_tools"      # tools desde el LLM
DEFAULT_CONTROL_MODE = CONTROL_MODE_LLM

# Estado manual del soporte de tools por modelo
CONF_MODEL_SUPPORTS_TOOLS = "model_supports_tools"

# ICL (few-shot dinámico)
CONF_ENABLE_ICL = "enable_icl"
CONF_ICL_MAX_EXAMPLES = "icl_max_examples"
CONF_ICL_AUTO_CAPTURE = "icl_auto_capture"
CONF_ICL_CLEAR = "icl_clear"  # acción: borrar ejemplos almacenados

# Defaults
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
DEFAULT_REFRESH_SYSTEM_EVERY_TURN = True

# Dominios permitidos por defecto
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
DEFAULT_TOOL_ITER_LIMIT = 1
DEFAULT_TOOL_FOLLOW_UP_MODE = TOOL_FOLLOW_UP_DIRECT

# Control mode
DEFAULT_CONTROL_MODE = CONTROL_MODE_LLM

# ICL defaults
DEFAULT_ENABLE_ICL = False
DEFAULT_ICL_MAX_EXAMPLES = 4
DEFAULT_ICL_AUTO_CAPTURE = False
