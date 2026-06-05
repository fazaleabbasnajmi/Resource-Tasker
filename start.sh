#!/bin/bash
# Resource Tasker - Start Script
# Run this to start the application on your local intranet

cd "$(dirname "$0")"

# Activate virtual environment
source venv/bin/activate

echo "========================================"
echo "  Resource Tasker - Starting Server"
echo "========================================"
echo ""
echo "  URL: http://localhost:8080"
echo ""
echo "  Default accounts:"
echo "  Manager: admin / admin123"
echo "  User:    jdoe  / user123"
echo "  User:    asmith / user123"
echo ""
echo "  To access from other devices on your"
echo "  local network, use:"
IP=$(ipconfig getifaddr en0 2>/dev/null || hostname -I 2>/dev/null | awk '{print $1}')
echo "  http://$IP:8080"
echo ""
echo "  Press Ctrl+C to stop."
echo "========================================"
echo ""

python app.py

