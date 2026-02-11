import os

# LLM server settings (Ollama OpenAI-compatible API)
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://127.0.0.1:11434/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY", "ollama")
LLM_MODEL = os.getenv("LLM_MODEL", "dolphin-mistral")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.7"))
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "512"))

# App settings
APP_HOST = os.getenv("APP_HOST", "127.0.0.1")
APP_PORT = int(os.getenv("APP_PORT", "8080"))
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
PROGRESS_FILE = os.path.join(DATA_DIR, "progress.json")
