from functools import wraps

from flask import session, redirect, url_for, request, jsonify


def login_required(f):
    """
    Decorator to ensure a user is logged in before accessing a route.
    Redirects to login page if user is not logged in.
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('authenticated'):
            if request.is_json:
                return jsonify({'authenticated': False}), 403
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)

    return decorated_function
