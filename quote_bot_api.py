from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
import asyncio
import json
import os
from typing import List, Optional
import uvicorn
from datetime import datetime
from playwright.async_api import async_playwright
import pyotp

app = FastAPI(title="Quote Retweet Bot API", version="1.0.0")

class Account(BaseModel):
    username: str
    password: str
    email: str
    auth_token: str
    totp_secret: str
    registration_year: int

class QuoteRequest(BaseModel):
    tweet_url: str
    users_to_tag: List[str]
    message: Optional[str] = ""
    account_ids: Optional[List[int]] = None

class AccountAdd(BaseModel):
    username: str
    password: str
    email: str
    auth_token: str
    totp_secret: str
    registration_year: int

class BotStatus(BaseModel):
    is_running: bool
    total_accounts: int
    active_accounts: int
    last_campaign: Optional[str]

# Global state
bot_state = {
    "is_running": False,
    "last_campaign": None,
    "logs": []
}

def load_accounts():
    """Load accounts from JSON file"""
    if os.path.exists("accounts.json"):
        with open("accounts.json", "r") as f:
            return json.load(f)
    return []

def save_accounts(accounts):
    """Save accounts to JSON file"""
    with open("accounts.json", "w") as f:
        json.dump(accounts, f, indent=2)

def log_message(message: str):
    """Add log message"""
    timestamp = datetime.now().isoformat()
    log_entry = f"[{timestamp}] {message}"
    bot_state["logs"].append(log_entry)
    print(log_entry)
    
    # Keep only last 100 logs
    if len(bot_state["logs"]) > 100:
        bot_state["logs"] = bot_state["logs"][-100:]

async def login_with_auth_token(context, auth_token: str):
    """Login using auth token"""
    try:
        cookies = [
            {
                "name": "auth_token",
                "value": auth_token,
                "domain": ".x.com",
                "path": "/",
                "httpOnly": True,
                "secure": True,
                "sameSite": "Lax",
            }
        ]
        await context.add_cookies(cookies)
        return True
    except Exception as e:
        log_message(f"Auth token login failed: {e}")
        return False

async def login_with_credentials(page, username: str, password: str, totp_secret: str):
    """Login using username/password with 2FA"""
    try:
        await page.goto("https://x.com/login")
        await page.wait_for_timeout(3000)
        
        # Username
        await page.fill('input[name="text"]', username)
        await page.click('div[role="button"]:has-text("Next")')
        await page.wait_for_timeout(2000)
        
        # Password
        await page.fill('input[name="password"]', password)
        await page.click('div[role="button"]:has-text("Log in")')
        await page.wait_for_timeout(3000)
        
        # 2FA if required
        if totp_secret and await page.query_selector('input[name="text"]'):
            totp = pyotp.TOTP(totp_secret)
            code = totp.now()
            await page.fill('input[name="text"]', code)
            await page.click('div[role="button"]:has-text("Next")')
            await page.wait_for_timeout(3000)
        
        # Verify login
        await page.wait_for_selector('[data-testid="SideNav_NewTweet_Button"]', timeout=10000)
        return True
        
    except Exception as e:
        log_message(f"Credential login failed: {e}")
        return False

async def quote_retweet(page, tweet_url: str, users_to_tag: List[str], message: str = ""):
    """Perform quote retweet with user tags"""
    try:
        log_message(f"Processing tweet: {tweet_url}")
        await page.goto(tweet_url)
        await page.wait_for_timeout(3000)

        # Click retweet button
        retweet_btn = await page.wait_for_selector('[data-testid="retweet"]', timeout=5000)
        await retweet_btn.click()
        await page.wait_for_timeout(2000)

        # Click quote option
        quote_btn = await page.wait_for_selector('[data-testid="Dropdown"] [role="menuitem"]:nth-child(2)', timeout=3000)
        await quote_btn.click()
        await page.wait_for_timeout(2000)

        # Find text area
        textarea = await page.wait_for_selector('div[role="textbox"][data-testid^="tweetTextarea"]', timeout=3000)
        await textarea.click()
        
        # Build quote text
        quote_text = ""
        for user in users_to_tag:
            if not user.startswith('@'):
                user = f"@{user}"
            quote_text += f"{user} "
        
        if message:
            quote_text += message

        # Type text with mention handling
        await page.keyboard.press('Control+A')
        await page.keyboard.press('Backspace')
        
        words = quote_text.split(' ')
        for idx, word in enumerate(words):
            if word.startswith('@'):
                # Type mention slowly
                for char in word:
                    await page.keyboard.type(char, delay=100)
                await page.wait_for_timeout(700)
                
                # Select first suggestion
                try:
                    suggestion = await page.wait_for_selector('[role="option"]', timeout=2000)
                    if suggestion:
                        await suggestion.click()
                        await page.wait_for_timeout(300)
                except:
                    pass
            else:
                await page.keyboard.type(word, delay=50)
            
            if idx < len(words) - 1:
                await page.keyboard.type(' ', delay=20)

        await page.wait_for_timeout(1000)

        # Click post button
        post_btn = await page.wait_for_selector('button[data-testid="tweetButtonInline"]', timeout=3000)
        if await post_btn.get_attribute('aria-disabled') != 'true':
            await post_btn.click()
            await page.wait_for_timeout(2000)
            return True
        
        return False

    except Exception as e:
        log_message(f"Quote retweet failed: {e}")
        return False

