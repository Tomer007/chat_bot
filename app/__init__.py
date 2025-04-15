import os
from flask import Flask, request, session, redirect, url_for
from dotenv import load_dotenv
from flask_session import Session

from app.config import SECRET_KEY, DEBUG, PORT, Config

def create_app(config_class=Config):
    """Create and configure the Flask application"""
    # Load environment variables
    load_dotenv()
    
    # Create Flask app
    app = Flask(__name__, 
                template_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates'),
                static_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static'))
    
    # Basic configuration
    app.secret_key = SECRET_KEY
    app.config['DEBUG'] = DEBUG
    
    # Simple session config
    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['SESSION_FILE_DIR'] = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'sessions')
    os.makedirs(app.config['SESSION_FILE_DIR'], exist_ok=True)
    
    # Initialize session
    Session(app)
    
    # Register blueprints
    from app.routes.chat import chat_bp
    from app.routes.auth import auth_bp
    
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(chat_bp, url_prefix='/chat')
    
    # Root route
    @app.route('/')
    def index():
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        return redirect(url_for('chat.index'))
    
    # Redirect /login to /auth/login for convenience
    @app.route('/login')
    def login_redirect():
        return redirect(url_for('auth.login'))
    
    return app

# Create the application instance
app = create_app()

def run_app():
    """Run the Flask application"""
    app.run(host='0.0.0.0', port=PORT, debug=DEBUG)
