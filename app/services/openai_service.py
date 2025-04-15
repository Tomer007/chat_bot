import os
import openai
from flask import current_app

# Initialize the OpenAI client
openai.api_key = os.environ.get("OPENAI_API_KEY")

def get_openai_response(messages, model="gpt-4"):
    """
    Get a response from the OpenAI API
    
    Args:
        messages (list): A list of message objects with role and content
        model (str): The model to use for the API call
        
    Returns:
        str: The response content from the OpenAI API
    """
    try:
        # Make the API call
        response = openai.ChatCompletion.create(
            model=model,
            messages=messages,
            max_tokens=1000,
            temperature=0.7
        )
        
        # Extract and return the response content
        return response.choices[0].message.content
    except Exception as e:
        current_app.logger.error(f"Error calling OpenAI API: {str(e)}")
        return "I'm sorry, I encountered an error processing your request. Please try again."

def analyze_personality(user_input, context=""):
    """
    Analyze the user's personality based on their input
    
    Args:
        user_input (str): The user's message to analyze
        context (str): Additional context about the assessment stage
        
    Returns:
        str: Analysis of the user's personality traits
    """
    system_prompt = f"""
    You are a personality assessment expert analyzing responses for the PDN personality framework.
    {context}
    Provide a concise analysis of the key personality traits evident in the user's response.
    Keep your analysis brief and focused only on identifying dominant traits.
    """
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_input}
    ]
    
    return get_openai_response(messages)

def generate_personality_description(pdn_code):
    """
    Generate a personalized description for a PDN personality code
    
    Args:
        pdn_code (str): The three-letter PDN code (e.g., ASN, EFC)
        
    Returns:
        str: A detailed description of the personality type
    """
    prompt = f"""
    Generate a detailed, personalized description for someone with the PDN personality code {pdn_code}.
    
    Break down the description into these sections:
    1. Overview of the type
    2. Key strengths
    3. Potential challenges
    4. Communication style
    5. Work style and preferences
    6. Relationship patterns
    7. Growth opportunities
    
    Make the description nuanced, insightful, and helpful for self-understanding.
    """
    
    messages = [
        {"role": "system", "content": "You are an expert personality assessment coach helping someone understand their PDN personality type."},
        {"role": "user", "content": prompt}
    ]
    
    return get_openai_response(messages, model="gpt-4") 