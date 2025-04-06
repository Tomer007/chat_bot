from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from openai import OpenAI
from dotenv import load_dotenv
import os
import json
from docx import Document
from langchain.schema import Document as LangChainDoc
from langchain.text_splitter import RecursiveCharacterTextSplitter
from functools import wraps

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "supersecret")

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

# Load base system prompt and inject .docx context
with open("buddy_budge.txt", "r") as f:
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

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        
        if password == "Tomer":
            session['user_email'] = email
            return redirect(url_for('index'))
        else:
            return render_template("login.html", error="סיסמה שגויה. אנא נסה שוב.")
    
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop('user_email', None)
    return redirect(url_for('login'))

@app.route("/")
@login_required
def index():
    return render_template("index.html")

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

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5001, debug=True)
