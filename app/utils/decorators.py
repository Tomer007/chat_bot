from functools import wraps
from flask import session, redirect, url_for

from app.utils.logging_config import logger

def login_required(f):
    """
    Decorator to ensure a user is logged in before accessing a route.
    Redirects to login page if user is not logged in.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            logger.warning(f"Unauthorized access attempt to {f.__name__}")
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)

    return decorated_function

def admin_required(f):
    """
    Decorator to ensure a user is an admin before accessing a route.
    Redirects to home page if user is not an admin.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = session.get('user_id', '')
        
        # Check if user is in admin list
        # You can modify this to use a database or env var
        admin_users = ['admin', 'supervisor', 'root', 'superuser']
        
        if user_id not in admin_users:
            logger.warning(f"Non-admin user '{user_id}' tried to access {f.__name__}")
            logger.audit(f"Admin access denied: user '{user_id}' attempted to access {f.__name__}")
            return redirect(url_for('chat.index'))
        
        logger.debug(f"Admin access granted to {user_id} for {f.__name__}")
        return f(*args, **kwargs)
        
    return decorated_function 