#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Define variables
APP_DIR="$(pwd)"
VENV_DIR="$APP_DIR/venv"
REQUIREMENTS_FILE="$APP_DIR/requirements.txt"
NGINX_CONFIG_FILE="/etc/nginx/sites-available/SMS-Notifier"
NGINX_ENABLED_FILE="/etc/nginx/sites-enabled/SMS-Notifier"
DOMAIN_OR_IP=$(curl -s ifconfig.co)

echo "Installing SMS-Notifier..."

# Install virtualenv if not installed
echo "Installing virtualenv..."
sudo apt install python3-virtualenv

# Create a virtual environment
echo "Creating virtual environment..."
virtualenv $VENV_DIR

# Activate the virtual environment
echo "Activating virtual environment..."
source $VENV_DIR/bin/activate

# Install required packages from requirements.txt
echo "Installing required packages..."
pip3 install -r $REQUIREMENTS_FILE

# Generate random strings for SECRET_KEY and LOG_TOKEN
echo "Creating config.py with the API Tokens..."
SECRET_KEY=$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 20 | head -n 1)
LOG_TOKEN=$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 20 | head -n 1)

# Update config.py with the generated strings
cat << EOF > app/config.py
class Config:
    DEBUG = True  # Set to False for production
    SECRET_KEY = '$SECRET_KEY'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///app.db'
    LOG_TOKEN = '$LOG_TOKEN'
EOF

echo "Config.py created successfully."


# Deactivating the Virtual ENV
deactivate
echo "Deactivataed the virtual environment..."

# Install Nginx
echo "Installing Nginx..."
sudo apt update
sudo apt install -y nginx

# Check if Nginx configuration file already exists
if [ ! -f "$NGINX_CONFIG_FILE" ]; then
    # Create Nginx configuration file
    echo "Creating Nginx configuration file..."
    sudo tee "$NGINX_CONFIG_FILE" > /dev/null <<EOL
    server {
        listen 80;
        server_name $DOMAIN_OR_IP;

        location / {
            proxy_pass http://127.0.0.1:8000;
            proxy_set_header Host \$host;
            proxy_set_header X-Real-IP \$remote_addr;
            proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        }
    }
EOL
else
    echo "Nginx configuration file already exists."
fi

# Enable Nginx configuration by creating a symbolic link
echo "Enabling Nginx configuration..."
sudo ln -sf $NGINX_CONFIG_FILE $NGINX_ENABLED_FILE

# Test Nginx configuration
echo "Testing Nginx configuration..."
sudo nginx -t

# Restart Nginx to apply changes
echo "Restarting Nginx..."
sudo systemctl restart nginx

echo "Setup complete!"
