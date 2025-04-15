from flask import Blueprint, request, render_template, session, redirect, url_for, jsonify
import os

auth_bp = Blueprint('auth', __name__)

# Default chatbot config
DEFAULT_CONFIG = {
    'name': 'PDN Chat',
    'title': 'Personal Code Profiler',
    'description': 'AI-powered personality assessment'
}

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password = request.form.get('password', '')
        if password == '123':
            session['authenticated'] = True
            session['user_id'] = 'user'
            return redirect(url_for('chat.index'))
        return render_template('login.html', 
                             error='Invalid password',
                             chatbot_config=DEFAULT_CONFIG)
    return render_template('login.html', 
                         chatbot_config=DEFAULT_CONFIG)

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))

@auth_bp.route('/check_session')
def check_session():
    if session.get('authenticated'):
        return jsonify({'authenticated': True})
    return jsonify({'authenticated': False}) 