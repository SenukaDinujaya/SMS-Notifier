#!/bin/bash

# Activate the Virtual environment
source venv/bin/activate

#Run the before first request
python3 app.py

# Start the server
# If you are changing the port you have to change it in the setup.sh and in the log.py as well
gunicorn -w 4 -b 127.0.0.1:8000 wsgi:app