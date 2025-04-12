from flask import Blueprint, render_template, request, jsonify

from app.config import CHATBOT_CONFIG
from app.utils.decorators import login_required
from app.utils.logging_config import logger
from app.services.chat_service import get_session_id, generate_response, get_conversation_history
from app.services.document_service import extract_text_from_file

# Create the blueprint
chat_bp = Blueprint('chat', __name__)

@chat_bp.route("/")
@login_required
def index():
    """Render the main chat interface"""
    logger.debug("Rendering chat interface")
    return render_template("chat.html", chatbot_config=CHATBOT_CONFIG)

@chat_bp.route("/session-status", methods=["GET"])
@login_required
def session_status():
    """Get the status of the current chat session"""
    session_id = get_session_id()
    history = get_conversation_history(session_id)
    
    status = {
        "session_id": session_id,
        "has_history": bool(history),
        "history_length": len(history)
    }
    
    logger.debug(f"Session status: {status}")
    return jsonify(status)

@chat_bp.route('/api/chat_upload', methods=['POST'])
@login_required
def handle_input():
    """Accept both user text and optional file, combine, and send to OpenAI"""
    user_message = request.form.get("message", "").strip()
    uploaded_file = request.files.get("file")  # None if not provided
    file_content = ""
    
    logger.info("Processing chat request")
    
    if uploaded_file and uploaded_file.filename:
        try:
            uploaded_file.seek(0)  # Reset pointer
            logger.info(f"Processing uploaded file: {uploaded_file.filename}")
            file_content = extract_text_from_file(uploaded_file)
            logger.info(f"Extracted text length: {len(file_content)} characters")
            logger.debug(f"First 100 chars of content: {file_content[:100]}...")
        except Exception as e:
            error_msg = f"Error processing file: {str(e)}"
            logger.error(error_msg)
            return jsonify({"success": False, "error": error_msg}), 500

    # Combine text + file content into a single prompt
    combined_prompt = (
        f"{user_message if user_message != '' else 'Please analyze and create a PDN report based on the content above.'}\n{file_content}\n"
    )

    try:
        # Send combined prompt to OpenAI
        logger.info("Generating response")
        response_text = generate_response(combined_prompt)
        logger.info("Response generated successfully")
        return jsonify({"success": True, "response": response_text})
    except Exception as e:
        error_msg = f"Error generating response: {str(e)}"
        logger.error(error_msg)
        return jsonify({"success": False, "error": error_msg}), 500 