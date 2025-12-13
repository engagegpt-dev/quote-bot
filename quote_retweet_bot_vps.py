import asyncio
import json
import os
import time
from datetime import datetime
from typing import List, Optional
from playwright.async_api import async_playwright
import httpx
import logging

class QuoteRetweetBot:
    def __init__(self):
        self.is_running = False
        self.tweets_sent = 0
        self.errors = 0
        self.last_activity = None
        self.logs = []
        self.config = {
            "twiboost_api_key": "RSPR0pU6f3G6lF8oKDncvsUdrfpStdgcoUQHN7RIF0QBLtpTUhvauCANq75t",
            "twiboost_api_url": "https://twiboost.com/api/v2",
            "post_interval": 3600,
            "batch_size": 3
        }
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def log(self, message: str):
        timestamp = datetime.now().isoformat()
        log_entry = f"[{timestamp}] {message}"
        self.logs.append(log_entry)
        self.logger.info(message)
        
        # Keep only last 100 logs
        if len(self.logs) > 100:
            self.logs = self.logs[-100:]

    async def _save_debug_info(self, page, label: str):
        try:
            ts = datetime.now().strftime('%Y%m%d_%H%M%S')
            debug_dir = os.path.join('debug', ts)
            os.makedirs(debug_dir, exist_ok=True)
            screenshot_path = os.path.join(debug_dir, f"{label}.png")
            html_path = os.path.join(debug_dir, f"{label}.html")
            try:
                await page.screenshot(path=screenshot_path, full_page=True)
            except Exception as e:
                self.log(f"_save_debug_info screenshot failed: {e}")
            try:
                content = await page.content()
                with open(html_path, 'w', encoding='utf-8') as f:
                    f.write(content)
            except Exception as e:
                self.log(f"_save_debug_info HTML failed: {e}")
            self.log(f"Saved debug info: {screenshot_path}, {html_path}")
        except Exception as e:
            self.log(f"_save_debug_info error: {e}")

    async def set_auth_token_cookie(self, context, auth_token: str) -> bool:
        try:
            cookies = [
                {
                    "name": "auth_token",
                    "value": auth_token,
                    "domain": ".twitter.com",
                    "path": "/",
                    "httpOnly": True,
                    "secure": True,
                    "sameSite": "Lax",
                },
                {
                    "name": "auth_token",
                    "value": auth_token,
                    "domain": ".x.com",
                    "path": "/",
                    "httpOnly": True,
                    "secure": True,
                    "sameSite": "Lax",
                },
            ]
            await context.add_cookies(cookies)
            return True
        except Exception as e:
            self.log(f"Error setting auth_token: {e}")
            return False

    async def quote_retweet(self, page, post_url: str, quote_text: str) -> bool:
        try:
            self.log(f"Processing post: {post_url}")
            await page.goto(post_url)
            await page.wait_for_timeout(3000)

            # Find retweet button
            retweet_selectors = [
                '[data-testid="retweet"]',
                '[aria-label="Repost"]',
                'div[data-testid="retweet"]'
            ]

            retweet_button = None
            for selector in retweet_selectors:
                try:
                    retweet_button = await page.wait_for_selector(selector, timeout=4000)
                    if retweet_button:
                        break
                except:
                    continue

            if not retweet_button:
                self.log("Repost button not found")
                await self._save_debug_info(page, 'retweet_button_not_found')
                return False

            await retweet_button.click()
            await page.wait_for_timeout(2000)

            # Find quote button
            quote_selectors = [
                '[data-testid="Dropdown"] [role="menuitem"]:has-text("Quote")',
                '[data-testid="Dropdown"] [role="menuitem"]:nth-child(2)'
            ]

            quote_button = None
            for selector in quote_selectors:
                try:
                    quote_button = await page.wait_for_selector(selector, timeout=2000)
                    if quote_button:
                        break
                except:
                    continue

            if not quote_button:
                self.log("Quote button not found")
                await self._save_debug_info(page, 'quote_button_not_found')
                return False

            await quote_button.click()
            await page.wait_for_timeout(2000)

            # Find text area
            textarea_selector = 'div[role="textbox"][data-testid^="tweetTextarea"]'
            try:
                await page.wait_for_selector(textarea_selector, timeout=3000)
            except:
                self.log("Text area not found")
                await self._save_debug_info(page, 'textarea_not_found')
                return False

            # Clear and type text
            await page.click(textarea_selector)
            await page.keyboard.press('Control+A')
            await page.keyboard.press('Backspace')
            await page.wait_for_timeout(500)

            # Type quote text with mention handling
            words = quote_text.split(' ')
            for idx, word in enumerate(words):
                if word.startswith('@'):
                    # Type mention slowly
                    for ch in word:
                        await page.keyboard.type(ch, delay=100)
                    await page.wait_for_timeout(700)
                    
                    # Try to select first suggestion
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

            # Find and click post button
            post_button_selectors = [
                'button[data-testid="tweetButtonInline"]',
                'button[data-testid="tweetButton"]'
            ]

            post_clicked = False
            for selector in post_button_selectors:
                try:
                    buttons = await page.query_selector_all(selector)
                    for btn in buttons:
                        if await btn.is_visible() and await btn.get_attribute('aria-disabled') != 'true':
                            await btn.click()
                            post_clicked = True
                            break
                    if post_clicked:
                        break
                except:
                    continue

            if not post_clicked:
                self.log("Post button not found or disabled")
                await self._save_debug_info(page, 'post_button_not_found')
                return False

            self.log("Quote retweet published successfully")
            await page.wait_for_timeout(2000)
            return True

        except Exception as e:
            self.log(f"Error in quote_retweet: {e}")
            try:
                await self._save_debug_info(page, 'quote_retweet_exception')
            except:
                pass
            return False

    async def boost_post(self, post_url: str) -> bool:
        """Send boost request to TwiBoost API"""
        if not self.config.get("twiboost_api_key"):
            return False
            
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.config['twiboost_api_url']}/order",
                    headers={"Authorization": f"Bearer {self.config['twiboost_api_key']}"},
                    json={
                        "url": post_url,
                        "service": "likes",
                        "quantity": 50
                    }
                )
                if response.status_code == 200:
                    self.log("Boost order placed successfully")
                    return True
                else:
                    self.log(f"Boost failed: {response.status_code}")
                    return False
        except Exception as e:
            self.log(f"Boost error: {e}")
            return False

    async def run_campaign(self, post_url: str, quote_texts: List[str], auth_tokens: List[str], boost_enabled: bool = True):
        """Run the quote retweet campaign"""
        self.is_running = True
        self.tweets_sent = 0
        self.errors = 0
        self.last_activity = datetime.now().isoformat()
        
        self.log(f"Starting campaign with {len(auth_tokens)} accounts and {len(quote_texts)} quotes")

        async with async_playwright() as p:
            for i, (auth_token, quote_text) in enumerate(zip(auth_tokens, quote_texts)):
                if not self.is_running:
                    break
                    
                try:
                    self.log(f"Processing account {i+1}/{len(auth_tokens)}")
                    
                    browser = await p.chromium.launch(headless=True)
                    context = await browser.new_context()
                    page = await context.new_page()

                    # Login with auth token
                    login_success = await self.set_auth_token_cookie(context, auth_token)
                    if not login_success:
                        self.log(f"Login failed for account {i+1}")
                        self.errors += 1
                        await browser.close()
                        continue

                    # Navigate to Twitter
                    await page.goto("https://twitter.com/home")
                    await page.wait_for_timeout(3000)

                    # Verify login
                    try:
                        await page.wait_for_selector('[data-testid="SideNav_NewTweet_Button"]', timeout=5000)
                        self.log(f"Account {i+1} logged in successfully")
                    except:
                        self.log(f"Account {i+1} login verification failed")
                        self.errors += 1
                        await browser.close()
                        continue

                    # Perform quote retweet
                    success = await self.quote_retweet(page, post_url, quote_text)
                    if success:
                        self.tweets_sent += 1
                        self.log(f"Quote {i+1} posted successfully")
                        
                        # Boost if enabled
                        if boost_enabled:
                            await self.boost_post(post_url)
                    else:
                        self.errors += 1
                        self.log(f"Failed to post quote {i+1}")

                    await browser.close()
                    
                    # Wait between accounts
                    if i < len(auth_tokens) - 1:
                        await asyncio.sleep(self.config["post_interval"])

                except Exception as e:
                    self.log(f"Error processing account {i+1}: {e}")
                    self.errors += 1

        self.is_running = False
        self.last_activity = datetime.now().isoformat()
        self.log(f"Campaign completed. Sent: {self.tweets_sent}, Errors: {self.errors}")

    def stop_campaign(self):
        """Stop the running campaign"""
        self.is_running = False
        self.log("Campaign stopped by user")

    def update_config(self, new_config: dict):
        """Update bot configuration"""
        self.config.update(new_config)
        self.log(f"Configuration updated: {new_config}")

    def get_logs(self) -> List[str]:
        """Get recent logs"""
        return self.logs[-50:]  # Return last 50 logs