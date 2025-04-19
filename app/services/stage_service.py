import json
import os
import time
import traceback

from flask import session

from app.config import PROMPTS_FOLDER, ASSESSMENT_RESULTS_FOLDER
from app.utils.logging_config import logger

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
        "file": "step_3_energy.txt",
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
    session_to_return = get_session_state()
    logger.info(f"Initialized session: {session_to_return}")

    return session_to_return


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


def set_stage(stage):
    """Set the current stage of the conversation"""
    if stage not in STAGES:
        logger.error(f"Invalid stage requested: {stage}")
        return False, f"Invalid stage: {stage}. Available stages: {', '.join(STAGES.keys())}"

    previous_stage = session.get('stage', DEFAULT_STAGE)
    session['stage'] = stage
    session.modified = True  # Ensure Flask knows the session was modified

    logger.info(f"Stage transition: {previous_stage} -> {stage}")
    logger.debug(f"Session after stage change: stage={session.get('stage')}")

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
    """Store data from the assessment in the session and save to file"""
    if 'assessment_data' not in session:
        session['assessment_data'] = {}
        logger.debug("Initialized assessment_data in session")

    session['assessment_data'][key] = value
    session.modified = True
    logger.debug(f"Stored assessment data in session: {key}={value}")

    # Save to file after each update
    success, filepath = save_assessment_results()
    if success:
        logger.debug(f"Successfully saved assessment results to {filepath}")
    else:
        logger.error(f"Failed to save assessment results to file")
    return success, filepath


def save_assessment_results():
    """Save all assessment data to a single JSON file per session"""
    logger.debug("Saving assessment results")
    try:
        os.makedirs(ASSESSMENT_RESULTS_FOLDER, exist_ok=True)
        logger.debug(f"Ensuring assessment results directory exists: {ASSESSMENT_RESULTS_FOLDER}")

        # Get session and user info
        session_id = session.get('session_id', 'unknown')
        user_id = session.get('user_id', 'unknown')
        current_stage = session.get('stage', DEFAULT_STAGE)

        # Create filename with session ID
        filename = f"assessment_{user_id}_{session_id}.json"
        filepath = os.path.join(ASSESSMENT_RESULTS_FOLDER, filename)
        logger.debug(f"Will save assessment to: {filepath}")

        # Load existing data if file exists
        existing_data = {}
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
                logger.debug(f"Loaded existing assessment data from {filepath}")
            except json.JSONDecodeError:
                logger.warning(f"Could not parse existing assessment file {filepath}, starting fresh")

        # Initialize or update base assessment data
        assessment_data = existing_data or {
            'session_id': session_id,
            'user': {
                'username': user_id
            },
            'started_at': time.strftime("%Y-%m-%d %H:%M:%S"),
            'last_updated': time.strftime("%Y-%m-%d %H:%M:%S"),
            'current_stage': get_current_stage(),
            'assessment_data': session.get('assessment_data', {}),
            'stages': {}
        }

        # Update last_updated timestamp and current stage
        assessment_data['last_updated'] = time.strftime("%Y-%m-%d %H:%M:%S")
        assessment_data['current_stage'] = get_current_stage()
        assessment_data['assessment_data'] = session.get('assessment_data', {})

        # Process history for current stage
        history = get_history()
        stage_data = {
            'started_at': None,
            'messages': [],
            'completed_at': None
        }

        if history:
            for entry in history:
                entry_role = entry.get('role', 'unknown')
                entry_stage = entry.get('stage', current_stage)

                # Only process entries for current stage
                if entry_stage == current_stage:
                    if entry_role == 'system':
                        stage_data['started_at'] = entry.get('timestamp', time.strftime("%Y-%m-%d %H:%M:%S"))
                    elif entry_role in ['user', 'assistant']:
                        stage_data['messages'].append({
                            'role': entry_role,
                            'content': entry.get('content', ''),
                            'timestamp': entry.get('timestamp', time.strftime("%Y-%m-%d %H:%M:%S"))
                        })

        # Update stage data if we have a valid start time
        if stage_data['started_at']:
            stage_data['completed_at'] = time.strftime("%Y-%m-%d %H:%M:%S")
            assessment_data['stages'][current_stage] = stage_data

        # Save to file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(assessment_data, f, ensure_ascii=False, indent=2)

        logger.info(f"Saved assessment results to {filepath}")
        return True, filepath

    except Exception as e:
        error_details = traceback.format_exc()
        logger.error(f"Error saving assessment results: {str(e)}\n{error_details}")
        return False, str(e)


def get_history():
    """Get the full conversation history"""
    history = session.get('history')
    if history is None:
        history = []
        session['history'] = history
        logger.debug("Initialized new history list in session")
    logger.debug(f"Retrieved history from session: {history}")
    return history
