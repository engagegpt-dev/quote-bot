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
    # Check for duplicates by username/email/auth token
    dup_user = next((acc for acc in accounts if acc.get('username', '').lower() == username.lower()), None)
    dup_email = next((acc for acc in accounts if acc.get('email', '').lower() == email.lower()), None)
    dup_token = next((acc for acc in accounts if acc.get('auth_token', '') == auth_token), None)
    if dup_user or dup_email or dup_token:
        log_message(f"Duplicate account skipped: {username}")
        return RedirectResponse(url='/accounts', status_code=303)
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


def parse_accounts_from_text(text: str) -> List[dict]:
    """Parse pasted account blocks into a list of account dicts.

    Supported formats: blocks separated by lines of dashes or blank lines.
    Each block contains lines like `Username: foo` or `Auth Token: abc`.
    Returns a list of parsed accounts (may exclude malformed entries).
    """
    import re

    if not text:
        return []

    # Split on lines of 3+ dashes or blank lines followed by 'Account' headers
    blocks = re.split(r"\n-{3,}\n|\n\s*Account\s*\d+\s*:\s*\n", text, flags=re.IGNORECASE)
    parsed = []
    for block in blocks:
        if not block or not block.strip():
            continue
        data = {}
        for line in block.splitlines():
            if ':' not in line:
                continue
            key, val = line.split(':', 1)
            key_n = key.strip().lower()
            val = val.strip()
            if key_n.startswith('username'):
                data['username'] = val.lstrip('@')
            elif key_n.startswith('password'):
                data['password'] = val
            elif key_n.startswith('email'):
                data['email'] = val
            elif key_n.startswith('auth') and 'token' in key_n:
                data['auth_token'] = val
            elif key_n.startswith('totp') or key_n.startswith('topt') or 'totp' in key_n:
                data['totp_secret'] = val
            elif key_n.startswith('registration') or key_n.startswith('reg') or 'year' in key_n:
                try:
                    data['registration_year'] = int(val)
                except:
                    data['registration_year'] = None
        # Minimal sanity check: must have username and either password or auth_token
        if 'username' in data and (('password' in data and data['password']) or ('auth_token' in data and data['auth_token'])):
            # Initialize optional keys
            data.setdefault('password', '')
            data.setdefault('email', '')
            data.setdefault('auth_token', '')
            data.setdefault('totp_secret', '')
            if 'registration_year' not in data or not data['registration_year']:
                data['registration_year'] = datetime.now().year
            parsed.append(data)
    return parsed


@app.post('/accounts/import')
async def import_accounts_form(request: Request, accounts_text: str = Form(...), user: str = Depends(authenticate)):
    accounts = load_accounts()
    existing_usernames = set([acc.get('username').lower() for acc in accounts if acc.get('username')])
    existing_emails = set([acc.get('email').lower() for acc in accounts if acc.get('email')])
    existing_tokens = set([acc.get('auth_token') for acc in accounts if acc.get('auth_token')])

    parsed = parse_accounts_from_text(accounts_text)
    added = 0
    skipped = 0
    skipped_reasons = []
    max_id = max([acc.get('id', 0) for acc in accounts], default=0)
    for p in parsed:
        username_l = p.get('username', '').lower()
        email_l = p.get('email', '').lower()
        token = p.get('auth_token', '')
        if username_l in existing_usernames or (email_l and email_l in existing_emails) or (token and token in existing_tokens):
            skipped += 1
            skipped_reasons.append((p.get('username'), 'duplicate'))
            continue
        max_id += 1
        new_acc = {
            'id': max_id,
            'username': p.get('username'),
            'password': p.get('password', ''),
            'email': p.get('email', ''),
            'auth_token': p.get('auth_token', ''),
            'totp_secret': p.get('totp_secret', ''),
            'registration_year': p.get('registration_year', datetime.now().year),
            'active': True
        }
        accounts.append(new_acc)
        existing_usernames.add(username_l)
        if new_acc['email']:
            existing_emails.add(new_acc['email'].lower())
        if new_acc['auth_token']:
            existing_tokens.add(new_acc['auth_token'])
        added += 1
        log_message(f"Batch added account {new_acc['username']}")
    if added > 0:
        save_accounts(accounts)
    log_message(f"Import completed: {added} added, {skipped} skipped")
    return RedirectResponse(url='/accounts', status_code=303)

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
        # Add cookies for both x.com and twitter.com domains to increase compatibility
        cookies = [
            {
                "name": "auth_token",
                "value": auth_token,
                "domain": ".x.com",
                "path": "/",
                "httpOnly": True,
                "secure": True,
                "sameSite": "Lax",
            },
            {
                "name": "auth_token",
                "value": auth_token,
                "domain": ".twitter.com",
                "path": "/",
                "httpOnly": True,
                "secure": True,
                "sameSite": "Lax",
            }
        ]
        await context.add_cookies(cookies)
        # Log cookies present in context for debugging
        try:
            current_cookies = await context.cookies()
            log_message(f"Auth cookies set: {len(current_cookies)} cookies")
        except Exception as e:
            log_message(f"Could not read context cookies after set: {e}")
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

