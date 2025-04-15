import os
from flask import session
from app.utils.logging_config import logger
from app.config import BASE_DIR, PROMPTS_FOLDER, ASSESSMENT_RESULTS_FOLDER
import json
import time
import traceback

# Define constants for the stages with more metadata
STAGES = {
    "apvset": {
        "file": "step_1_ap_et_distinction.txt",
        "name": "AP vs ET Distinction",
        "description": "Initial personality orientation assessment",
        "next": "personality"
    },
    "personality": {
        "file": "step_2_personality_types.txt",
        "name": "Personality Types",
        "description": "Detailed personality type assessment",
        "next": "energy"
    },
    "energy": {
        "file": "step_3_energy_questions.txt",
        "name": "Energy Questions",
        "description": "Energy and decision-making patterns",
        "next": "reinforcement"
    },
    "reinforcement": {
        "file": "step_4_reinforcement_childhood.txt",
        "name": "Reinforcement Patterns",
        "description": "Childhood experiences and reinforcement patterns",
        "next": "final"
    },
    "final": {
        "file": "step_5_final_code_reveal.txt",
        "name": "Final Code Reveal",
        "description": "Summary and personality code revelation",
        "next": None
    }
}

# Default starting stage
DEFAULT_STAGE = "apvset"

def initialize_session_state():
    """Initialize or reset the session state for a new conversation"""
    if 'stage' not in session:
        session['stage'] = DEFAULT_STAGE
    if 'history' not in session:
        session['history'] = []
    if 'assessment_data' not in session:
        session['assessment_data'] = {}
    
    logger.info(f"Initialized session state with stage: {DEFAULT_STAGE}")
    return get_session_state()

def get_session_state():
    """Get the current state of the session"""
    current_stage = session.get('stage', DEFAULT_STAGE)
    return {
        'stage': current_stage,
        'stage_name': STAGES[current_stage]['name'],
        'stage_description': STAGES[current_stage]['description'],
        'next_stage': STAGES[current_stage]['next'],
        'history_length': len(session.get('history', [])),
        'assessment_data': session.get('assessment_data', {})
    }

def get_available_stages():
    """Return a list of available stages with their metadata"""
    return {
        stage_id: {
            'name': data['name'],
            'description': data['description'],
            'next': data['next']
        }
        for stage_id, data in STAGES.items()
    }

def set_stage(stage):
    """Set the current stage of the conversation"""
    if stage not in STAGES:
        logger.error(f"Invalid stage requested: {stage}")
        return False, f"Invalid stage: {stage}. Available stages: {', '.join(STAGES.keys())}"
    
    previous_stage = session.get('stage', DEFAULT_STAGE)
    session['stage'] = stage
    
    logger.info(f"Stage transition: {previous_stage} -> {stage}")
    return True, f"Stage set to: {STAGES[stage]['name']}"

def get_current_stage():
    """Get the current stage of the conversation with metadata"""
    current_stage = session.get('stage', DEFAULT_STAGE)
    return {
        'id': current_stage,
        'name': STAGES[current_stage]['name'],
        'description': STAGES[current_stage]['description'],
        'next': STAGES[current_stage]['next']
    }

def advance_stage():
    """Advance to the next stage if available"""
    current_stage = session.get('stage', DEFAULT_STAGE)
    next_stage = STAGES[current_stage]['next']
    
    if next_stage is None:
        logger.info(f"Cannot advance stage: {current_stage} is the final stage")
        return False, "Already at final stage"
    
    return set_stage(next_stage)

def load_stage_prompt(stage=None):
    """Load the prompt for the specified stage or current stage"""
    if stage is None:
        stage = session.get('stage', DEFAULT_STAGE)
    
    if stage not in STAGES:
        logger.error(f"Invalid stage requested for prompt: {stage}")
        return None
    
    prompt_file = STAGES[stage]['file']
    prompt_path = os.path.join(PROMPTS_FOLDER, prompt_file)
    
    try:
        if not os.path.exists(prompt_path):
            logger.error(f"Prompt file not found: {prompt_path}")
            return None
        
        with open(prompt_path, 'r', encoding='utf-8') as file:
            prompt_content = file.read()
        
        logger.info(f"Loaded prompt for stage '{stage}' ({len(prompt_content)} chars)")
        return prompt_content
    
    except Exception as e:
        logger.error(f"Error loading prompt for stage '{stage}': {str(e)}")
        return None

