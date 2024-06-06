#!/bin/bash

# Activate the Virtual environment
source venv/bin/activate

#Run the before first request
python3 app.py

# Start the server
gunicorn -w 4 -b 127.0.0.1:8000 wsgi:app