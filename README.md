# PDN Personality Assessment Chatbot

A conversational chatbot that guides users through the Personality Distinction Numbering (PDN) assessment - a comprehensive personality typing system.

## Overview

The PDN Personality Assessment Chatbot is a Flask-based application that helps users discover their unique personality type through an interactive conversation. The assessment evaluates three key dimensions:

1. **Primary Type (A, E, T, or P)** - Your foundational personality orientation
2. **Energy Pattern (D, S, or F)** - How you direct and express your energy
3. **Reinforcement Pattern (N, C, or I)** - How you strengthen yourself and others

These three elements combine to create a three-letter PDN code that represents your unique personality profile.

## Features

- Stepwise assessment process with conversational interface
- Detailed personality descriptions for each type
- AI-powered analysis of free-text responses
- Session management for assessment progress
- Comprehensive explanations of personality traits and tendencies

## Project Structure

```
chat_bot/
├── app/
│   ├── __init__.py
│   ├── config.py              # Application configuration
│   ├── routes/               # API routes
│   ├── services/             # Business logic
│   │   ├── chat_service.py   # Chat handling
│   │   ├── stage_service.py  # Stage management
│   │   └── document_service.py
│   └── utils/                # Utility functions
├── static/
│   ├── css/                  # Stylesheets
│   └── js/                   # JavaScript files
├── templates/                # HTML templates
├── prompts/                  # Assessment stage prompts
│   ├── 1-AP-vs-ET-Distinction.txt
│   ├── 2-Personality-Types-AETP.txt
│   ├── 3-Energy-Questions-DSF.txt
│   ├── 4-Reinforcement-Childhood-Fears.txt
│   └── 5-Final-Code-Reveal-Summary.txt
├── assessment_results/       # Stored assessment results
├── uploads/                  # File upload directory
├── logs/                    # Application logs
├── sessions/                # Flask session files
├── tests/                   # Test files
└── config/                  # Configuration files
    └── config.yaml          # Additional configuration
```

## Configuration

### Environment Variables (.env)

```env
FLASK_DEBUG=True
FLASK_PORT=5000
FLASK_SECRET_KEY=your-secret-key-here
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-4
TEMPERATURE=0.7
SESSION_LIFETIME_DAYS=7
```

### Directory Configuration

The application automatically creates and manages the following directories:
- `uploads/`: For file uploads
- `logs/`: Application logs
- `assessment_results/`: Assessment result files
- `sessions/`: Flask session files

## Assessment Stages

1. **AP vs ET Distinction** (apvset)
   - Initial personality orientation assessment
   - Distinguishes between Analytical-Peaceful and Expressive-Tactical traits

2. **Personality Types** (personality)
   - Detailed personality type assessment
   - AETP framework analysis

3. **Energy Questions** (energy)
   - Energy and decision-making patterns
   - DSF (Decision-Style-Focus) evaluation

4. **Reinforcement Patterns** (reinforcement)
   - Childhood experiences and reinforcement patterns
   - Analysis of formative influences

5. **Final Code Reveal** (final)
   - Summary and personality code revelation
   - Comprehensive analysis and recommendations

## Assessment Results

Results are saved automatically after each stage and stored in JSON format:
- Filename format: `assessment_username_YYYYMMDD_HHMMSS.json`
- Includes:
  - User information
  - Stage progression
  - Conversation history
  - Assessment data
  - Timestamps for all interactions

## Getting Started

### Prerequisites

- Python 3.8 or higher
- OpenAI API key
- Redis (optional, for test configuration)

### Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/pdn-chatbot.git
   cd pdn-chatbot
   ```

2. Create and activate a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install the dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Create a `.env` file in the project root with the following variables:
   ```
   SECRET_KEY=your_secret_key
   OPENAI_API_KEY=your_openai_api_key
   DEBUG=True
   PORT=5000
   SESSION_LIFETIME=3600
   ```

### Running the Application

1. Start the Flask development server:
   ```
   python run.py
   ```

2. Access the application in your web browser at `http://localhost:5000`

## API Endpoints

### `/chat/start_assessment` (POST)
Initializes a new personality assessment session.

**Response:**
```json
{
  "message": "Welcome message",
  "assessment_stage": "introduction"
}
```

### `/chat/send_message` (POST)
Processes a user message in the assessment.

**Request:**
```json
{
  "message": "User message text"
}
```

**Response:**
```json
{
  "message": "Assistant response",
  "assessment_stage": "current_stage"
}
```

### `/chat/reset` (POST)
Resets the assessment session.

**Response:**
```json
{
  "message": "Assessment reset successfully"
}
```

