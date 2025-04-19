import os
import traceback
from datetime import datetime
from functools import wraps

import markdown
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, make_response

from app.config import load_chatbot_config, PROMPTS_FOLDER
from app.services.chat_service import generate_response, \
    get_session_info
from app.services.document_service import process_uploaded_file
from app.utils.logging_config import logger, log_performance

# Create the blueprint
chat_bp = Blueprint('chat', __name__)


# Helper function to read prompt files
def read_prompt_file(filename):
    prompt_path = os.path.join(PROMPTS_FOLDER, filename)
    with open(prompt_path, 'r') as file:
        return file.read()


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)

    return decorated_function


@chat_bp.route("/")
@chat_bp.route("/index")
@login_required
@log_performance(logger)
def index():
    """Render the main chat interface"""
    user_id = session.get('user_id')
    logger.debug(f"Rendering chat interface for user: {user_id}")

    chatbot_config = load_chatbot_config()
    chatbot_config['user_id'] = user_id  # Add user info to config

    return render_template(
        'chat.html',
        user_id=user_id,
        chatbot_config=chatbot_config
    )


@chat_bp.route('/session', methods=['GET'])
def session_status():
    """Get the current session status including stage and history information"""
    try:
        session_info = get_session_info()
        return jsonify({
            'status': 'success',
            'session': session_info
        }), 200
    except Exception as e:
        error_details = traceback.format_exc()
        logger.error(f"Error getting session status: {str(e)}\n{error_details}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@chat_bp.route('/send_message', methods=['POST'])
@login_required
def send_message():
    """Handle user input (text and/or files) and generate a response"""
    try:
        # Get message text from form data or JSON
        message = ""
        stage = None

        if request.content_type and 'application/json' in request.content_type:
            data = request.get_json()
            if data:
                message = data.get('message', '')
                stage = data.get('stage', None)  # Optionally change stage with message
        else:
            message = request.form.get('message', '')
            stage = request.form.get('stage', None)

        # Log the request details
        logger.info(f"Received chat input: message length {len(message)}" +
                    (f", stage: {stage}" if stage else ""))

        # Check for file upload
        file_text = ""
        file_info = {}

        if 'file' in request.files:
            file = request.files['file']

            if file and file.filename:
                logger.info(f"Processing uploaded file: {file.filename}")

                # Process file to extract text
                file_info, file_text = process_uploaded_file(file)
                if file_text:
                    logger.info(f"Extracted {len(file_text)} characters from file")
                else:
                    logger.warning(f"No text extracted from file: {file.filename}")
            else:
                logger.debug("No valid file received in upload")

        # Combine message and file text (if any)
        if file_text:
            combined_message = f"{message}\n\nFile Content:\n{file_text}"
        else:
            combined_message = message

        # Generate response
        if combined_message:
            try:
                response = generate_response(combined_message, stage)

                # Check if response is a dictionary (special handling)
                if isinstance(response, dict):
                    return jsonify(response), 200

                # Format response with RTL/LTR support for text responses
                formatted_response = {
                    'status': 'success',
                    'message': response,
                    'session': get_session_info(),  # Include current session info with response
                    'formatting': {
                        'rtl': any(ord(c) >= 0x590 and ord(c) <= 0x6FF for c in str(response)),
                        'markdown': True,  # Enable markdown parsing
                        'direction': 'rtl' if any(ord(c) >= 0x590 and ord(c) <= 0x6FF for c in str(response)) else 'ltr'
                    }
                }

                # Add file info if a file was processed
                if file_info:
                    formatted_response['file_info'] = file_info

                return jsonify(formatted_response), 200

            except ValueError as ve:
                # Handle specific validation errors (like invalid stage)
                logger.error(f"Validation error: {str(ve)}")
                return jsonify({
                    'status': 'error',
                    'message': str(ve),
                    'formatting': {
                        'rtl': True,
                        'markdown': True,
                        'direction': 'rtl'
                    }
                }), 400
            except FileNotFoundError as fe:
                # Handle missing prompt files
                logger.error(f"Prompt file not found: {str(fe)}")
                return jsonify({
                    'status': 'error',
                    'message': 'קובץ התבנית הנדרש לא נמצא. אנא צור קשר עם התמיכה.',
                    'formatting': {
                        'rtl': True,
                        'markdown': True,
                        'direction': 'rtl'
                    }
                }), 500
        else:
            return jsonify({
                'status': 'error',
                'message': 'לא סופקה הודעה או קובץ',
                'formatting': {
                    'rtl': True,
                    'markdown': True,
                    'direction': 'rtl'
                }
            }), 400

    except Exception as e:
        error_details = traceback.format_exc()
        logger.error(f"Error handling chat input: {str(e)}\n{error_details}")
        return jsonify({
            'status': 'error',
            'message': str(e),
            'formatting': {
                'rtl': True,
                'markdown': True,
                'direction': 'rtl'
            }
        }), 500


@chat_bp.route('/upload', methods=['POST'])
@login_required
def chat_upload():
    """Handle file upload and generate response"""
    try:
        # Check if the post request has the file part
        if 'file' not in request.files:
            return jsonify({'error': 'No file part'}), 400

        file = request.files['file']
        message = request.form.get('message', '')

        # If user does not select file, browser also
        # submit an empty part without filename
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400

        # Process the file and message
        combined_message = f"{message}\n[File: {file.filename}]"

        # Generate response
        response_text = generate_response(combined_message)

        return jsonify({
            'message': response_text,
            'file_processed': True
        })

    except Exception as e:
        logger.error(f"Error in chat upload: {str(e)}\n{traceback.format_exc()}")
        return jsonify({'error': 'Internal server error'}), 500


@chat_bp.route('/view_report')
@login_required
def view_report():
    """View the PDN personality report"""
    try:
        # Get the report content from session
        assessment_data = session.get('assessment_data', {})
        report_content = assessment_data.get('final_report', '')

        if not report_content:
            return redirect(url_for('chat.index'))

        html_content = f'<div class="markdown-body">{markdown.markdown(report_content, extensions=["extra", "sane_lists"])}</div>'

        # Get user's language preference
        user_language = session.get('language', 'en')
        is_rtl = user_language == 'he'

        return render_template('pdn_report.html',
                               report_content=html_content,
                               report_date=datetime.now().strftime('%Y-%m-%d'),
                               is_rtl=is_rtl)

    except Exception as e:
        logger.error(f"Error viewing report: {str(e)}")
        return redirect(url_for('chat.index'))


@chat_bp.route('/download_report')
@login_required
def download_report():
    """Download the PDN personality report as HTML"""
    try:
        # Get the report content from session
        assessment_data = session.get('assessment_data', {})
        report_content = assessment_data.get('final_report', '')
        html_content = f'<div class="markdown-body">{markdown.markdown(report_content, extensions=["extra", "sane_lists"])}</div>'

        if not html_content:
            return redirect(url_for('chat.index'))

        # Get user's language preference
        user_language = session.get('language', 'en')
        is_rtl = user_language == 'he'

        # Generate HTML
        html = render_template('pdn_report.html',
                               report_content=html_content,
                               report_date=datetime.now().strftime('%Y-%m-%d'),
                               is_rtl=is_rtl)

        # Create response with HTML content
        response = make_response(html)
        response.headers['Content-Type'] = 'text/html'
        response.headers['Content-Disposition'] = 'attachment; filename=PDN_Personality_Report.html'

        return response

    except Exception as e:
        logger.error(f"Error downloading report: {str(e)}")
        return redirect(url_for('chat.index'))
