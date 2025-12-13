#!/bin/bash

# Setup script for GitHub repository

echo "🚀 Setting up Quote Retweet Bot repository..."

# Initialize git if not already done
if [ ! -d ".git" ]; then
    git init
    echo "✅ Git initialized"
fi

# Add remote origin
git remote add origin https://github.com/engagegpt-dev/quote-bot.git 2>/dev/null || echo "Remote already exists"

# Add all files
git add .

# Commit
git commit -m "Initial commit: Quote Retweet Bot with API and Codespaces support"

# Push to main branch
git branch -M main
git push -u origin main

echo "✅ Repository setup complete!"
echo "🌐 Repository: https://github.com/engagegpt-dev/quote-bot"
echo ""
echo "📋 Next steps:"
echo "1. Go to your GitHub repository"
echo "2. Click 'Code' → 'Codespaces' → 'Create codespace'"
echo "3. Wait for setup (2-3 minutes)"
echo "4. Run: python api_server.py"
echo "5. Manage from this chat using the API!"