import os
import re
import time
import traceback

from flask import session, url_for
from openai import OpenAI

from app.config import OPENAI_MODEL, TEMPERATURE, OPENAI_API_KEY, RAG_FILE, PROMPTS_FOLDER
from app.services.document_service import load_and_chunk_document
from app.services.stage_service import (
    get_current_stage,
    load_stage_prompt,
    get_history,
    store_assessment_data,
    set_stage,
    STAGES
)
from app.utils.logging_config import logger, log_performance

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

# Define the stages and their corresponding prompt files
PROMPT_STAGES = {
    "apvset": os.path.join(PROMPTS_FOLDER, "step_1_ap_et_distinction.txt"),
    "personality": os.path.join(PROMPTS_FOLDER, "step_2_personality_types.txt"),
    "energy": os.path.join(PROMPTS_FOLDER, "step_3_energy.txt"),
    "reinforcement": os.path.join(PROMPTS_FOLDER, "step_4_reinforcement_childhood_fear.txt"),
    "final": os.path.join(PROMPTS_FOLDER, "step_5_final_code_summary.txt")
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
            logger.debug(f"Prompt loaded for stage '{stage}': {len(prompt)} characters")
            return prompt
    except Exception as e:
        error_details = traceback.format_exc()
        logger.error(f"Error loading prompt file for stage '{stage}': {str(e)}\n{error_details}")
        raise


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


def get_session_id():
    """Get a unique session ID for the current user session"""
    if 'session_id' not in session:
        session['session_id'] = os.urandom(8).hex()
        logger.info(f"New session created: {session['session_id']}")

        # Initialize stage for new session
        set_stage("apvset")  # Start with the first stage

        # Initialize history
        if 'history' not in session:
            session['history'] = []

        # Audit log for new session
        user = session.get('user_id', 'anonymous')
        logger.audit(f"New chat session started by user '{user}' with session_id {session['session_id']}")

    return session['session_id']


def get_current_stage(session_id=None):
    """Get the current stage for a session"""
    sid = session_id or get_session_id()
    return session.get('stage', "apvset")


def handle_post_completion_action(user_message):
    """Handle user actions after assessment completion"""
    message = user_message.lower().strip()

    try:
        if message == "review":
            # Get all messages except system messages
            history = get_history()
            review = "**Your Assessment Journey**\n\n"
            for msg in history:
                if msg['role'] != 'system':
                    timestamp = msg['timestamp']
                    role = "👤 You" if msg['role'] == 'user' else "🤖 Assistant"
                    review += f"**{role}** ({timestamp}):\n{msg['content']}\n\n"

            return review

        elif message == "save":
            # Get the saved report
            assessment_data = session.get('assessment_data', {})
            final_report = assessment_data.get('final_report', '')

            if final_report:
                # The report is already saved in the assessment results folder
                return """Your report has already been saved! You can find it in your assessment results folder.

Need anything else? You can:
- Review your responses (type "review")
- Exit to login page (type "done")
- Or just ask me any questions about your results!"""
            else:
                return "⚠️ Sorry, I couldn't find your final report. You might need to complete the assessment first."

        elif message == "done":
            # Clear the session
            session.clear()
            session.modified = True

            # Return special message that will trigger redirect
            return "REDIRECT_TO_LOGIN"

        else:
            return None  # Let the normal message handling take over

    except Exception as e:
        logger.error(f"Error handling post-completion action: {str(e)}")
        return "⚠️ Sorry, there was an error processing your request. Please try again."


def detect_language(text):
    """
    Detect if text is primarily Hebrew or English.
    Returns 'he' for Hebrew, 'en' for English
    """
    # Hebrew Unicode range
    hebrew_pattern = re.compile(r'[\u0590-\u05FF]')

    # Count Hebrew characters
    hebrew_count = len(hebrew_pattern.findall(text))

    # If more than 20% of characters are Hebrew, consider it Hebrew
    return 'he' if hebrew_count > len(text) * 0.2 else 'en'


@log_performance(logger)
def generate_response(user_message, stage=None):
    """Generate a response using the OpenAI API for the current stage"""
    try:
        # Detect language of user message
        user_language = detect_language(user_message)
        logger.debug(f"Detected language: {user_language}")

        # Store language in session if not already set
        if 'language' not in session:
            session['language'] = user_language
            session.modified = True

        # Check if assessment is completed and handle post-completion actions
        if session.get('assessment_completed', False):
            post_completion_response = handle_post_completion_action(user_message)
            if post_completion_response:
                return post_completion_response

        # Get current stage info
        current_stage = session.get('stage', "apvset")
        stage_info = STAGES[current_stage]
        logger.debug(f"Current stage: {current_stage}")

        # Get or initialize history
        history = get_history()
        if history is None:
            history = []
            session['history'] = history
            logger.debug("Initialized empty history list")

        logger.debug(f"Current history before processing: {history}")

        # Initialize with system prompt if this is the first message
        if not history:
            initialize_history(current_stage, history, stage_info)
            logger.debug(f"History after initialization: {history}")

        # Add user message to history with timestamp
        add_message_to_history(history, user_message, "user")
        logger.debug(f"History after adding user message: {history}")

        # Call OpenAI API
        start_time = time.time()
        try:
            # Get stage prompt
            stage_prompt = load_stage_prompt()
            system_content = stage_prompt + f"\n\nRemember to format your response with proper Markdown, and clear structure. Use bold for emphasis, proper spacing. IMPORTANT: Always respond in the same language as the user's input ({user_language}). If the user writes in Hebrew, respond in Hebrew. If the user writes in English, respond in English."

            # Include recent history for context
            messages = [
                {
                    "role": "system",
                    "content": system_content
                }
            ]

            # Add recent history (last 4 messages) for context
            recent_history = history[-4:] if len(history) > 0 else []
            for entry in recent_history:
                if entry.get('role') in ['user', 'assistant']:
                    messages.append({
                        "role": entry['role'],
                        "content": entry['content']
                    })

            # Add current message
            messages.append({
                "role": "user",
                "content": user_message
            })

            logger.debug(f"Sending messages to API: {messages}")
        except Exception as e:
            logger.error(f"Error preparing messages: {str(e)}")
            raise

        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            temperature=TEMPERATURE
        )
        api_time = time.time() - start_time

        # Get and format the response
        bot_reply = response.choices[0].message.content.strip()

        logger.debug(f"Bot reply before processing: {bot_reply}")

        # Process stage advancement and data storage as before...
        advance_stage = False
        if "ADVANCE_STAGE" in bot_reply:
            logger.debug(f"Found ADVANCE_STAGE marker in response")
            # Remove ADVANCE_STAGE from visible response
            bot_reply = bot_reply.replace("ADVANCE_STAGE", "").strip()
            advance_stage = True

        # Add the bot's response to history with timestamp
        add_message_to_history(history, bot_reply, "assistant")

        if advance_stage:
            next_stage = stage_info['next']
            if next_stage:
                logger.debug(f"Attempting to advance to stage: {next_stage}")

                # Save current stage results before advancing
                success_save, filepath = store_assessment_data("stage_complete", current_stage)
                if success_save:
                    logger.info(f"Saved assessment results for stage {current_stage} to {filepath}")
                else:
                    logger.error(f"Failed to save assessment results for stage {current_stage}")

                success, message = set_stage(next_stage)
                if success:
                    new_stage_info = STAGES[next_stage]
                    logger.info(f"Advanced to stage: {new_stage_info['name']}")

                    # Special handling for final stage
                    if next_stage == 'final':
                        logger.info("Generating final report")
                        # Load all assessment data
                        assessment_data = session.get('assessment_data', {})
                        # Create a message for final report generation
                        final_messages = [
                            {
                                "role": "system",
                                "content": load_stage_prompt('final')
                            }
                        ]

                        # Generate final report
                        final_response = client.chat.completions.create(
                            model=OPENAI_MODEL,
                            messages=final_messages,
                            temperature=TEMPERATURE
                        )

                        final_report = final_response.choices[0].message.content.strip()
                        add_message_to_history(history, final_report, "assistant")

                        # Save the final report in the assessment data
                        store_assessment_data("final_report", final_report)

                        # Return special response to trigger redirect
                        return {
                            'status': 'redirect',
                            'redirect_url': url_for('chat.view_report'),
                            'message': 'final_report'
                        }
                    else:
                        # Normal stage advancement
                        # Load the new stage's prompt
                        new_stage_prompt = load_stage_prompt(next_stage)
                        logger.debug(f"Loaded new stage prompt for {next_stage}")

                        # Add system message with new stage prompt
                        add_message_to_history(history, new_stage_prompt, "system")

                        # Update session with new stage
                        session['stage'] = next_stage
                        session.modified = True
                        logger.debug(f"Updated session stage to: {next_stage}")

                        # Generate first question of new stage
                        try:
                            # Create messages for the new stage
                            messages = [
                                {
                                    "role": "system",
                                    "content": new_stage_prompt + "\n\nRemember to format your response with proper Markdown, emojis, and clear structure. Use bold for emphasis, proper spacing, and emoji numbers for options."
                                },
                                {
                                    "role": "user",
                                    "content": "start"  # Trigger initial question
                                }
                            ]

                            # Get first question from OpenAI
                            first_response = client.chat.completions.create(
                                model=OPENAI_MODEL,
                                messages=messages,
                                temperature=TEMPERATURE
                            )

                            # Get and format the first question
                            first_question = first_response.choices[0].message.content.strip()

                            # Add the first question to history
                            add_message_to_history(history, first_question, "assistant")

                            # Return combined response with transition and first question
                            bot_reply = f"{bot_reply}\n\n{first_question}"

                        except Exception as e:
                            logger.error(f"Error generating first question of new stage: {str(e)}")
                            # Continue with original response if error occurs
                else:
                    logger.error(f"Failed to advance stage: {message}")

        logger.info(f"Generated response ({len(bot_reply)} chars) in {api_time:.2f}s")
        return bot_reply

    except Exception as e:
        error_details = traceback.format_exc()
        logger.error(f"Error generating response: {str(e)}\n{error_details}")
        return "⚠️ **Error:** I encountered an issue processing your request. Please try again."


def add_message_to_history(history, message, role):
    """Add a message to the conversation history and save to session"""
    if not isinstance(history, list):
        logger.warning(f"History is not a list, initializing new list. Current history: {history}")
        history = []
        session['history'] = history

    message_entry = {
        "role": role,
        "content": message,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    if role == "system":
        message_entry["stage"] = session.get('stage')

    history.append(message_entry)
    session['history'] = history
    logger.debug(f"Added {role} message to history. Current history: {history}")


def initialize_history(current_stage, history, stage_info):
    """Initialize conversation history with system prompt"""
    if not isinstance(history, list):
        logger.warning(f"History is not a list during initialization. Current history: {history}")
        history = []
        session['history'] = history

    stage_prompt = load_stage_prompt()
    add_message_to_history(history, stage_prompt, "system")
    logger.info(f"Initialized conversation for stage: {stage_info['name']}")


def get_session_info():
    """Get comprehensive information about the current session"""
    stage_data = get_current_stage()
    history = get_history()

    return {
        "session_id": session.get('session_id', 'unknown'),
        "user": session.get('user_id', 'unknown'),
        "stage": stage_data,
        "history_length": len(history) if history else 0,
        "last_message": history[-1] if history and len(history) > 0 else None
    }
