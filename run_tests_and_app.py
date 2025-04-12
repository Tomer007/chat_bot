#!/usr/bin/env python3
import subprocess
import sys
import os

# Initialize logging before importing app modules
from app.utils.logging_config import logger

def main():
    logger.info("========================================")
    logger.info("Running tests before starting the app...")
    logger.info("========================================")
    
    # Run pytest
    logger.info("Executing pytest")
    test_result = subprocess.run(["python", "-m", "pytest", "-v"], capture_output=False)
    
    # Check exit code
    if test_result.returncode == 0:
        logger.info("✓ All tests passed!")
        logger.info("✓ Starting the application...")
        
        # Start the app using proper Python method rather than subprocess
        try:
            logger.info("Importing app module...")
            # Import after tests to ensure clean app state
            import app
            
            logger.info("Starting app...")
            # Call run_app without Flask context requirements
            if os.environ.get('FLASK_APP') == 'app.py':
                app.app.run(host='0.0.0.0', 
                           port=int(os.environ.get('PORT', 5001)), 
                           debug=os.environ.get('DEBUG', 'False').lower() == 'true')
            else:
                app.run_app()
        except KeyboardInterrupt:
            logger.info("Application stopped by user")
        except Exception as e:
            logger.error(f"Error running application: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            sys.exit(1)
    else:
        logger.error("✗ Tests failed. Please fix the issues before running the app.")
        logger.warning("Hint: Check the test output above for details.")
        sys.exit(1)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"Unhandled exception: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1) 