async def save_debug_info(page, label: str):
    try:
        import os
        from datetime import datetime
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        debug_dir = os.path.join('debug', ts)
        os.makedirs(debug_dir, exist_ok=True)
        screenshot_path = os.path.join(debug_dir, f"{label}.png")
        html_path = os.path.join(debug_dir, f"{label}.html")
        # Try to capture screenshot
        try:
            await page.screenshot(path=screenshot_path, full_page=True)
        except Exception as e:
            log_message(f"save_debug_info screenshot failed: {e}")
        try:
            content = await page.content()
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(content)
        except Exception as e:
            log_message(f"save_debug_info HTML failed: {e}")
        log_message(f"Saved debug info: {screenshot_path}, {html_path}")
    except Exception as e:
        log_message(f"save_debug_info error: {e}")


async def quote_retweet(page, tweet_url: str, users_to_tag: List[str], message: str = ""):
    try:
        log_message(f"Processing tweet: {tweet_url}")
        # Navigate and capture response status and final URL
        try:
            response = await page.goto(tweet_url, wait_until='networkidle', timeout=60000)
            if response:
                status = response.status
                log_message(f"Navigation response status: {status}")
            else:
                log_message("Navigation response: None")
        except Exception as e:
            log_message(f"Navigation error: {e}")
            # Prova senza wait_until
            try:
                await page.goto(tweet_url, timeout=30000)
                log_message("Navigation successful on retry")
            except Exception as e2:
                log_message(f"Navigation retry failed: {e2}")
                await save_debug_info(page, 'navigation_error')
                return False
        await page.wait_for_timeout(3000)

        # Check if we're on the correct tweet page
        try:
            current_url = page.url
            log_message(f"Current page URL after goto: {current_url}")
            # More flexible URL check - just check if we have a status ID
            if not current_url or "/status/" not in current_url:
                log_message(f"Unexpected URL after navigation: {current_url}")
                try:
                    await save_debug_info(page, 'unexpected_url_after_goto')
                except:
                    pass
                return False
        except Exception as e:
            log_message(f"Error reading page.url: {e}")

        # Try multiple selectors for the retweet/repost button to be robust against UI changes
        retweet_selectors = [
            '[data-testid="retweet"]',
            '[aria-label="Repost"]',
            'div[data-testid="retweet"]',
            'button[data-testid="retweet"]'
        ]
        retweet_btn = None
        for selector in retweet_selectors:
            try:
                retweet_btn = await page.wait_for_selector(selector, timeout=4000)
                if retweet_btn:
                    break
            except:
                continue

        if not retweet_btn:
            log_message("Repost/retweet button not found")
            await save_debug_info(page, 'retweet_button_not_found')
            return False

        # Movimento mouse più umano prima del click
        await page.hover('[data-testid="retweet"]')
        await page.wait_for_timeout(500)
        await retweet_btn.click()
        await page.wait_for_timeout(3000)
        
        # Controlla se siamo ancora sul tweet
        current_url = page.url
        if "status" not in current_url:
            log_message(f"Redirected after retweet click to: {current_url}")
            await page.goto(tweet_url)
            await page.wait_for_timeout(2000)

        # Try multiple ways to find the Quote/Retweet with comment menu item (diff languages/markup)
        quote_selectors = [
            'a[href="/compose/post"][role="menuitem"]',
            'a[role="menuitem"]:has-text("Quote")',
            '[role="menuitem"]:has-text("Quote")',
            '[role="menuitem"]:nth-child(2)'
        ]
        quote_btn = None
        for selector in quote_selectors:
            try:
                quote_btn = await page.wait_for_selector(selector, timeout=2500)
                if quote_btn:
                    break
            except:
                continue

        if not quote_btn:
            log_message("Quote menu item not found")
            await save_debug_info(page, 'quote_menuitem_not_found')
            return False

        # Prova a cliccare direttamente usando JavaScript
        log_message("Attempting to click Quote button with JavaScript")
        try:
            await page.evaluate('document.querySelector("a[href=\"/compose/post\"][role=\"menuitem\"]").click()')
        except:
            await quote_btn.click()
        await page.wait_for_timeout(4000)
        
        # Screenshot dopo aver cliccato quote
        await save_debug_info(page, 'after_quote_click')
        
        # Aspetta che il modal si carichi
        await page.wait_for_timeout(2000)
        
        # Selettori multilingue per "Add a comment" / "Ajouter un commentaire"
        textarea_selectors = [
            '[data-testid="tweetTextarea_0"][role="textbox"]',
            '.public-DraftEditor-content[data-testid="tweetTextarea_0"]',
            '[aria-describedby*="placeholder"][contenteditable="true"]',
            'div[aria-label="Post text"][contenteditable="true"]',
            'div[aria-label="Texte du post"][contenteditable="true"]',  # French
            '[placeholder*="Ajouter un commentaire"][contenteditable="true"]',  # French placeholder
            '[aria-placeholder*="Ajouter un commentaire"][contenteditable="true"]',
            'div[contenteditable="true"][data-testid="tweetTextarea_0"]',
            '.notranslate[contenteditable="true"]',
            '[role="textbox"][contenteditable="true"]'
        ]
        
        textarea = None
        found_selector = None
        for sel in textarea_selectors:
            try:
                textarea = await page.wait_for_selector(sel, timeout=2000)
                if textarea:
                    found_selector = sel
                    log_message(f"Found textarea with selector: {sel}")
                    break
            except Exception as e:
                log_message(f"Selector {sel} failed: {e}")
                continue

        if not textarea:
            log_message("Add a comment textarea not found with any selector")
            await save_debug_info(page, 'textarea_not_found')
            return False
            
        # Multiple click attempts
        await textarea.click()
        await page.wait_for_timeout(500)
        
        # Build final text with tags in message template (RESTORED WORKING LOGIC)
        if "{TAGS}" in message:
            # Replace {TAGS} placeholder with actual tags
            tags_text = " ".join([f"@{user}" if not user.startswith('@') else user for user in users_to_tag])
            quote_text = message.replace("{TAGS}", tags_text)
        else:
            # Fallback to old method if no {TAGS} placeholder
            quote_text = ""
            for user in users_to_tag:
                if not user.startswith('@'):
                    user = f"@{user}"
                quote_text += f"{user} "
            if message:
                quote_text += message

        log_message(f"Typing text: {quote_text}")
        
        # Multiple text input methods
        try:
            # Method 1: Clear and type
            await page.keyboard.press('Control+a')
            await page.keyboard.type(quote_text)
        except:
            try:
                # Method 2: Focus and type
                await textarea.focus()
                await page.keyboard.type(quote_text)
            except:
                # Method 3: JavaScript injection
                await page.evaluate(f'document.querySelector("{found_selector}").innerText = "{quote_text}"')
        
        await page.wait_for_timeout(1000)
        
        # Verify text was inserted
        try:
            text_content = await page.evaluate(f'document.querySelector("{found_selector}").innerText')
            log_message(f"Text in textarea after typing: {text_content}")
        except:
            log_message("Could not verify text content")
        
        # Screenshot dopo aver inserito il testo
        await save_debug_info(page, 'after_text_input')
        
        # Clicca sul bottone Post
        post_btn = await page.wait_for_selector('button[data-testid="tweetButton"]', timeout=3000)
        if post_btn:
            await post_btn.click()
            await page.wait_for_timeout(2000)
            log_message("Post button clicked successfully")
        else:
            log_message("Post button not found")
            await save_debug_info(page, 'post_button_not_found')
            return False
        
        # Screenshot finale
        await save_debug_info(page, 'final_result')
        
        return True

    except Exception as e:
        log_message(f"Quote retweet failed: {e}")
        try:
            await save_debug_info(page, 'quote_retweet_exception')
        except:
            pass
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
                
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        '--no-first-run',
                        '--disable-blink-features=AutomationControlled',
                        '--disable-web-security'
                    ]
                )
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    viewport={'width': 1920, 'height': 1080}
                )
                page = await context.new_page()
                
                # Rimuovi tracce di automazione
                await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

                login_success = await login_with_auth_token(context, account["auth_token"])
                
                if login_success:
                    await page.goto("https://x.com/home")
                    await page.wait_for_timeout(3000)
                    
                    try:
                        await page.wait_for_selector('[data-testid="SideNav_NewTweet_Button"]', timeout=5000)
                        log_message(f"Auth token login successful for {account['username']}")
                    except:
                        login_success = False
                        try:
                            await save_debug_info(page, f'login_verification_failed_{account["username"]}')
                        except:
                            pass

                if not login_success:
                    login_success = await login_with_credentials(
                        page, 
                        account["username"], 
                        account["password"], 
                        account["totp_secret"]
                    )

                if not login_success:
                    log_message(f"Login failed for {account['username']}")
                    try:
                        await save_debug_info(page, f'login_failed_{account["username"]}')
                    except:
                        pass
                    await browser.close()
                    continue

                # Usa twitter.com e naviga prima alla home
                tweet_url_fixed = tweet_url.replace("x.com", "twitter.com")
                await page.goto("https://twitter.com/home")
                await page.wait_for_timeout(2000)
                
                success = await quote_retweet(page, tweet_url_fixed, users_to_tag, message)
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