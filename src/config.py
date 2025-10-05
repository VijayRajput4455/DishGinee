# --- Directories ---
UPLOAD_DIR = "images"
LOG_DIR = "logs"
LOG_FILE = "dishgenie.log" 


# --- Detection Configuration ---
CONF_THRESHOLD: float = 0.5


# --- LLM Configuration ---
OLLAMA_ENDPOINT = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.2:latest"


# Model file path
MODEL_PATH = "models/Veg_best.pt"