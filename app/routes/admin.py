import os
from datetime import datetime
from flask import Blueprint, request, render_template, jsonify, send_file, abort

from app.utils.decorators import login_required, admin_required
from app.utils.logging_config import logger
from app.services.chat_service import get_session_stats, clear_conversation_history

# Create the blueprint
admin_bp = Blueprint('admin', __name__)

@admin_bp.route("/admin")
@login_required
@admin_required
def admin_dashboard():
    """Admin dashboard for monitoring the application"""
    logger.info("Admin dashboard accessed")
    logger.audit("Admin dashboard accessed")
    return render_template("admin/dashboard.html")

@admin_bp.route("/admin/logs")
@login_required
@admin_required
def view_logs():
    """View application logs"""
    log_type = request.args.get("type", "app")
    lines = int(request.args.get("lines", "100"))
    
    # Limit lines to prevent huge responses
    if lines > 1000:
        lines = 1000
    
    # Determine which log file to read
    log_file = "logs/app.log"
    if log_type == "error":
        log_file = "logs/error.log"
    elif log_type == "audit":
        log_file = "logs/audit.log"
    
    # Check if file exists
    if not os.path.exists(log_file):
        logger.error(f"Log file not found: {log_file}")
        return jsonify({"error": f"Log file not found: {log_file}"}), 404
    
    # Read the requested number of log lines
    log_lines = []
    try:
        with open(log_file, 'r') as f:
            # Read lines from the end of the file
            all_lines = f.readlines()
            log_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
            
        logger.info(f"Admin viewed {len(log_lines)} lines from {log_file}")
        logger.audit(f"Log access: {log_file}, {len(log_lines)} lines")
        
        return jsonify({
            "file": log_file,
            "lines": len(log_lines),
            "contents": log_lines
        })
    except Exception as e:
        logger.error(f"Error reading log file {log_file}: {str(e)}")
        return jsonify({"error": f"Error reading log file: {str(e)}"}), 500

@admin_bp.route("/admin/download/logs/<log_type>")
@login_required
@admin_required
def download_logs(log_type):
    """Download a log file"""
    # Determine which log file to download
    log_file = "logs/app.log"
    if log_type == "error":
        log_file = "logs/error.log"
    elif log_type == "audit":
        log_file = "logs/audit.log"
    else:
        log_file = "logs/app.log"
    
    # Check if file exists
    if not os.path.exists(log_file):
        logger.error(f"Log file not found for download: {log_file}")
        abort(404)
    
    # Log the download
    logger.info(f"Admin downloaded log file: {log_file}")
    logger.audit(f"Log download: {log_file}")
    
    # Attach a timestamp to the filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    download_name = f"{log_type}_log_{timestamp}.log"
    
    return send_file(log_file, as_attachment=True, download_name=download_name)

@admin_bp.route("/admin/sessions")
@login_required
@admin_required
def session_stats():
    """Get statistics about all active sessions"""
    stats = get_session_stats()
    
    logger.info(f"Admin viewed session stats: {stats['total_sessions']} sessions")
    logger.audit(f"Session stats accessed: {stats['total_sessions']} sessions, {stats['total_messages']} messages")
    
    return jsonify(stats)

@admin_bp.route("/admin/sessions/<session_id>/clear", methods=["POST"])
@login_required
@admin_required
def clear_session(session_id):
    """Clear a specific session's conversation history"""
    result = clear_conversation_history(session_id)
    
    if result:
        logger.info(f"Admin cleared session: {session_id}")
        logger.audit(f"Admin action: cleared session {session_id}")
        return jsonify({"success": True, "message": f"Session {session_id} cleared"})
    else:
        logger.warning(f"Admin attempted to clear non-existent session: {session_id}")
        return jsonify({"success": False, "message": f"Session {session_id} not found"}) 