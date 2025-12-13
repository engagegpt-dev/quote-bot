@echo off
echo 🚀 Uploading Quote Bot to GitHub...

cd /d "c:\Users\Macci\Desktop\Business\Automazioni\X Mention Tool\quote mention tool"

git init
git remote add origin https://github.com/engagegpt-dev/quote-bot.git
git add .
git commit -m "Initial quote bot setup with API and accounts"
git branch -M main
git push -u origin main

echo ✅ Upload complete!
echo 🌐 Repository: https://github.com/engagegpt-dev/quote-bot
pause