async def run_quote_campaign(tweet_url: str, users_to_tag: List[str], message: str, account_ids: List[int] = None):
    """Run quote campaign with specified accounts"""
    bot_state["is_running"] = True
    bot_state["last_campaign"] = datetime.now().isoformat()
    
    accounts = load_accounts()
    if account_ids:
        accounts = [acc for acc in accounts if acc.get("id") in account_ids]
    
    active_accounts = [acc for acc in accounts if acc.get("active", True)]
    
    log_message(f"Starting campaign with {len(active_accounts)} accounts")
    log_message(f"Tweet: {tweet_url}")
    log_message(f"Tags: {', '.join(users_to_tag)}")

    success_count = 0
    
    async with async_playwright() as p:
        for account in active_accounts:
            if not bot_state["is_running"]:
                break
                
            try:
                log_message(f"Processing account: {account['username']}")
                
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context()
                page = await context.new_page()

                # Try auth token first
                login_success = await login_with_auth_token(context, account["auth_token"])
                
                if login_success:
                    await page.goto("https://x.com/home")
                    await page.wait_for_timeout(3000)
                    
                    try:
                        await page.wait_for_selector('[data-testid="SideNav_NewTweet_Button"]', timeout=5000)
                        log_message(f"Auth token login successful for {account['username']}")
                    except:
                        login_success = False

                # Fallback to credentials
                if not login_success:
                    login_success = await login_with_credentials(
                        page, 
                        account["username"], 
                        account["password"], 
                        account["totp_secret"]
                    )

                if not login_success:
                    log_message(f"Login failed for {account['username']}")
                    await browser.close()
                    continue

                # Perform quote retweet
                success = await quote_retweet(page, tweet_url, users_to_tag, message)
                if success:
                    success_count += 1
                    log_message(f"Quote posted successfully by {account['username']}")
                else:
                    log_message(f"Quote failed for {account['username']}")

                await browser.close()
                await asyncio.sleep(5)  # Delay between accounts

            except Exception as e:
                log_message(f"Error with account {account['username']}: {e}")

    bot_state["is_running"] = False
    log_message(f"Campaign completed. Success: {success_count}/{len(active_accounts)}")

@app.get("/")
async def root():
    return {"message": "Quote Retweet Bot API", "status": "online"}

@app.post("/quote/start")
async def start_quote_campaign(request: QuoteRequest, background_tasks: BackgroundTasks):
    """Start quote retweet campaign"""
    if bot_state["is_running"]:
        raise HTTPException(status_code=400, detail="Campaign already running")
    
    background_tasks.add_task(
        run_quote_campaign,
        request.tweet_url,
        request.users_to_tag,
        request.message or "",
        request.account_ids
    )
    
    return {"message": "Campaign started", "status": "success"}

@app.post("/quote/stop")
async def stop_campaign():
    """Stop current campaign"""
    if not bot_state["is_running"]:
        raise HTTPException(status_code=400, detail="No campaign running")
    
    bot_state["is_running"] = False
    return {"message": "Campaign stopped", "status": "success"}

@app.get("/status")
async def get_status() -> BotStatus:
    """Get bot status"""
    accounts = load_accounts()
    active_accounts = len([acc for acc in accounts if acc.get("active", True)])
    
    return BotStatus(
        is_running=bot_state["is_running"],
        total_accounts=len(accounts),
        active_accounts=active_accounts,
        last_campaign=bot_state["last_campaign"]
    )

@app.get("/accounts")
async def list_accounts():
    """List all accounts (without sensitive data)"""
    accounts = load_accounts()
    safe_accounts = []
    for acc in accounts:
        safe_accounts.append({
            "id": acc.get("id"),
            "username": acc["username"],
            "email": acc["email"],
            "registration_year": acc["registration_year"],
            "active": acc.get("active", True)
        })
    return {"accounts": safe_accounts}

@app.post("/accounts/add")
async def add_account(account: AccountAdd):
    """Add new account"""
    accounts = load_accounts()
    
    # Generate new ID
    max_id = max([acc.get("id", 0) for acc in accounts], default=0)
    new_account = account.dict()
    new_account["id"] = max_id + 1
    new_account["active"] = True
    
    accounts.append(new_account)
    save_accounts(accounts)
    
    return {"message": "Account added", "id": new_account["id"]}

@app.delete("/accounts/{account_id}")
async def delete_account(account_id: int):
    """Delete account"""
    accounts = load_accounts()
    accounts = [acc for acc in accounts if acc.get("id") != account_id]
    save_accounts(accounts)
    
    return {"message": "Account deleted"}

@app.put("/accounts/{account_id}/toggle")
async def toggle_account(account_id: int):
    """Toggle account active status"""
    accounts = load_accounts()
    for acc in accounts:
        if acc.get("id") == account_id:
            acc["active"] = not acc.get("active", True)
            break
    
    save_accounts(accounts)
    return {"message": "Account status updated"}

@app.get("/logs")
async def get_logs():
    """Get recent logs"""
    return {"logs": bot_state["logs"][-50:]}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)