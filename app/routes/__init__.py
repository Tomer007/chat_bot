"""Routes package for the application.

This package contains all the route blueprints for the application:
- auth_bp: Authentication routes (/auth/*)
- chat_bp: Chat functionality routes (/chat/*)
"""

from app.routes.auth import auth_bp
from app.routes.chat import chat_bp

# Export blueprints
__all__ = ['auth_bp', 'chat_bp']
