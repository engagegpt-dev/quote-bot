#!/bin/bash

# VPS Deployment Script for Quote Retweet Bot

echo "🚀 Deploying Quote Retweet Bot to VPS..."

# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker and Docker Compose
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.21.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Create project directory
mkdir -p ~/quote-bot-api
cd ~/quote-bot-api

# Copy files (you need to upload these first)
echo "📁 Make sure you've uploaded all project files to ~/quote-bot-api/"

# Build and start services
docker-compose up --build -d

# Show status
docker-compose ps

echo "✅ Deployment complete!"
echo "🌐 API available at: http://your-vps-ip:8000"
echo "📚 API docs at: http://your-vps-ip:8000/docs"

# Setup firewall
sudo ufw allow 8000
sudo ufw allow 80
sudo ufw allow 443
sudo ufw --force enable

echo "🔒 Firewall configured"
echo "🎉 Quote Retweet Bot API is now running!"