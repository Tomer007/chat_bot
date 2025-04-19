import logging
import os
import sys
import time
import uuid
from functools import wraps
from logging.handlers import RotatingFileHandler

from flask import request, g, session, has_request_context

from app.config import LOG_FOLDER

# Custom log levels
AUDIT = 25  # Between WARNING (30) and INFO (20)
logging.addLevelName(AUDIT, "AUDIT")


# Add audit method to Logger class (applies to all loggers including RootLogger)
def audit_log(self, message, *args, **kwargs):
    """Log at AUDIT level (25)"""
    if self.isEnabledFor(AUDIT):
        self._log(AUDIT, message, args, **kwargs)


# Add the audit method to the Logger class
logging.Logger.audit = audit_log


class ContextualLogger(logging.Logger):
    """Extended logger class that adds context to log messages"""

    def _add_context(self, msg):
        """Add contextual information to log messages"""
        # Only attempt to access Flask request context if we're in a request
        if not has_request_context():
            return msg

        context = {}

        # Add request info if available
        context['ip'] = request.remote_addr
        context['method'] = request.method
        context['path'] = request.path

        # Add session/user info if available
        try:
            context['session_id'] = session.get('session_id', 'none')
            context['user'] = session.get('user_id', 'anonymous')
        except RuntimeError:
            # Session might not be available
            pass

        # Add request ID if available
        if hasattr(g, 'request_id'):
            context['request_id'] = g.request_id

        # Format the context as a string
        if context:
            context_str = ' '.join([f"{k}={v}" for k, v in context.items()])
            return f"{msg} - [{context_str}]"
        return msg

    def info(self, msg, *args, **kwargs):
        """Log with context at INFO level"""
        msg = self._add_context(msg)
        super().info(msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        """Log with context at ERROR level"""
        msg = self._add_context(msg)
        super().error(msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        """Log with context at WARNING level"""
        msg = self._add_context(msg)
        super().warning(msg, *args, **kwargs)

    def debug(self, msg, *args, **kwargs):
        """Log with context at DEBUG level"""
        msg = self._add_context(msg)
        super().debug(msg, *args, **kwargs)

    def critical(self, msg, *args, **kwargs):
        """Log with context at CRITICAL level"""
        msg = self._add_context(msg)
        super().critical(msg, *args, **kwargs)

    def audit(self, msg, *args, **kwargs):
        """Log with context at AUDIT level"""
        msg = self._add_context(msg)
        super().audit(msg, *args, **kwargs)


def log_performance(logger):
    """Decorator to log function performance metrics"""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()

            # Get function name and arguments for logging
            func_name = func.__name__
            arg_str = ', '.join([str(arg) for arg in args])
            kwarg_str = ', '.join([f"{k}={v}" for k, v in kwargs.items()])
            call_str = f"{func_name}({arg_str}{', ' if arg_str and kwarg_str else ''}{kwarg_str})"

            logger.debug(f"Starting {call_str}")

            try:
                # Execute the function
                result = func(*args, **kwargs)

                # Calculate execution time
                execution_time = (time.time() - start_time) * 1000  # Convert to milliseconds

                # Log success
                logger.debug(f"Completed {func_name} in {execution_time:.2f}ms")

                return result

            except Exception as e:
                # Log failure
                execution_time = (time.time() - start_time) * 1000
                logger.error(f"Failed {func_name} after {execution_time:.2f}ms: {str(e)}")
                raise

        return wrapper

    return decorator


def setup_logger():
    """
    Set up logging configuration for the application.
    Logs to console and multiple files with different formats.
    """
    # Register the custom logger class
    logging.setLoggerClass(ContextualLogger)

    # Create logs directory if it doesn't exist
    os.makedirs(LOG_FOLDER, exist_ok=True)

    # Get log level from environment variable (default to INFO)
    log_level_name = os.environ.get('LOG_LEVEL', 'INFO').upper()
    log_level = getattr(logging, log_level_name, logging.INFO)

    # Create a new logger instance
    logger = logging.getLogger('app')
    logger.setLevel(log_level)

    # Remove existing handlers to avoid duplicates when reloading
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Create formatters
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_formatter = logging.Formatter(
        '%(levelname)s: %(message)s'
    )

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)  # Use same level as logger
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # Add file handlers in development mode
    if os.environ.get('FLASK_ENV') != 'production':
        # Debug log file
        debug_handler = RotatingFileHandler(
            os.path.join(LOG_FOLDER, 'debug.log'),
            maxBytes=10485760,
            backupCount=5
        )
        debug_handler.setLevel(logging.DEBUG)
        debug_handler.setFormatter(file_formatter)
        logger.addHandler(debug_handler)

    return logger


# Create and configure the logger
logger = setup_logger()


# Function to generate a unique request ID
def generate_request_id():
    """Generate a unique request ID"""
    return str(uuid.uuid4())
