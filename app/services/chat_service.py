import json
import os
import time
import traceback
from flask import session
from app.utils.logging_config import logger, log_performance
from app.config import OPENAI_MODEL, TEMPERATURE, OPENAI_API_KEY, RAG_FILE
from app.services.document_service import load_and_chunk_document
from app.services.stage_service import (
    get_current_stage,
    load_stage_prompt,
    append_to_history,
    get_history,
    advance_stage,
    store_assessment_data,
    set_stage,
    STAGES
)
from openai import OpenAI

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

# Define the stages and their corresponding prompt files
PROMPT_STAGES = {
    "apvset": "prompts/step_1_ap_et_distinction.txt",
    "personality": "prompts/step_2_personality_types.txt",
    "energy": "prompts/step_3_energy_questions.txt",
    "reinforcement": "prompts/step_4_reinforcement_childhood.txt",
    "final": "prompts/step_5_final_code_reveal.txt"
}

# Load the stage-specific prompt from file
@log_performance(logger)
def load_stage_prompt(stage="apvset"):
    """Load a stage-specific system prompt template from file"""
    try:
        if stage not in PROMPT_STAGES:
            raise ValueError(f"Invalid stage '{stage}' - must be one of {list(PROMPT_STAGES.keys())}")
            
        prompt_file = PROMPT_STAGES[stage]
        logger.debug(f"Loading prompt for stage '{stage}' from file: {prompt_file}")
        
        with open(prompt_file, "r", encoding="utf-8") as f:
            prompt = f.read().strip()
            # Add formatting instructions to the prompt
            prompt += "\n\n=== Formatting Instructions ===\n"
            prompt += "1. Use proper Markdown formatting:\n"
            prompt += "   - **Bold** for emphasis and headers\n"
            prompt += "   - *Italic* for secondary emphasis\n"
            prompt += "   - Lists with proper indentation\n"
            prompt += "   - Line breaks between sections\n\n"
            prompt += "2. Format numbered options consistently:\n"
            prompt += "   1️⃣ First option\n"
            prompt += "   2️⃣ Second option\n\n"
            prompt += "3. Structure your responses with clear sections:\n"
            prompt += "   - Start with a friendly greeting\n"
            prompt += "   - Present the main content clearly\n"
            prompt += "   - End with a clear call to action\n\n"
            prompt += "4. Use emojis appropriately:\n"
            prompt += "   - 👋 For greetings\n"
            prompt += "   - 💭 For questions\n"
            prompt += "   - ✨ For highlighting key points\n"
            prompt += "   - 🎯 For goals or objectives\n\n"
            prompt += "5. Maintain consistent spacing:\n"
            prompt += "   - Use blank lines between sections\n"
            prompt += "   - Indent nested content\n"
            prompt += "   - Align related items\n\n"
            prompt += "Remember to format ALL responses according to these guidelines, regardless of language.\n"
            
            logger.debug(f"Prompt loaded for stage '{stage}': {len(prompt)} characters")
            return prompt
    except Exception as e:
        error_details = traceback.format_exc()
        logger.error(f"Error loading prompt file for stage '{stage}': {str(e)}\n{error_details}")
        raise

# Load the base prompt from file (for backward compatibility)
@log_performance(logger)
def load_base_prompt():
    """Load the system prompt template from file"""
    return load_stage_prompt("default")

# Load reference text from document
@log_performance(logger)
def load_reference_text():
    """Load reference text from document file"""
    try:
        logger.debug(f"Loading reference text from: {RAG_FILE}")
        doc_chunks = load_and_chunk_document(RAG_FILE)
        # Take top chunks (can be improved with retrieval later)
        reference = "\n\n".join([chunk.page_content for chunk in doc_chunks[:2]])
        logger.debug(f"Reference text loaded: {len(reference)} characters")
        return reference
    except Exception as e:
        error_details = traceback.format_exc()
        logger.error(f"Error loading reference text: {str(e)}\n{error_details}")
        return "Default reference text - error loading reference document."

# Create the system prompt
@log_performance(logger)
def create_system_prompt():
    """Create the complete system prompt with stage-specific content"""
    stage = get_current_stage()
    stage_prompt = load_stage_prompt(stage)
    
    if not stage_prompt:
        logger.error("Failed to load stage prompt")
        return "Default system prompt - error loading stage prompt."
    
    logger.debug(f"Created system prompt for stage '{stage}': {len(stage_prompt)} characters")
    return stage_prompt

# Chat history per session
conversation_history = {}
session_stages = {}  # Track the current stage for each session

def get_session_id():
    """Get a unique session ID for the current user session"""
    if 'session_id' not in session:
        session['session_id'] = os.urandom(8).hex()
        logger.info(f"New session created: {session['session_id']}")
        
        # Initialize stage for new session
        set_stage("apvset")  # Start with the first stage
        
        # Audit log for new session
        user = session.get('user_id', 'anonymous')
        logger.audit(f"New chat session started by user '{user}' with session_id {session['session_id']}")
    else:
        logger.debug(f"Using existing session: {session['session_id']}")
        
        # Ensure stage is initialized for existing session
        if session['session_id'] not in session_stages:
            session_stages[session['session_id']] = "apvset"
            
    return session['session_id']

def get_current_stage(session_id=None):
    """Get the current stage for a session"""
    sid = session_id or get_session_id()
    return session_stages.get(sid, "apvset")

