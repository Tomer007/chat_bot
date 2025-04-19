import os

from flask import Flask, session, redirect, url_for
from flask_session import Session

# Get the absolute path to the root directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

app = Flask(__name__,
            template_folder=os.path.join(BASE_DIR, 'templates'),
            static_folder=os.path.join(BASE_DIR, 'static'))

# Basic configuration
app.config.update(
    SECRET_KEY='dev',
    DEBUG=True,
    SESSION_TYPE='filesystem',
    SESSION_FILE_DIR=os.path.join(BASE_DIR, 'sessions'),
    SESSION_FILE_THRESHOLD=500,  # Maximum number of sessions stored
    SESSION_FILE_MODE=0o600,  # File permission
    SESSION_FILE_EXTENSION='.txt'  # Use .txt extension
)

# Initialize session
os.makedirs(app.config['SESSION_FILE_DIR'], exist_ok=True)
Session(app)

# Import and register blueprints
from app.routes import auth_bp, chat_bp

app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(chat_bp, url_prefix='/chat')


# Root routes
@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    return redirect(url_for('chat.index'))


@app.route('/login')
def login_redirect():
    return redirect(url_for('auth.login'))


def run_app():
    """Run the Flask application"""
    app.run(host='0.0.0.0', port=5000)
