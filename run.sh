#!/bin/bash

# Activate the Virtual environment
source venv/bin/activate
#!/bin/bash

# Start a new screen session
screen -dmS Notifier

# Send the command to run your Python app in the screen session
clear
screen -S Notifier -X stuff "python3 run.py$(printf \\r)"

# Attach to the screen session to interact with the Python app
screen -r Notifier
