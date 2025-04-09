import json
import os
from datetime import datetime, timedelta
from functools import wraps

from docx import Document
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_cors import CORS
from langchain.schema import Document as LangChainDoc
from langchain.text_splitter import RecursiveCharacterTextSplitter
from openai import OpenAI

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "supersecret")
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=3)  # Set session timeout to 3 minutes
CORS(app)

# Load chatbot configuration
import os
import yaml


def load_chatbot_config():
    # Ensure the path is correct relative to your app file
    config_path = os.path.join(os.path.dirname(__file__), 'config', 'chatbot_config.yaml')
    print("Trying to load YAML from:", config_path)

    with open(config_path, 'r', encoding='utf-8') as file:
        config_data = yaml.safe_load(file)

    chatbots = config_data.get("chatbots", {})


    # Get the environment variable, defaulting to "default"
    selected_chatbot = os.getenv("CHATBOT_NAME", "default").strip()

    # If not found by key, try searching by the chatbot's "name" field
    for key, config in chatbots.items():
        if config.get("name") == selected_chatbot:
            # Look up the configuration within the "chatbots" dictionary
            chosen_config = config
            break


    print("chosen_config:", chosen_config)


    if not chosen_config:
        # Log a warning and fallback to default if the selected key isn't found
        chosen_config = config_data.get("chatbots", {}).get("default", {})

    return chosen_config


# Example of calling the function:
chatbot_config = load_chatbot_config()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_email' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# --- Load external content from .docx ---
def load_docx(path: str):
    try:
        doc = Document(path)
        full_text = "\n".join([para.text for para in doc.paragraphs if para.text.strip() != ""])
        return LangChainDoc(page_content=full_text)
    except Exception as e:
        print(f"Error loading document: {e}")
        # Return a default document with some basic information
        return LangChainDoc(page_content="This is a default reference text. The actual document could not be loaded.")

# Load and optionally chunk the .docx file
docx_file = os.getenv("DOCX_FILE_PATH", "default_document.docx")

pdn_doc = load_docx(docx_file)

# Optional: split if needed for large files
splitter = RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=200)
doc_chunks = splitter.split_documents([pdn_doc])
# Take top 1–2 chunks if needed (can be improved with retrieval later)
reference_text = "\n\n".join([chunk.page_content for chunk in doc_chunks[:2]])

# Get the prompt file path from an environment variable
prompt_file = os.getenv("BUDDY_PROMPT_FILE", "prompts/buddy_prompt.txt")

# Read the prompt from the specified file
with open(prompt_file, "r", encoding="utf-8") as f:
    base_prompt = f.read().strip()

SYSTEM_PROMPT = f"""{base_prompt}

להלן מידע נוסף :

{reference_text}
"""

# Chat history per session
conversation_history = {}

def get_session_id():
    if 'session_id' not in session:
        session['session_id'] = os.urandom(8).hex()
        print(f"\n🆕 New session created: {session['session_id']}")
    else:
        print(f"\n📝 Using existing session: {session['session_id']}")
    return session['session_id']

def generate_response(user_message):
    session_id = get_session_id()

    if session_id not in conversation_history:
        conversation_history[session_id] = [{"role": "system", "content": SYSTEM_PROMPT}]
        print(f"\n📚 Initialized conversation history for session: {session_id}")
    else:
        print(f"\n📖 Retrieved existing conversation history for session: {session_id}")

    history = conversation_history[session_id]
    history.append({"role": "user", "content": user_message})

    print("\n📥 Prompt sent to GPT:\n----------------------")
    print(json.dumps(history, indent=2, ensure_ascii=False))

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=history,
            temperature=0.7
        )
        bot_reply = response.choices[0].message.content.strip()
        history.append({"role": "assistant", "content": bot_reply})
    except Exception as e:
        bot_reply = f"I'm sorry, I encountered an error: {e}"

    return bot_reply

@app.before_request
def before_request():
    if 'user_email' in session:
        # Check if session is expired
        if 'last_activity' in session:
            last_activity = datetime.fromisoformat(session['last_activity'])
            if datetime.now() - last_activity > app.config['PERMANENT_SESSION_LIFETIME']:
                session.clear()
                return redirect(url_for('login'))
        # Update last activity time
        session['last_activity'] = datetime.now().isoformat()

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        
        if password == os.getenv('USER_PASSWORD'):
            session['user_email'] = email
            session['last_activity'] = datetime.now().isoformat()
            return redirect(url_for('index'))
        else:
            return render_template("login.html", error="Invalid credentials", chatbot_config=chatbot_config)
    
    return render_template("login.html", chatbot_config=chatbot_config)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route("/")
@login_required
def index():
    return render_template("index.html", chatbot_config=chatbot_config)

@app.route("/chat", methods=["POST"])
@login_required
def chat():
    data = request.get_json()
    user_message = data.get("message", "")
    if user_message.lower() in ["exit", "quit", "bye"]:
        session_id = get_session_id()
        conversation_history.pop(session_id, None)
        return jsonify({"response": "Goodbye!"})
    response = generate_response(user_message)
    return jsonify({"response": response})

@app.route("/session-status", methods=["GET"])
@login_required
def session_status():
    session_id = get_session_id()
    return jsonify({
        "session_id": session_id,
        "has_history": session_id in conversation_history,
        "history_length": len(conversation_history.get(session_id, []))
    })

@app.route('/check_session')
def check_session():
    if 'user_email' in session and 'last_activity' in session:
        last_activity = datetime.fromisoformat(session['last_activity'])
        if datetime.now() - last_activity > app.config['PERMANENT_SESSION_LIFETIME']:
            session.clear()
            return jsonify({'status': 'expired'})
        return jsonify({'status': 'active'})
    return jsonify({'status': 'expired'})

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5001, debug=True)
