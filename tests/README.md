# Chat+Bot Tests

This directory contains tests for the Chat+Bot application, covering all backend endpoints and functionality.

## Test Structure

- `conftest.py`: Contains pytest fixtures used across all tests
- `test_auth_routes.py`: Tests for authentication routes (login, logout, etc.)
- `test_chat_routes.py`: Tests for chat and file upload functionality
- `test_document_processing.py`: Tests for document text extraction

## Running Tests

To run all tests:

```bash
# From the project root directory
pytest -v

# Using the helper script (also starts app if tests pass)
python run_tests_and_app.py
```

To run a specific test file:

```bash
pytest -v tests/test_auth_routes.py
```

To run a specific test:

```bash
pytest -v tests/test_auth_routes.py::test_login_post_success
```

## Testing the Refactored Application

The tests were designed to work with the application's modular architecture:

1. The `app/` package contains the application code organized into modules:
   - `routes/`: Contains route blueprints
   - `services/`: Contains business logic 
   - `utils/`: Contains utility functions

2. When running tests:
   - Each test imports from the appropriate module
   - The refactored architecture makes it easier to test individual components
   - Mock objects can be used to isolate components for testing

## Troubleshooting

If you encounter import errors, make sure you're running pytest from the project root directory. The test configuration automatically adds the parent directory to the Python path to make the app modules importable.

If you still have issues, you can explicitly set the Python path:

```bash
PYTHONPATH=. pytest -v
```

## Test Coverage

The tests cover:

1. **Authentication**
   - Login functionality (GET/POST)
   - Logout
   - Session handling and expiration
   - Access control for protected routes

2. **Chat API**
   - Sending text messages
   - File uploads with various formats
   - Error handling
   - Response formatting

3. **Document Processing**
   - Text extraction from TXT files
   - Text extraction from DOCX files
   - Text extraction from PDF files
   - Handling of unsupported file types

## Requirements

Running the tests requires:

1. pytest
2. pytest-mock (for mocking)

You can install them with:

```bash
pip install pytest pytest-mock
```

## Environment Variables

Tests use mocked environment variables. If you need to test with specific environment variables, create a `.env.test` file and load it in `conftest.py`. 