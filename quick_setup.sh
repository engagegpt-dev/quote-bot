#!/bin/bash

# Quick VPS Setup Script for Quote Retweet Bot
# Tested on Ubuntu 22.04 LTS

echo "🚀 Quick Setup for Quote Retweet Bot VPS"
echo "========================================"

# Update system
echo "📦 Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install Python and pip
echo "🐍 Installing Python..."
sudo apt install -y python3 python3-pip python3-venv

# Install system dependencies for Playwright
echo "🎭 Installing Playwright system dependencies..."
sudo apt install -y \
    libnss3-dev \
    libatk-bridge2.0-dev \
    libdrm-dev \
    libxcomposite-dev \
    libxdamage-dev \
    libxrandr-dev \
    libgbm-dev \
    libxss-dev \
    libasound2-dev \
    libxshmfence-dev

# Create project directory
echo "📁 Creating project directory..."
mkdir -p ~/quote-bot
cd ~/quote-bot

# Create virtual environment
echo "🔧 Setting up Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install Python packages
echo "📚 Installing Python packages..."
pip install --upgrade pip
pip install playwright fastapi uvicorn httpx pydantic python-multipart

# Install Playwright browsers
echo "🌐 Installing Playwright browsers..."
playwright install chromium
playwright install-deps

# Test installation
echo "🧪 Testing installation..."
python3 -c "
import asyncio
from playwright.async_api import async_playwright

async def test():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto('https://httpbin.org/get')
        print('✅ Playwright test successful!')
        await browser.close()

asyncio.run(test())
"

# Setup firewall
echo "🔒 Configuring firewall..."
sudo ufw allow 8000
sudo ufw allow 22
sudo ufw --force enable

# Create systemd service
echo "⚙️ Creating systemd service..."
sudo tee /etc/systemd/system/quote-bot.service > /dev/null <<EOF
[Unit]
Description=Quote Retweet Bot API
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$HOME/quote-bot
Environment=PATH=$HOME/quote-bot/venv/bin
ExecStart=$HOME/quote-bot/venv/bin/python api_server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

echo "✅ Setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Upload your bot files to ~/quote-bot/"
echo "2. Start the service: sudo systemctl start quote-bot"
echo "3. Enable auto-start: sudo systemctl enable quote-bot"
echo "4. Check status: sudo systemctl status quote-bot"
echo ""
echo "🌐 Your API will be available at: http://$(curl -s ifconfig.me):8000"