def set_session_stage(stage, session_id=None):
    """Set the current stage for a session"""
    sid = session_id or get_session_id()
    
    if stage in PROMPT_STAGES:
        session_stages[sid] = stage
        logger.info(f"Session {sid} stage set to '{stage}'")
        return True
    else:
        logger.error(f"Invalid stage '{stage}' - must be one of {list(PROMPT_STAGES.keys())}")
        return False

@log_performance(logger)
def generate_response(user_message, stage=None):
    """Generate a response using the OpenAI API for the current stage"""
    try:
        # Get session ID and user info
        session_id = session.get('session_id', 'unknown')
        user = session.get('user_id', 'unknown')
        message_length = len(user_message)
        
        # Get current stage info
        current_stage = get_current_stage()
        stage_info = STAGES[current_stage]
        
        logger.info(f"Generating response for user '{user}', stage '{stage_info['name']}', message length: {message_length} chars")
        
        # Get or create conversation history
        history = get_history()
        
        # Initialize with system prompt if this is the first message
        if not history:
            stage_prompt = load_stage_prompt()
            history.append({
                "role": "system",
                "content": stage_prompt,
                "stage": current_stage,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            })
            logger.info(f"Initialized conversation for stage: {stage_info['name']}")
        
        # Add user message to history with timestamp
        message_entry = {
            "role": "user",
            "content": user_message,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        history.append(message_entry)
        append_to_history(message_entry)
        
        # Call OpenAI API with formatting reminder
        start_time = time.time()
        messages = [{"role": m["role"], "content": m["content"]} for m in history]
        messages.append({
            "role": "system",
            "content": "Remember to format your response with proper Markdown, emojis, and clear structure. Use bold for emphasis, proper spacing, and emoji numbers for options."
        })
        
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            temperature=TEMPERATURE
        )
        api_time = time.time() - start_time
        
        # Get and format the response
        bot_reply = response.choices[0].message.content.strip()
        
        # Ensure proper formatting
        if not bot_reply.startswith(('👋', '✨', '💭', '🎯')):
            bot_reply = "👋 " + bot_reply
            
        # Add line breaks if missing
        if not "\n\n" in bot_reply:
            bot_reply = bot_reply.replace("\n", "\n\n")
        
        # Add the bot's response to history with timestamp
        response_entry = {
            "role": "assistant",
            "content": bot_reply,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        history.append(response_entry)
        append_to_history(response_entry)
        
        # Process stage advancement and data storage as before...
        if "ADVANCE_STAGE" in bot_reply:
            next_stage = stage_info['next']
            if next_stage:
                success, _ = set_stage(next_stage)
                if success:
                    new_stage_info = STAGES[next_stage]
                    logger.info(f"Advanced to stage: {new_stage_info['name']}")
                    new_stage_prompt = load_stage_prompt()
                    history.append({
                        "role": "system",
                        "content": new_stage_prompt,
                        "stage": next_stage,
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                    })
        
        if "STORE_DATA:" in bot_reply:
            for line in bot_reply.split('\n'):
                if line.startswith("STORE_DATA:"):
                    key, value = line.replace("STORE_DATA:", "").strip().split("=")
                    store_assessment_data(key.strip(), value.strip())
        
        logger.info(f"Generated response ({len(bot_reply)} chars) in {api_time:.2f}s")
        return bot_reply
        
    except Exception as e:
        error_details = traceback.format_exc()
        logger.error(f"Error generating response: {str(e)}\n{error_details}")
        return "⚠️ **Error:** I encountered an issue processing your request. Please try again."

def get_conversation_history(session_id=None):
    """Get the conversation history for the current or specified session"""
    sid = session_id or get_session_id()
    history = conversation_history.get(sid, [])
    logger.debug(f"Retrieved conversation history for session {sid}: {len(history)} messages")
    return history

def clear_conversation_history(session_id=None):
    """Clear the conversation history for the current or specified session"""
    sid = session_id or get_session_id()
    user = session.get('user_id', 'anonymous')
    
    if sid in conversation_history:
        message_count = len(conversation_history[sid])
        del conversation_history[sid]
        logger.info(f"Conversation history cleared for session {sid}: {message_count} messages")
        logger.audit(f"User '{user}' cleared conversation history for session {sid}, {message_count} messages deleted")
        return True
    
    logger.debug(f"No conversation history found for session {sid}")
    return False

def get_session_stats():
    """Get statistics about all active sessions"""
    stats = {
        "total_sessions": len(conversation_history),
        "total_messages": sum(len(messages) for messages in conversation_history.values()),
        "sessions": {}
    }
    
    for sid, messages in conversation_history.items():
        stats["sessions"][sid] = {
            "message_count": len(messages),
            "last_update": messages[-1].get("timestamp", "unknown") if messages else "unknown"
        }
    
    logger.debug(f"Session stats: {stats['total_sessions']} active sessions, {stats['total_messages']} total messages")
    return stats

def get_session_info():
    """Get comprehensive information about the current session"""
    stage_data = get_current_stage()
    history = get_history()
    
    return {
        "session_id": session.get('session_id', 'unknown'),
        "user": session.get('user_id', 'unknown'),
        "stage": stage_data,
        "history_length": len(history),
        "last_message": history[-1] if history else None
    } 