## The PDN Assessment Process

1. **Analytical-Peaceful vs. Expressive-Tactical Distinction**
   - Determine your broad orientation (AP or ET)

2. **Primary Type Identification (A, E, T, or P)**
   - Analytical: Methodical, detail-oriented, valuing precision
   - Expressive: People-oriented, enthusiastic, valuing connection
   - Tactical: Action-oriented, practical, valuing efficiency
   - Peaceful: Harmony-seeking, patient, valuing stability

3. **Energy Pattern Identification (D, S, or F)**
   - Dominant: Forward, assertive, taking charge
   - Steady: Consistent, reliable, creating stability
   - Flexible: Adaptable, responsive, adjusting with agility

4. **Reinforcement Pattern Identification (N, C, or I)**
   - Nurturing: Supportive, compassionate, strengthening through care
   - Challenging: Growth-oriented, improvement-focused, high standards
   - Inspiring: Uplifting, possibility-focused, strengthening through vision

## Troubleshooting

### Common Issues and Solutions

#### Application Startup Issues

1. **Application fails to start**
   ```
   Error: No module named 'flask'
   ```
   **Solution:**
   - Ensure virtual environment is activated
   - Reinstall dependencies: `pip install -r requirements.txt`
   - Check Python version compatibility (3.8+ required)

2. **OpenAI API errors**
   ```
   openai.error.AuthenticationError: Invalid API key
   ```
   **Solution:**
   - Verify OPENAI_API_KEY in .env file
   - Check API key validity in OpenAI dashboard
   - Ensure no whitespace in API key

3. **Directory permissions**
   ```
   PermissionError: [Errno 13] Permission denied: '/path/to/directory'
   ```
   **Solution:**
   - Check directory permissions: `ls -la`
   - Grant necessary permissions: `chmod 755 directory_name`
   - Verify user has write access to required directories

#### Assessment Issues

1. **Session not persisting**
   - Check SESSION_LIFETIME_DAYS in .env
   - Verify sessions directory exists and is writable
   - Clear browser cookies and cache
   - Ensure SECRET_KEY is properly set

2. **Assessment results not saving**
   - Verify ASSESSMENT_RESULTS_FOLDER exists and is writable
   - Check disk space availability
   - Ensure user has valid session
   - Check file permissions in assessment_results directory

3. **Stage progression issues**
   - Clear session data: `/chat/reset`
   - Verify prompt files exist in prompts directory
   - Check stage service logs for errors
   - Ensure all stage files are properly formatted

#### Chat Interface Issues

1. **Messages not sending**
   - Check browser console for JavaScript errors
   - Verify WebSocket connection (if applicable)
   - Clear browser cache
   - Check network connectivity

2. **RTL/LTR text display problems**
   - Verify CSS loading properly
   - Check browser language settings
   - Clear browser cache
   - Update to latest browser version

### Logging and Debugging

1. **Enable debug mode**
   ```env
   FLASK_DEBUG=True
   ```

2. **Check application logs**
   - Location: `logs/app.log`
   - View recent logs: `tail -f logs/app.log`
   - Search for errors: `grep "ERROR" logs/app.log`

3. **Debug session data**
   ```python
   # In Python console
   from flask import session
   print(session.get('assessment_data'))
   ```

### Performance Issues

1. **Slow response times**
   - Check OpenAI API latency
   - Monitor system resources
   - Verify database connections (if applicable)
   - Check network connectivity

2. **Memory usage**
   - Monitor process memory: `top` or Task Manager
   - Check for memory leaks
   - Verify file cleanup routines
   - Monitor session size

### System Requirements

1. **Minimum requirements**
   - Python 3.8+
   - 2GB RAM
   - 1GB free disk space
   - Stable internet connection

2. **Recommended setup**
   - Python 3.10+
   - 4GB RAM
   - 5GB free disk space
   - High-speed internet connection

### Getting Help

1. **Support channels**
   - Open GitHub issue
   - Check existing issues
   - Review documentation
   - Contact support team

2. **Useful commands**
   ```bash
   # Check Python version
   python --version

   # Verify dependencies
   pip freeze

   # Check logs
   tail -f logs/app.log

   # Test application
   python -m pytest tests/

   # Clear sessions
   rm -rf sessions/*
   ```

3. **Debug information to provide when reporting issues**
   - Python version
   - Operating system
   - Error messages
   - Log excerpts
   - Steps to reproduce
   - Recent changes made

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- This project uses the PDN personality framework
- Powered by OpenAI's GPT models for natural language understanding

## Contact

[Your Contact Information]