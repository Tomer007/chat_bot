import os
import yaml
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Flask app configuration
SECRET_KEY = os.getenv("SECRET_KEY", "supersecret")
SESSION_LIFETIME = timedelta(minutes=5)
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
PORT = int(os.getenv("PORT", 5001))

# OpenAI API configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4")
TEMPERATURE = float(os.getenv("TEMPERATURE", 0.7))

# Document paths
DOCX_FILE_PATH = os.getenv("DOCX_FILE_PATH", "doc/rag_content.txt")
PROMPT_FILE = os.getenv("BUDDY_PROMPT_FILE", "prompts/buddy_prompt.txt")

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