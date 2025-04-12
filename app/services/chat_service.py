import json
import os
import time
import traceback
from flask import session

from openai import OpenAI
from app.config import OPENAI_API_KEY, OPENAI_MODEL, TEMPERATURE, PROMPT_FILE, DOCX_FILE_PATH
from app.utils.logging_config import logger, log_performance
from app.services.document_service import load_and_chunk_document

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

# Load the base prompt from file
@log_performance(logger)
def load_base_prompt():
    """Load the system prompt template from file"""
    try:
        logger.debug(f"Loading prompt from file: {PROMPT_FILE}")
        with open(PROMPT_FILE, "r", encoding="utf-8") as f:
            prompt = f.read().strip()
            logger.debug(f"Prompt loaded: {len(prompt)} characters")
            return prompt
    except Exception as e:
        error_details = traceback.format_exc()
        logger.error(f"Error loading prompt file: {str(e)}\n{error_details}")
        return "Default system prompt - error loading prompt file."

# Load reference text from document
@log_performance(logger)
def load_reference_text():
    """Load reference text from document file"""
    try:
        logger.debug(f"Loading reference text from: {DOCX_FILE_PATH}")
        doc_chunks = load_and_chunk_document(DOCX_FILE_PATH)
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
    """Create the complete system prompt with reference text"""
    base_prompt = load_base_prompt()
    reference_text = load_reference_text()
    
    combined = f"""{base_prompt}

להלן מידע נוסף :

{reference_text}
"""
    logger.debug(f"Created system prompt: {len(combined)} characters")
    return combined

# Chat history per session
conversation_history = {}

def get_session_id():
    """Get a unique session ID for the current user session"""
    if 'session_id' not in session:
        session['session_id'] = os.urandom(8).hex()
        logger.info(f"New session created: {session['session_id']}")
        
        # Audit log for new session
        user = session.get('user_id', 'anonymous')
        logger.audit(f"New chat session started by user '{user}' with session_id {session['session_id']}")
    else:
        logger.debug(f"Using existing session: {session['session_id']}")
    return session['session_id']

@log_performance(logger)
def generate_response(user_message):
    """Generate a response using the OpenAI API"""
    session_id = get_session_id()
    user = session.get('user_id', 'anonymous')
    message_length = len(user_message)
    
    logger.info(f"Generating response for user '{user}', message length: {message_length} chars")
    
    # Generate system prompt if needed (first message)
    if session_id not in conversation_history:
        system_prompt = create_system_prompt()
        conversation_history[session_id] = [{"role": "system", "content": system_prompt}]
        logger.info(f"Initialized conversation history for session: {session_id}")
        
        # Log message count statistics
        logger.audit(f"New conversation started by user '{user}' with session_id {session_id}")
    else:
        logger.debug(f"Retrieved existing conversation history for session: {session_id}")
    
    # Record message stats
    messages_before = len(conversation_history[session_id])
    
    # Get history and add user message
    history = conversation_history[session_id]
    history.append({"role": "user", "content": user_message})
    
    # Truncate message if too long for logging
    log_message = user_message
    if len(log_message) > 500:
        log_message = f"{log_message[:500]}... [truncated, total {len(user_message)} chars]"
    
    logger.info(f"User message: {log_message}")
    logger.debug(f"Conversation history length: {len(history)} messages")
    
    # Track token counts and API usage for cost monitoring
    start_time = time.time()
    
    try:
        # Call OpenAI API
        logger.debug(f"Calling OpenAI API with model {OPENAI_MODEL}, temperature {TEMPERATURE}")
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=history,
            temperature=TEMPERATURE
        )
        
        # Calculate API call duration
        api_duration = (time.time() - start_time) * 1000  # ms
        
        # Get token usage if available - properly access CompletionUsage object
        prompt_tokens = 0
        completion_tokens = 0
        total_tokens = 0
        
        if hasattr(response, 'usage'):
            # Access usage attributes directly, not with .get()
            prompt_tokens = getattr(response.usage, 'prompt_tokens', 0)
            completion_tokens = getattr(response.usage, 'completion_tokens', 0)
            total_tokens = getattr(response.usage, 'total_tokens', 0)
        
        # Get and log the response
        bot_reply = response.choices[0].message.content.strip()
        reply_length = len(bot_reply)
        
        # Add to history
        history.append({"role": "assistant", "content": bot_reply})
        
        # Truncate for logging
        log_reply = bot_reply
        if len(log_reply) > 500:
            log_reply = f"{log_reply[:500]}... [truncated, total {reply_length} chars]"
        
        logger.debug(f"Response generated: {log_reply}")
        logger.info(f"OpenAI API stats: {api_duration:.2f}ms, {prompt_tokens} prompt tokens, {completion_tokens} completion tokens")
        
        # Audit log for message statistics
        logger.audit(f"Chat interaction: user '{user}' sent {message_length} chars, received {reply_length} chars, used {total_tokens} tokens")
        
        return bot_reply
    except Exception as e:
        error_details = traceback.format_exc()
        logger.error(f"Error generating response: {str(e)}\n{error_details}")
        
        # Audit log for failed API call
        logger.audit(f"Failed API call: user '{user}' message of {message_length} chars triggered error: {str(e)}")
        
        bot_reply = f"I'm sorry, I encountered an error: {e}"
        return bot_reply

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