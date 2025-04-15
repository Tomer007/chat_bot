import os
import yaml
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Base directory of the application
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Directory paths
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
STATIC_FOLDER = os.path.join(BASE_DIR, 'static')
TEMPLATE_FOLDER = os.path.join(BASE_DIR, 'templates')
LOG_FOLDER = os.path.join(BASE_DIR, 'logs')
PROMPTS_FOLDER = os.path.join(BASE_DIR, 'prompts')
ASSESSMENT_RESULTS_FOLDER = os.path.join(BASE_DIR, 'assessment_results')

# Create necessary directories if they don't exist
for directory in [UPLOAD_FOLDER, LOG_FOLDER, ASSESSMENT_RESULTS_FOLDER]:
    os.makedirs(directory, exist_ok=True)

# Flask configuration
DEBUG = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
PORT = int(os.getenv('FLASK_PORT', 5000))
SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'your-secret-key-here')

# Session configuration
SESSION_TYPE = 'filesystem'
SESSION_FILE_DIR = os.path.join(BASE_DIR, 'sessions')
SESSION_PERMANENT = True
PERMANENT_SESSION_LIFETIME = timedelta(days=int(os.getenv('SESSION_LIFETIME_DAYS', 7)))
SESSION_COOKIE_SECURE = True  # Only send cookie over HTTPS
SESSION_COOKIE_HTTPONLY = True  # Prevent JavaScript access to session cookie
SESSION_COOKIE_SAMESITE = 'Strict'  # Prevent CSRF
SESSION_REFRESH_EACH_REQUEST = True  # Update session on each request

# Create sessions directory if it doesn't exist
os.makedirs(SESSION_FILE_DIR, exist_ok=True)

# OpenAI configuration
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4')
TEMPERATURE = float(os.getenv('TEMPERATURE', 0.7))

# Security configuration
MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))  # 16MB max file size
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'doc', 'docx'}

# Load additional configuration from YAML if exists
config_path = os.path.join(BASE_DIR, 'config', 'config.yaml')
if os.path.exists(config_path):
    with open(config_path, 'r') as f:
        yaml_config = yaml.safe_load(f)
        globals().update(yaml_config)

# Export all variables
__all__ = [
    'BASE_DIR',
    'UPLOAD_FOLDER',
    'STATIC_FOLDER',
    'TEMPLATE_FOLDER',
    'LOG_FOLDER',
    'PROMPTS_FOLDER',
    'ASSESSMENT_RESULTS_FOLDER',
    'DEBUG',
    'PORT',
    'SECRET_KEY',
    'PERMANENT_SESSION_LIFETIME',
    'SESSION_TYPE',
    'SESSION_FILE_DIR',
    'OPENAI_API_KEY',
    'OPENAI_MODEL',
    'TEMPERATURE',
    'MAX_CONTENT_LENGTH',
    'ALLOWED_EXTENSIONS'
]

# Flask app configuration
SESSION_LIFETIME_SECONDS = int(os.environ.get('SESSION_LIFETIME', 3600))  # Default to 1 hour
SESSION_LIFETIME = timedelta(seconds=SESSION_LIFETIME_SECONDS)

# Document paths
RAG_FILE = os.getenv("RAG_FILE", "doc/rag_content.txt")

# Chatbot configuration
def load_chatbot_config():
    # Try multiple possible locations for the config file
    possible_paths = [
        os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'chatbot_config.yaml'),
        os.path.join(os.path.dirname(os.path.dirname(__file__)), 'chatbot_config.yaml'),
        'config/chatbot_config.yaml',
        'chatbot_config.yaml'
    ]
    
    config_path = None
    for path in possible_paths:
        if os.path.exists(path):
            config_path = path
            break
    
    if not config_path:
        print(f"Warning: Could not find chatbot_config.yaml in any of the expected locations")
        return {"name": "Default Chat Bot", "description": "A default chatbot configuration"}

    with open(config_path, 'r', encoding='utf-8') as file:
        config_data = yaml.safe_load(file)

    chatbots = config_data.get("chatbots", {})

    # Get the environment variable, defaulting to "default"
    selected_chatbot = os.getenv("CHATBOT_NAME", "default").strip()
    chosen_config = None

    # If not found by key, try searching by the chatbot's "name" field
    for key, config in chatbots.items():
        if config.get("name") == selected_chatbot:
            # Look up the configuration within the "chatbots" dictionary
            chosen_config = config
            break

    if not chosen_config:
        # Log a warning and fallback to default if the selected key isn't found
        chosen_config = config_data.get("chatbots", {}).get("default", {})

    return chosen_config

# Load chatbot configuration
CHATBOT_CONFIG = load_chatbot_config()

class Config:
    """Base configuration class."""
    # Flask configuration
    SECRET_KEY = SECRET_KEY
    DEBUG = DEBUG
    
    # OpenAI API configuration
    OPENAI_API_KEY = OPENAI_API_KEY
    
    # Flask-Session configuration
    SESSION_TYPE = 'filesystem'  # Store sessions in the filesystem
    SESSION_PERMANENT = True
    PERMANENT_SESSION_LIFETIME = SESSION_LIFETIME
    SESSION_FILE_DIR = SESSION_FILE_DIR
    SESSION_USE_SIGNER = True  # Sign the session cookie
    
    # Ensure session directory exists
    os.makedirs(SESSION_FILE_DIR, exist_ok=True)

class TestConfig(Config):
    """Test configuration class."""
    TESTING = True
    DEBUG = True
    
    # Use in-memory server for testing
    SESSION_TYPE = 'redis'  # Use Redis for tests
    SESSION_REDIS = 'redis://localhost:6379/0' 