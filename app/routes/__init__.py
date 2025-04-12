from flask import Blueprint
from app.routes.auth import auth_bp
from app.routes.chat import chat_bp
from app.routes.admin import admin_bp

# Register all blueprints
def register_blueprints(app):
    """Register all blueprints with the Flask app"""
    app.register_blueprint(auth_bp, url_prefix='')
    app.register_blueprint(chat_bp, url_prefix='')
    app.register_blueprint(admin_bp, url_prefix='')
