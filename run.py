import os
from app import create_app
from app.config import DEBUG, PORT

# Use a different port if the default is in use
app = create_app()

if __name__ == '__main__':
    # Try to use the configured PORT, but fall back to 5050 if it's in use
    port_to_use = PORT
    
    # Check if running in development mode
    if DEBUG:
        print(f"Starting development server on port {port_to_use}...")
        app.run(debug=DEBUG, port=port_to_use)
    else:
        print(f"Starting production server on port {port_to_use}...")
        app.run(host='0.0.0.0', port=port_to_use) 