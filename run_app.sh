#!/bin/bash

# Set colors for better readability
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Running tests before starting the app...${NC}"
echo -e "${BLUE}========================================${NC}"

# Run pytest with more readable output
python -m pytest -v

# Check if tests were successful
if [ $? -eq 0 ]; then
    echo -e "\n${GREEN}✓ All tests passed!${NC}"
    echo -e "${GREEN}✓ Starting the application...${NC}\n"
    
    # Start the Flask application
    python app.py
else
    echo -e "\n${RED}✗ Tests failed. Please fix the issues before running the app.${NC}"
    echo -e "${YELLOW}Hint: Check the test output above for details.${NC}\n"
    exit 1
fi 