import os
import time
import traceback
from flask import Flask, g, request, session, current_app
from flask_cors import CORS
from dotenv import load_dotenv

from app.config import SECRET_KEY, SESSION_LIFETIME, DEBUG, PORT
from app.routes import register_blueprints
from app.utils.logging_config import logger, generate_request_id

def create_app(test_config=None):
    """Create and configure the Flask application"""
    # Load environment variables
    load_dotenv()
    
    # Log startup information - outside of request context
    logger.info("Starting Chat+Bot application")
    
    # Create Flask app
    app = Flask(__name__, 
                template_folder='../templates',
                static_folder='../static')
    
    # Configure app
    app.secret_key = SECRET_KEY
    app.config['PERMANENT_SESSION_LIFETIME'] = SESSION_LIFETIME
    app.config['DEBUG'] = DEBUG
    
    logger.info(f"App configured with DEBUG={DEBUG}")
    
    # Enable CORS
    CORS(app)
    
    # Add request logging middleware
    @app.before_request
    def before_request():
        # Skip for static files
        if request.path.startswith('/static'):
            return
            
        # Assign a unique request ID
        g.request_id = generate_request_id()
        g.start_time = time.time()
        
        # Get username if available in session
        username = session.get('user_id', 'anonymous')
        
        # Log the incoming request
        logger.info(f"Request started: {request.method} {request.path}")
    
    @app.after_request
    def after_request(response):
        # Skip logging for static files
        if request.path.startswith('/static'):
            return response
            
        try:
            # Calculate request duration
            duration = time.time() - g.get('start_time', time.time())
            duration_ms = round(duration * 1000, 2)
            
            # Log request completion with status code and duration
            logger.info(f"Request completed: {request.method} {request.path} - Status: {response.status_code} - Duration: {duration_ms}ms")
            
            # Log warning for slow requests
            if duration_ms > 1000:
                logger.warning(f"Slow request: {request.method} {request.path} took {duration_ms}ms")
        except Exception as e:
            # Don't let logging errors break the response
            logger.error(f"Error in after_request: {str(e)}")
            
        return response
    
    @app.teardown_request
    def teardown_request(exception=None):
        if exception:
            # Get full exception details
            error_details = traceback.format_exc()
            logger.error(f"Request failed with exception: {str(exception)}")
            logger.error(f"Stack trace: {error_details}")
    
    @app.errorhandler(Exception)
    def handle_exception(e):
        # Log any unhandled exceptions
        error_details = traceback.format_exc()
        logger.error(f"Unhandled exception: {str(e)}")
        logger.error(f"Stack trace: {error_details}")
        
        # Return a generic error response
        return {"error": "An unexpected error occurred"}, 500
    
    # Register blueprints
    register_blueprints(app)
    logger.info("Blueprints registered")
    
    return app

# Create the application instance
app = create_app()

def run_app():
    """Run the Flask application"""
    try:
        logger.info(f"Starting server on port {PORT}")
        app.run(host='0.0.0.0', port=PORT, debug=DEBUG)
    except Exception as e:
        logger.error(f"Failed to start server: {str(e)}")
        logger.error(traceback.format_exc())
