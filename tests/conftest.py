"""
Test Configuration and Fixtures for Chat+Bot Application.

This module provides the pytest fixtures and configuration needed for testing the Chat+Bot
application. It includes fixtures for creating:
- A test Flask application instance
- Test clients (both authenticated and non-authenticated)
- Mock environment and session data

These fixtures are automatically available to all test modules in this directory.
"""

import os
import sys
import yaml
import pytest
from datetime import timedelta
from unittest.mock import patch, mock_open

# Add the parent directory to the path so we can import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the Flask app from the new app structure
from app import app as flask_app


@pytest.fixture
def mock_chatbot_config():
    """Create a mock chatbot config."""
    config_data = {
        "chatbots": {
            "default": {
                "name": "default",
                "title": "Test Chatbot",
                "description": "Test description",
                "welcome_message": "Hello from test",
                "contact_email": "test@example.com",
                "version": "1.0.0"
            }
        }
    }
    return yaml.dump(config_data)


@pytest.fixture
def app(mock_chatbot_config):
    """Create and configure a Flask app for testing."""
    # Set test configuration
    flask_app.config.update({
        "TESTING": True,
        "SECRET_KEY": "test_secret_key",
        "PERMANENT_SESSION_LIFETIME": timedelta(minutes=5),  # Use timedelta not int
    })
    
    # Create temp environment for testing
    os.environ["CHATBOT_NAME"] = "default"
    
    # Mock the config file
    with patch("builtins.open", mock_open(read_data=mock_chatbot_config)):
        yield flask_app


@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()


@pytest.fixture
def authenticated_client(client):
    """A test client that's authenticated."""
    with client.session_transaction() as session:
        session["user_id"] = "test_user"
        session["last_activity"] = "2023-01-01T00:00:00"
    
    return client 