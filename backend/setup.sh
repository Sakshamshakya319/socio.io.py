#!/bin/bash

# Setup script for local development

# Install Node.js dependencies
echo "Installing Node.js dependencies..."
npm install

# Install Python dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt

echo "Setup complete! You can now run the application with:"
echo "npm run dev"
echo ""
echo "Or start the services separately:"
echo "- Node.js server: npm start"
echo "- Python server: python flask_server.py"