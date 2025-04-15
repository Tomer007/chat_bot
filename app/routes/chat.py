from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
import traceback
import os
from werkzeug.utils import secure_filename
import time
from functools import wraps

from app.config import CHATBOT_CONFIG, load_chatbot_config
from app.utils.decorators import login_required
from app.utils.logging_config import logger, log_performance
from app.services.chat_service import get_session_id, generate_response, get_conversation_history, clear_conversation_history, get_session_info, set_session_stage
from app.services.document_service import extract_text_from_file, process_uploaded_file
from app.services.openai_service import get_openai_response

# Create the blueprint
chat_bp = Blueprint('chat', __name__)

# Define path to prompt files
PROMPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'prompts')

# Helper function to read prompt files
def read_prompt_file(filename):
    with open(os.path.join(PROMPTS_DIR, filename), 'r') as file:
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

@chat_bp.route('/stage', methods=['POST'])
def change_stage():
    """Change the current stage of the conversation"""
    try:
        data = request.get_json()
        if not data or 'stage' not in data:
            return jsonify({
                'status': 'error',
                'message': 'Missing stage parameter'
            }), 400
            
        stage = data['stage']
        success = set_session_stage(stage)
        
        if success:
            return jsonify({
                'status': 'success',
                'message': f'Stage changed to {stage}',
                'session': get_session_info()
            }), 200
        else:
            return jsonify({
                'status': 'error',
                'message': f'Invalid stage: {stage}'
            }), 400
            
    except Exception as e:
        error_details = traceback.format_exc()
        logger.error(f"Error changing stage: {str(e)}\n{error_details}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@chat_bp.route('/input', methods=['POST'])
@login_required
def handle_input():
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
                response_text = generate_response(combined_message, stage)
                
                # Format response with RTL/LTR support
                formatted_response = {
                    'status': 'success',
                    'message': response_text,
                    'session': get_session_info(),  # Include current session info with response
                    'formatting': {
                        'rtl': any(ord(c) >= 0x590 and ord(c) <= 0x6FF for c in response_text),  # Check for Hebrew/Arabic characters
                        'markdown': True,  # Enable markdown parsing
                        'direction': 'rtl' if any(ord(c) >= 0x590 and ord(c) <= 0x6FF for c in response_text) else 'ltr'
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

@chat_bp.route('/clear', methods=['POST'])
def clear_chat():
    """Clear the current conversation history"""
    try:
        clear_conversation_history()
        return jsonify({
            'status': 'success',
            'message': 'Conversation cleared',
            'session': get_session_info()  # Include updated session info
        }), 200
    except Exception as e:
        error_details = traceback.format_exc()
        logger.error(f"Error clearing conversation: {str(e)}\n{error_details}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@chat_bp.route('/history', methods=['GET'])
def get_history():
    """Get the conversation history for the current session"""
    try:
        history = get_conversation_history()
        return jsonify({
            'status': 'success',
            'history': history
        }), 200
    except Exception as e:
        error_details = traceback.format_exc()
        logger.error(f"Error retrieving conversation history: {str(e)}\n{error_details}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@chat_bp.route('/start_assessment', methods=['POST'])
def start_assessment():
    """Initialize a new personality assessment session"""
    # Reset or initialize the session
    session['messages'] = []
    session['assessment_stage'] = 'introduction'
    
    # Read the overview prompt
    overview = read_prompt_file('pdn_overview.txt')
    
    # Create introduction message
    intro_message = {
        "role": "assistant",
        "content": "Welcome to the Personality Distinction Numbering (PDN) Assessment. This assessment will help you discover your unique personality type through a series of reflective questions.\n\nWould you like to begin your assessment journey?"
    }
    
    # Add to session history
    session['messages'].append(intro_message)
    
    # Return the introduction
    return jsonify({
        "message": intro_message["content"],
        "assessment_stage": session['assessment_stage']
    })

@chat_bp.route('/send_message', methods=['POST'])
def send_message():
    """Process a message in the personality assessment"""
    data = request.json
    user_message = data.get('message', '')
    
    if not user_message:
        return jsonify({"error": "Message is required"}), 400
    
    # Add user message to history
    if 'messages' not in session:
        session['messages'] = []
        session['assessment_stage'] = 'introduction'
    
    session['messages'].append({"role": "user", "content": user_message})
    
    # Determine current stage and next steps
    current_stage = session.get('assessment_stage', 'introduction')
    response_content = ""
    
    if current_stage == 'introduction':
        # Move to first stage after user confirms they want to begin
        if any(word in user_message.lower() for word in ['yes', 'begin', 'start', 'ready']):
            ap_et_prompt = read_prompt_file('ap_et_distinction.txt')
            response_content = ap_et_prompt
            session['assessment_stage'] = 'ap_et_distinction'
        else:
            response_content = "I understand you may have questions. The PDN assessment helps identify your unique personality pattern through a series of reflective questions. It takes about 15-20 minutes to complete. Would you like to begin when you're ready?"
    
    elif current_stage == 'ap_et_distinction':
        # Check if the user has indicated their AP or ET orientation
        if 'ap' in user_message.lower() or 'analytical' in user_message.lower() or 'peaceful' in user_message.lower():
            personality_types_prompt = read_prompt_file('personality_types.txt')
            response_content = "Based on your responses, you seem to align more with the Analytical-Peaceful orientation. Now, let's explore your specific personality type in more detail.\n\n" + personality_types_prompt
            session['assessment_stage'] = 'personality_type'
            session['orientation'] = 'AP'
        elif 'et' in user_message.lower() or 'expressive' in user_message.lower() or 'tactical' in user_message.lower():
            personality_types_prompt = read_prompt_file('personality_types.txt')
            response_content = "Based on your responses, you seem to align more with the Expressive-Tactical orientation. Now, let's explore your specific personality type in more detail.\n\n" + personality_types_prompt
            session['assessment_stage'] = 'personality_type'
            session['orientation'] = 'ET'
        else:
            # Use OpenAI to analyze the response and determine AP or ET orientation
            messages = session['messages'].copy()
            messages.append({"role": "system", "content": "Analyze the user's message to determine if they align more with AP (Analytical-Peaceful) or ET (Expressive-Tactical) orientation based on the PDN assessment framework. Respond with either 'AP' or 'ET' followed by a brief explanation."})
            
            ai_analysis = get_openai_response(messages)
            
            if 'AP' in ai_analysis:
                personality_types_prompt = read_prompt_file('personality_types.txt')
                response_content = "Based on your responses, you seem to align more with the Analytical-Peaceful orientation. Now, let's explore your specific personality type in more detail.\n\n" + personality_types_prompt
                session['assessment_stage'] = 'personality_type'
                session['orientation'] = 'AP'
            else:  # Default to ET if unclear
                personality_types_prompt = read_prompt_file('personality_types.txt')
                response_content = "Based on your responses, you seem to align more with the Expressive-Tactical orientation. Now, let's explore your specific personality type in more detail.\n\n" + personality_types_prompt
                session['assessment_stage'] = 'personality_type'
                session['orientation'] = 'ET'
    
    elif current_stage == 'personality_type':
        # Check if the user has indicated their personality type (A, E, T, P)
        personality_type = None
        for pt in ['analytical', 'expressive', 'tactical', 'peaceful']:
            if pt[0].lower() in user_message.lower() or pt.lower() in user_message.lower():
                personality_type = pt[0].upper()
                break
        
        if personality_type:
            energy_questions_prompt = read_prompt_file('energy_questions.txt')
            response_content = f"Thank you for identifying with the {personality_type} type. Now, let's explore your energy pattern.\n\n" + energy_questions_prompt
            session['assessment_stage'] = 'energy_pattern'
            session['personality_type'] = personality_type
        else:
            # Use OpenAI to analyze the response and determine personality type
            messages = session['messages'].copy()
            messages.append({"role": "system", "content": "Analyze the user's message to determine their primary personality type (A, E, T, or P) based on the PDN assessment framework. Respond with a single letter (A, E, T, or P) followed by a brief explanation."})
            
            ai_analysis = get_openai_response(messages)
            
            if any(pt in ai_analysis for pt in ['A', 'E', 'T', 'P']):
                for pt in ['A', 'E', 'T', 'P']:
                    if pt in ai_analysis:
                        personality_type = pt
                        break
                
                energy_questions_prompt = read_prompt_file('energy_questions.txt')
                response_content = f"Based on your responses, you seem to align with the {personality_type} type. Now, let's explore your energy pattern.\n\n" + energy_questions_prompt
                session['assessment_stage'] = 'energy_pattern'
                session['personality_type'] = personality_type
            else:
                response_content = "I'm having trouble determining your personality type from your response. Could you please clarify which type you identify with most: Analytical (A), Expressive (E), Tactical (T), or Peaceful (P)?"
    
    elif current_stage == 'energy_pattern':
        # Check if the user has indicated their energy pattern (D, S, F)
        energy_pattern = None
        for ep in ['dominant', 'steady', 'flexible']:
            if ep[0].lower() in user_message.lower() or ep.lower() in user_message.lower():
                energy_pattern = ep[0].upper()
                break
        
        if energy_pattern:
            reinforcement_patterns_prompt = read_prompt_file('reinforcement_patterns.txt')
            response_content = f"Great! You've identified with the {energy_pattern} energy pattern. Now, let's explore your reinforcement pattern to complete your PDN profile.\n\n" + reinforcement_patterns_prompt
            session['assessment_stage'] = 'reinforcement_pattern'
            session['energy_pattern'] = energy_pattern
        else:
            # Use OpenAI to analyze the response and determine energy pattern
            messages = session['messages'].copy()
            messages.append({"role": "system", "content": "Analyze the user's message to determine their energy pattern (D, S, or F) based on the PDN assessment framework. Respond with a single letter (D, S, or F) followed by a brief explanation."})
            
            ai_analysis = get_openai_response(messages)
            
            if any(ep in ai_analysis for ep in ['D', 'S', 'F']):
                for ep in ['D', 'S', 'F']:
                    if ep in ai_analysis:
                        energy_pattern = ep
                        break
                
                reinforcement_patterns_prompt = read_prompt_file('reinforcement_patterns.txt')
                response_content = f"Based on your responses, you seem to align with the {energy_pattern} energy pattern. Now, let's explore your reinforcement pattern to complete your PDN profile.\n\n" + reinforcement_patterns_prompt
                session['assessment_stage'] = 'reinforcement_pattern'
                session['energy_pattern'] = energy_pattern
            else:
                response_content = "I'm having trouble determining your energy pattern from your response. Could you please clarify which pattern you identify with most: Dominant (D), Steady (S), or Flexible (F)?"
    
    elif current_stage == 'reinforcement_pattern':
        # Check if the user has indicated their reinforcement pattern (N, C, I)
        reinforcement_pattern = None
        for rp in ['nurturing', 'challenging', 'inspiring']:
            if rp[0].lower() in user_message.lower() or rp.lower() in user_message.lower():
                reinforcement_pattern = rp[0].upper()
                break
        
        if reinforcement_pattern:
            # Complete the assessment with the full PDN code
            personality_type = session.get('personality_type', '?')
            energy_pattern = session.get('energy_pattern', '?')
            pdn_code = f"{personality_type}{energy_pattern}{reinforcement_pattern}"
            
            response_content = f"Congratulations! Your PDN personality code is: **{pdn_code}**\n\n"
            
            # Add description based on the PDN code
            response_content += generate_pdn_description(pdn_code)
            
            session['assessment_stage'] = 'complete'
            session['reinforcement_pattern'] = reinforcement_pattern
            session['pdn_code'] = pdn_code
        else:
            # Use OpenAI to analyze the response and determine reinforcement pattern
            messages = session['messages'].copy()
            messages.append({"role": "system", "content": "Analyze the user's message to determine their reinforcement pattern (N, C, or I) based on the PDN assessment framework. Respond with a single letter (N, C, or I) followed by a brief explanation."})
            
            ai_analysis = get_openai_response(messages)
            
            if any(rp in ai_analysis for rp in ['N', 'C', 'I']):
                for rp in ['N', 'C', 'I']:
                    if rp in ai_analysis:
                        reinforcement_pattern = rp
                        break
                
                # Complete the assessment with the full PDN code
                personality_type = session.get('personality_type', '?')
                energy_pattern = session.get('energy_pattern', '?')
                pdn_code = f"{personality_type}{energy_pattern}{reinforcement_pattern}"
                
                response_content = f"Congratulations! Your PDN personality code is: **{pdn_code}**\n\n"
                
                # Add description based on the PDN code
                response_content += generate_pdn_description(pdn_code)
                
                session['assessment_stage'] = 'complete'
                session['reinforcement_pattern'] = reinforcement_pattern
                session['pdn_code'] = pdn_code
            else:
                response_content = "I'm having trouble determining your reinforcement pattern from your response. Could you please clarify which pattern you identify with most: Nurturing (N), Challenging (C), or Inspiring (I)?"
    
    elif current_stage == 'complete':
        # Assessment is complete, respond to any follow-up questions
        messages = session['messages'].copy()
        messages.append({"role": "system", "content": f"The user has completed the PDN assessment with code {session.get('pdn_code', 'unknown')}. They may have follow-up questions about their type or the assessment in general. Provide helpful, personalized responses based on their PDN code."})
        
        response_content = get_openai_response(messages)
    
    # Add assistant response to history
    session['messages'].append({"role": "assistant", "content": response_content})
    
    # Return the response
    return jsonify({
        "message": response_content,
        "assessment_stage": session['assessment_stage']
    })

def generate_pdn_description(pdn_code):
    """Generate a description for a specific PDN code"""
    # This is a simplified implementation - in a production system, you would have 
    # detailed descriptions for each of the 36 possible combinations
    
    # Extract the components
    personality_type = pdn_code[0]  # A, E, T, or P
    energy_pattern = pdn_code[1]    # D, S, or F
    reinforcement_pattern = pdn_code[2]  # N, C, or I
    
    # Get descriptions for each component
    type_descriptions = {
        'A': "Analytical: You are methodical, detail-oriented, and value precision and accuracy.",
        'E': "Expressive: You are people-oriented, enthusiastic, and value connection and engagement.",
        'T': "Tactical: You are action-oriented, practical, and value efficiency and results.",
        'P': "Peaceful: You are harmony-seeking, patient, and value stability and balance."
    }
    
    energy_descriptions = {
        'D': "Dominant: You have a forward, assertive approach to life, naturally taking charge.",
        'S': "Steady: You have a consistent, reliable approach, maintaining stability and dependability.",
        'F': "Flexible: You have an adaptable, responsive approach, adjusting to circumstances with agility."
    }
    
    reinforcement_descriptions = {
        'N': "Nurturing: You strengthen through support, care, and emotional connection.",
        'C': "Challenging: You strengthen through high expectations, honest feedback, and pushing beyond comfort zones.",
        'I': "Inspiring: You strengthen through vision, enthusiasm, and belief in positive potential."
    }
    
    # Combine the descriptions
    description = f"**{type_descriptions.get(personality_type, '')}**\n\n"
    description += f"**{energy_descriptions.get(energy_pattern, '')}**\n\n"
    description += f"**{reinforcement_descriptions.get(reinforcement_pattern, '')}**\n\n"
    
    # Add a personalized summary
    description += f"As a {pdn_code} type, you combine these qualities into a unique personality profile. "
    
    # Add some general advice based on the PDN code
    description += "Your awareness of these natural tendencies can help you leverage your strengths and navigate potential challenges in your personal and professional life. Remember that this represents your core tendencies, not rigid limitations.\n\n"
    description += "Would you like to explore any specific aspect of your personality type in more detail?"
    
    return description

@chat_bp.route('/reset', methods=['POST'])
def reset_assessment():
    """Reset the assessment session"""
    session.clear()
    return jsonify({"message": "Assessment reset successfully"})

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