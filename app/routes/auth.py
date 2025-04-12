import os
import time
import hashlib
from datetime import datetime
from flask import Blueprint, request, render_template, session, redirect, url_for, jsonify, g

from app.config import load_chatbot_config, SESSION_LIFETIME
from app.utils.decorators import login_required
from app.utils.logging_config import logger, log_performance

# Create the blueprint
auth_bp = Blueprint('auth', __name__)

@auth_bp.before_request
def before_request():
    """Check and update session activity before each request"""
    if 'user_id' in session:
        # Get current time
        current_time = datetime.now()
        
        # Check if session is expired
        if 'last_activity' in session:
            last_activity = datetime.fromisoformat(session['last_activity'])
            # Calculate session age
            session_age = (current_time - last_activity).total_seconds()
            
            if current_time - last_activity > SESSION_LIFETIME:
                user_id = session.get('user_id')
                session_id = session.get('session_id', 'unknown')
                
                logger.info(f"Session expired for user: {user_id} (idle for {session_age:.1f}s)")
                logger.audit(f"Session expired: user '{user_id}' session {session_id} timed out after {session_age:.1f}s of inactivity")
                
                session.clear()
                return redirect(url_for('auth.login'))
        
        # Update last activity time
        session['last_activity'] = current_time.isoformat()

@log_performance(logger)
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Handle user login"""
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        remember = request.form.get("remember") == "on"
        
        # Calculate a request identifier (hash of username and request time - for anonymized logs)
        request_time = time.time()
        request_hash = hashlib.md5(f"{username}:{request_time}".encode()).hexdigest()[:8]
        client_ip = request.remote_addr
        
        # Add to g for logging context
        g.login_request_id = request_hash
        
        # Log login attempt 
        logger.info(f"Login attempt - username: {username}, remember: {remember}")
        logger.debug(f"Login attempt details - IP: {client_ip}, User-Agent: {request.user_agent}")
        
        correct_password = os.getenv("USER_PASSWORD")
        
        # Check if password is correct
        if password == correct_password:
            # Generate session data
            session.permanent = remember
            session["user_id"] = username
            session["login_time"] = datetime.now().isoformat()
            session["login_ip"] = client_ip
            
            # Record successful login
            logger.info(f"User logged in successfully: {username}")
            logger.audit(f"Successful login: user '{username}' from IP {client_ip}, User-Agent: {request.user_agent}")
            
            # Redirect to intended destination or default page
            next_page = request.args.get("next")
            if next_page and next_page.startswith("/"):
                return redirect(next_page)
            return redirect(url_for('chat.index'))
        else:
            # Record failed login attempt
            logger.warning(f"Failed login attempt for user: {username} from IP {client_ip}")
            logger.audit(f"Failed login: user '{username}' from IP {client_ip}, User-Agent: {request.user_agent}, incorrect password")
            
            # Return to login page with error
            return render_template("login.html", 
                                  error="שם משתמש או סיסמה שגויים", 
                                  chatbot_config=load_chatbot_config())

    # GET request - show login form
    logger.debug("Rendering login page")
    
    # Check if redirected from session timeout
    was_timeout = request.args.get("timeout") == "1"
    if was_timeout:
        logger.debug("Login page loaded after session timeout")
        return render_template("login.html", 
                              error="Your session has expired. Please log in again.", 
                              chatbot_config=load_chatbot_config())
    
    return render_template("login.html", chatbot_config=load_chatbot_config())

@auth_bp.route("/logout")
def logout():
    """Handle user logout"""
    user = session.get('user_id', 'Unknown')
    session_id = session.get('session_id', 'unknown')
    login_time = session.get('login_time', 'unknown')
    
    # Calculate session duration if login time is available
    session_duration = "unknown"
    if login_time != 'unknown':
        try:
            login_datetime = datetime.fromisoformat(login_time)
            duration_seconds = (datetime.now() - login_datetime).total_seconds()
            session_duration = f"{duration_seconds:.1f}s"
        except:
            pass
    
    # Log logout
    logger.info(f"User logged out: {user}")
    logger.audit(f"User logout: '{user}' session {session_id} ended after {session_duration}")
    
    # Clear session
    session.clear()
    
    return redirect(url_for('auth.login'))

@auth_bp.route('/check_session')
def check_session():
    """Check if the user session is still valid"""
    if 'user_id' in session and 'last_activity' in session:
        # Get current time and calculate session age
        current_time = datetime.now()
        last_activity = datetime.fromisoformat(session['last_activity'])
        session_age = (current_time - last_activity).total_seconds()
        
        if current_time - last_activity > SESSION_LIFETIME:
            # Session expired
            user_id = session.get('user_id')
            session_id = session.get('session_id', 'unknown')
            
            logger.info(f"Session check: expired for user {user_id} (idle for {session_age:.1f}s)")
            logger.audit(f"Session expired during check: user '{user_id}' session {session_id} timed out after {session_age:.1f}s of inactivity")
            
            session.clear()
            return jsonify({'status': 'expired'})
            
        # Update last activity on successful check
        session['last_activity'] = current_time.isoformat()
        logger.debug(f"Session check: active for user {session.get('user_id')} (idle for {session_age:.1f}s)")
        return jsonify({'status': 'active'})
        
    logger.debug("Session check: no active session")
    return jsonify({'status': 'expired'}) 