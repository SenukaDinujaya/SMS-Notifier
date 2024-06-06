#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Define variables
REPO_URL="your_git_repo_url_here"
APP_DIR="/home/SMS-Notifier"
CLONE_DIR= "/home"
VENV_DIR="$APP_DIR/venv"
REQUIREMENTS_FILE="$APP_DIR/requirements.txt"
NGINX_CONFIG_FILE="/etc/nginx/sites-available/SMS-Notifier"
NGINX_ENABLED_FILE="/etc/nginx/sites-enabled/SMS-Notifiers"

echo "Installing SMS-Notifier..."

# Clone the Flask app repository from GitHub
echo "Cloning repository..."
git clone $REPO_URL $CLONE_DIR

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

# Install Nginx
echo "Installing Nginx..."
sudo apt update
sudo apt install -y nginx

# Create Nginx configuration file
echo "Creating Nginx configuration file..."
cat <<EOL | sudo tee $NGINX_CONFIG_FILE
server {
    listen 80;
    server_name your_domain_or_IP;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    }
}
EOL

# Enable Nginx configuration by creating a symbolic link
echo "Enabling Nginx configuration..."
sudo ln -s $NGINX_CONFIG_FILE $NGINX_ENABLED_FILE

# Test Nginx configuration
echo "Testing Nginx configuration..."
sudo nginx -t

# Restart Nginx to apply changes
echo "Restarting Nginx..."
sudo systemctl restart nginx

echo "Setup complete!"
