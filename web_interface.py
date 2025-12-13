from fastapi import FastAPI, HTTPException, BackgroundTasks, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import secrets
from pydantic import BaseModel
import asyncio
import json
import os
from typing import List, Optional
import uvicorn
from datetime import datetime
from playwright.async_api import async_playwright
import pyotp

app = FastAPI(title="Quote Retweet Bot", version="1.0.0")

# Security
security = HTTPBasic()
USERNAME = "admin"
PASSWORD = "quote2024"  # Change this!

def authenticate(credentials: HTTPBasicCredentials = Depends(security)):
    is_correct_username = secrets.compare_digest(credentials.username, USERNAME)
    is_correct_password = secrets.compare_digest(credentials.password, PASSWORD)
    if not (is_correct_username and is_correct_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return credentials.username

# Templates
templates = Jinja2Templates(directory="templates")

# Models
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

# Global state
bot_state = {
    "is_running": False,
    "last_campaign": None,
    "logs": []
}

def load_accounts():
    if os.path.exists("accounts.json"):
        with open("accounts.json", "r") as f:
            return json.load(f)
    return []

def save_accounts(accounts):
    with open("accounts.json", "w") as f:
        json.dump(accounts, f, indent=2)

def log_message(message: str):
    timestamp = datetime.now().isoformat()
    log_entry = f"[{timestamp}] {message}"
    bot_state["logs"].append(log_entry)
    print(log_entry)
    if len(bot_state["logs"]) > 100:
        bot_state["logs"] = bot_state["logs"][-100:]

# Web Interface Routes
@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, user: str = Depends(authenticate)):
    accounts = load_accounts()
    active_accounts = [acc for acc in accounts if acc.get("active", True)]
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "accounts": accounts,
        "active_accounts": len(active_accounts),
        "total_accounts": len(accounts),
        "is_running": bot_state["is_running"],
        "last_campaign": bot_state["last_campaign"],
        "logs": bot_state["logs"][-10:]
    })

@app.get("/accounts", response_class=HTMLResponse)
async def accounts_page(request: Request, user: str = Depends(authenticate)):
    accounts = load_accounts()
    return templates.TemplateResponse("accounts.html", {
        "request": request,
        "accounts": accounts
    })

@app.post("/accounts/add")
async def add_account_form(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    email: str = Form(...),
    auth_token: str = Form(...),
    totp_secret: str = Form(...),
    registration_year: int = Form(...),
    user: str = Depends(authenticate)
):
    accounts = load_accounts()
    max_id = max([acc.get("id", 0) for acc in accounts], default=0)
    
    new_account = {
        "id": max_id + 1,
        "username": username,
        "password": password,
        "email": email,
        "auth_token": auth_token,
        "totp_secret": totp_secret,
        "registration_year": registration_year,
        "active": True
    }
    
    accounts.append(new_account)
    save_accounts(accounts)
    log_message(f"Account {username} added")
    
    return RedirectResponse(url="/accounts", status_code=303)

@app.post("/accounts/{account_id}/delete")
async def delete_account_form(account_id: int, user: str = Depends(authenticate)):
    accounts = load_accounts()
    account = next((acc for acc in accounts if acc.get("id") == account_id), None)
    if account:
        accounts = [acc for acc in accounts if acc.get("id") != account_id]
        save_accounts(accounts)
        log_message(f"Account {account['username']} deleted")
    
    return RedirectResponse(url="/accounts", status_code=303)

@app.post("/accounts/{account_id}/toggle")
async def toggle_account_form(account_id: int, user: str = Depends(authenticate)):
    accounts = load_accounts()
    for acc in accounts:
        if acc.get("id") == account_id:
            acc["active"] = not acc.get("active", True)
            status = "activated" if acc["active"] else "deactivated"
            log_message(f"Account {acc['username']} {status}")
            break
    
    save_accounts(accounts)
    return RedirectResponse(url="/accounts", status_code=303)

@app.get("/campaign", response_class=HTMLResponse)
async def campaign_page(request: Request, user: str = Depends(authenticate)):
    accounts = load_accounts()
    active_accounts = [acc for acc in accounts if acc.get("active", True)]
    
    return templates.TemplateResponse("campaign.html", {
        "request": request,
        "accounts": active_accounts,
        "is_running": bot_state["is_running"]
    })

