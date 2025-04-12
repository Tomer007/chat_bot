# Chat+Bot - AI Chat Assistant

Chat+Bot is a flexible AI-powered chat assistant that integrates retrieval-augmented generation (RAG) capabilities. It features a modern, responsive chat interface with support for both Hebrew and English languages.

## Features

- 🤖 AI-powered conversational assistant with RAG integration
- 🌐 Bilingual support (Hebrew and English)
- 💬 Modern chat interface with RTL support
- 🌙 Dark/Light theme support
- 📱 Responsive design
- 💾 Chat history saving
- 🔄 Real-time typing indicators
- 📄 Document upload and processing (PDF, DOCX, TXT)
- 🔐 User authentication system

## Tech Stack

- Python
- Flask (with Blueprints for modular architecture)
- OpenAI API (GPT-4)
- LangChain
- HTML/CSS/JavaScript
- Render.com for deployment

## Project Structure

```
chat_bot/
│
├── app/                    # Application package
│   ├── routes/             # Route blueprints
│   │   ├── auth.py         # Authentication routes
│   │   └── chat.py         # Chat interface routes
│   │
│   ├── services/           # Business logic
│   │   ├── chat_service.py # Chat functionality
│   │   └── document_service.py # Document processing
│   │
│   ├── utils/              # Utility functions
│   │   └── decorators.py   # Authentication decorators
│   │
│   └── config.py           # Application configuration
│
├── templates/              # HTML templates
│   ├── partials/           # Reusable template parts
│   ├── base.html           # Base template
│   ├── chat.html           # Chat interface
│   └── login.html          # Login page
│
├── static/                 # Static assets (CSS, JS)
│
├── tests/                  # Test suite
│
├── app.py                  # Application entry point
└── run_tests_and_app.py    # Script to run tests and app
```

## Installation

Use a virtual environment
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

1. Clone the repository:
```bash
git clone https://github.com/Tomer007/chat_bot.git
cd chat_bot
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
Create a `.env` file with your OpenAI API key:
```
OPENAI_API_KEY=your_api_key_here
SECRET_KEY=your_secret_key
USER_PASSWORD=your_login_password
CHATBOT_NAME=default
DEBUG=False
```

4. Run the application:
```bash
python app.py
```

5. Run tests and start the application:
```bash
# Using the helper script (recommended)
python run_tests_and_app.py

# Or with a simple command
python -m pytest && python app.py
```

## Deployment
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

The application is configured for easy deployment on Render.com. Simply connect your GitHub repository to Render and deploy using the provided `render.yaml` configuration.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contact

For any questions or support, please contact: contact@oferlevy.co.il 