def store_assessment_data(key, value):
    """Store data from the assessment in the session"""
    if 'assessment_data' not in session:
        session['assessment_data'] = {}
    
    session['assessment_data'][key] = value
    logger.debug(f"Stored assessment data: {key}")
    
    # Save to file after each update
    save_assessment_results()
    return True

def save_assessment_results():
    """Save all assessment data to a JSON file"""
    try:
        os.makedirs(ASSESSMENT_RESULTS_FOLDER, exist_ok=True)
        
        # Get current timestamp and session info
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        session_id = session.get('session_id', 'unknown')
        
        # Get user information
        user_email = session.get('user', 'unknown')
        # Extract username without domain
        username = user_email.split('@')[0] if '@' in user_email else user_email
        
        # Create filename with username and timestamp
        filename = f"assessment_{username}_{timestamp}.json"
        filepath = os.path.join(ASSESSMENT_RESULTS_FOLDER, filename)
        
        # Prepare data to save
        assessment_data = {
            'session_id': session_id,
            'user': {
                'email': user_email,
                'username': username,
                'name': session.get('user_name', 'Unknown'),  # Full name if available
                'id': session.get('user_id', 'unknown')
            },
            'timestamp': time.strftime("%Y-%m-%d %H:%M:%S"),
            'current_stage': get_current_stage(),
            'assessment_data': session.get('assessment_data', {}),
            'stage_history': []
        }
        
        # Add stage history with timestamps
        history = get_history()
        current_stage = None
        stage_data = {}
        
        for entry in history:
            if entry['role'] == 'system':
                # If we have previous stage data, save it
                if current_stage and stage_data:
                    assessment_data['stage_history'].append({
                        'stage': current_stage,
                        'data': stage_data,
                        'completed_at': time.strftime("%Y-%m-%d %H:%M:%S")
                    })
                # Start new stage
                current_stage = entry.get('stage', 'unknown')
                stage_data = {
                    'started_at': entry.get('timestamp', time.strftime("%Y-%m-%d %H:%M:%S")),
                    'messages': []
                }
            elif entry['role'] in ['user', 'assistant']:
                if current_stage:
                    if 'messages' not in stage_data:
                        stage_data['messages'] = []
                    stage_data['messages'].append({
                        'role': entry['role'],
                        'content': entry['content'],
                        'timestamp': entry.get('timestamp', time.strftime("%Y-%m-%d %H:%M:%S"))
                    })
        
        # Add the last stage data if exists
        if current_stage and stage_data:
            assessment_data['stage_history'].append({
                'stage': current_stage,
                'data': stage_data,
                'completed_at': time.strftime("%Y-%m-%d %H:%M:%S")
            })
        
        # Save to file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(assessment_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Saved assessment results for user {username} to {filepath}")
        return True, filepath
    
    except Exception as e:
        error_details = traceback.format_exc()
        logger.error(f"Error saving assessment results: {str(e)}\n{error_details}")
        return False, str(e)

def get_saved_assessment_results(session_id=None):
    """Get all saved assessment results for a session"""
    try:
        results_dir = os.path.join(BASE_DIR, "assessment_results")
        if not os.path.exists(results_dir):
            return []
        
        # If session_id provided, get only that session's results
        results = []
        for filename in os.listdir(results_dir):
            if filename.endswith('.json'):
                if session_id and not filename.startswith(f"assessment_{session_id}_"):
                    continue
                    
                filepath = os.path.join(results_dir, filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    results.append(json.load(f))
        
        return sorted(results, key=lambda x: x['timestamp'], reverse=True)
    
    except Exception as e:
        logger.error(f"Error reading assessment results: {str(e)}")
        return []

def get_latest_assessment_result(session_id=None):
    """Get the most recent assessment result for a session"""
    results = get_saved_assessment_results(session_id)
    return results[0] if results else None

def get_assessment_data(key=None):
    """Get stored assessment data from the session"""
    if key is None:
        return session.get('assessment_data', {})
    
    return session.get('assessment_data', {}).get(key)

def append_to_history(entry):
    """Add an entry to the conversation history"""
    if 'history' not in session:
        session['history'] = []
    
    session['history'].append(entry)
    return True

def get_history():
    """Get the full conversation history"""
    return session.get('history', [])

def clear_history():
    """Clear the conversation history"""
    session['history'] = []
    logger.info("Conversation history cleared")
    return True

def reset_session():
    """Reset the entire session"""
    session.clear()
    initialize_session_state()
    logger.info("Session reset to initial state")
    return True 