@app.post("/campaign/start")
async def start_campaign_form(
    request: Request,
    background_tasks: BackgroundTasks,
    tweet_url: str = Form(...),
    users_to_tag: str = Form(...),
    message: str = Form(""),
    account_ids: List[int] = Form([]),
    user: str = Depends(authenticate)
):
    if bot_state["is_running"]:
        return templates.TemplateResponse("campaign.html", {
            "request": request,
            "error": "Campaign already running",
            "accounts": load_accounts()
        })
    
    # Parse users to tag
    users_list = [user.strip() for user in users_to_tag.split(",") if user.strip()]
    
    background_tasks.add_task(
        run_quote_campaign,
        tweet_url,
        users_list,
        message,
        account_ids if account_ids else None
    )
    
    return RedirectResponse(url="/", status_code=303)

@app.post("/campaign/stop")
async def stop_campaign_form(user: str = Depends(authenticate)):
    bot_state["is_running"] = False
    log_message("Campaign stopped by user")
    return RedirectResponse(url="/", status_code=303)

# Bot Logic (same as before)
async def login_with_auth_token(context, auth_token: str):
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
    try:
        await page.goto("https://x.com/login")
        await page.wait_for_timeout(3000)
        
        await page.fill('input[name="text"]', username)
        await page.click('div[role="button"]:has-text("Next")')
        await page.wait_for_timeout(2000)
        
        await page.fill('input[name="password"]', password)
        await page.click('div[role="button"]:has-text("Log in")')
        await page.wait_for_timeout(3000)
        
        if totp_secret and await page.query_selector('input[name="text"]'):
            totp = pyotp.TOTP(totp_secret)
            code = totp.now()
            await page.fill('input[name="text"]', code)
            await page.click('div[role="button"]:has-text("Next")')
            await page.wait_for_timeout(3000)
        
        await page.wait_for_selector('[data-testid="SideNav_NewTweet_Button"]', timeout=10000)
        return True
        
    except Exception as e:
        log_message(f"Credential login failed: {e}")
        return False

async def quote_retweet(page, tweet_url: str, users_to_tag: List[str], message: str = ""):
    try:
        log_message(f"Processing tweet: {tweet_url}")
        await page.goto(tweet_url)
        await page.wait_for_timeout(3000)

        retweet_btn = await page.wait_for_selector('[data-testid="retweet"]', timeout=5000)
        await retweet_btn.click()
        await page.wait_for_timeout(2000)

        quote_btn = await page.wait_for_selector('[data-testid="Dropdown"] [role="menuitem"]:nth-child(2)', timeout=3000)
        await quote_btn.click()
        await page.wait_for_timeout(2000)

        textarea = await page.wait_for_selector('div[role="textbox"][data-testid^="tweetTextarea"]', timeout=3000)
        await textarea.click()
        
        quote_text = ""
        for user in users_to_tag:
            if not user.startswith('@'):
                user = f"@{user}"
            quote_text += f"{user} "
        
        if message:
            quote_text += message

        await page.keyboard.press('Control+A')
        await page.keyboard.press('Backspace')
        
        words = quote_text.split(' ')
        for idx, word in enumerate(words):
            if word.startswith('@'):
                for char in word:
                    await page.keyboard.type(char, delay=100)
                await page.wait_for_timeout(700)
                
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

                login_success = await login_with_auth_token(context, account["auth_token"])
                
                if login_success:
                    await page.goto("https://x.com/home")
                    await page.wait_for_timeout(3000)
                    
                    try:
                        await page.wait_for_selector('[data-testid="SideNav_NewTweet_Button"]', timeout=5000)
                        log_message(f"Auth token login successful for {account['username']}")
                    except:
                        login_success = False

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

                success = await quote_retweet(page, tweet_url, users_to_tag, message)
                if success:
                    success_count += 1
                    log_message(f"Quote posted successfully by {account['username']}")
                else:
                    log_message(f"Quote failed for {account['username']}")

                await browser.close()
                await asyncio.sleep(5)

            except Exception as e:
                log_message(f"Error with account {account['username']}: {e}")

    bot_state["is_running"] = False
    log_message(f"Campaign completed. Success: {success_count}/{len(active_accounts)}")

# API Routes (for external access)
@app.post("/api/quote/start")
async def start_quote_campaign_api(request: QuoteRequest, background_tasks: BackgroundTasks, user: str = Depends(authenticate)):
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

@app.get("/api/status")
async def get_status_api(user: str = Depends(authenticate)):
    accounts = load_accounts()
    active_accounts = len([acc for acc in accounts if acc.get("active", True)])
    
    return {
        "is_running": bot_state["is_running"],
        "total_accounts": len(accounts),
        "active_accounts": active_accounts,
        "last_campaign": bot_state["last_campaign"]
    }

@app.get("/api/logs")
async def get_logs_api(user: str = Depends(authenticate)):
    return {"logs": bot_state["logs"][-50:]}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)