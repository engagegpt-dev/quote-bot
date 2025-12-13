import asyncio
import random
import glob
import os
from playwright.async_api import async_playwright
import httpx
import json
import time
import sys
import re


NUM_ACCOUNTS = 7
QUOTE_TEXT_PATH = "tweet.txt"
POST_TO_QUOTE_PATH = "post_to_quote.txt"
IMAGES_FOLDER = "images"
POST_INTERVAL_SECONDS = 3601
BATCH_SIZE = 7

COOKIES_DIR = "cookies"
if not os.path.exists(COOKIES_DIR):
    os.makedirs(COOKIES_DIR)

AUTH_TOKENS_PATH = "auth_tokens.txt"

POSTS_NUM = 3

num_accounts = NUM_ACCOUNTS
auth_tokens = []
all_cookies_paths = []

proxy_list = [
    "127.0.0.1:40000",
    "127.0.0.1:40001",
    "127.0.0.1:40002"
]

is_paused = False
last_post_time = None
next_post_time = None

TWIBOOST_API_KEY = "RSPR0pU6f3G6lF8oKDncvsUdrfpStdgcoUQHN7RIF0QBLtpTUhvauCANq75t"
TWIBOOST_API_URL = "https://twiboost.com/api/v2"

is_boost_enabled = True

twiboost_service_ids = {
    "views": None,
    "likes": None,
    "retweets": None
}

CUSTOM_QUOTE_TEXT = None
CUSTOM_NUM_ACCOUNTS = None
CUSTOM_POST_INTERVAL = None

TWEETS_SENT = 0
POST_ERRORS = 0
BOOST_ORDERS = 0
ACCOUNT_ERRORS = {}

is_running = False
run_event = asyncio.Event()

def get_post_to_quote():
    if not os.path.exists(POST_TO_QUOTE_PATH):
        return None
    with open(POST_TO_QUOTE_PATH, "r", encoding="utf-8") as f:
        content = f.read().strip()
    return content if content else None

async def save_cookies_from_context(context, cookies_path):
    cookies = await context.cookies()
    with open(cookies_path, "w", encoding="utf-8") as f:
        json.dump(cookies, f, ensure_ascii=False, indent=2)
    print(f"Cookies saved in {cookies_path}")

async def load_cookies_to_context(context, cookies_path):
    if not os.path.exists(cookies_path):
        print(f"Cookie file not found: {cookies_path}")
        return False
    with open(cookies_path, "r", encoding="utf-8") as f:
        cookies = json.load(f)

    valid_cookies = []
    for c in cookies:
        if not c.get("name") or not c.get("value"):
            continue
        if not c.get("path"):
            continue
        if not (c.get("url") or c.get("domain")):
            continue
        valid_cookies.append(c)
    if not valid_cookies:
        print("No valid cookies for loading!")
        return False
    await context.add_cookies(valid_cookies)
    print(f"Cookies loaded from {cookies_path}")
    return True

async def set_auth_token_cookie(context, auth_token: str) -> bool:
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
        print("auth_token cookie is set")
        return True
    except Exception as e:
        print(f"Error setting auth_token cookie: {e}")
        return False


async def save_debug_info(page, label: str):
    try:
        from datetime import datetime
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        debug_dir = os.path.join('debug', ts)
        os.makedirs(debug_dir, exist_ok=True)
        screenshot_path = os.path.join(debug_dir, f"{label}.png")
        html_path = os.path.join(debug_dir, f"{label}.html")
        try:
            await page.screenshot(path=screenshot_path, full_page=True)
            print(f"Screenshot saved: {screenshot_path}")
        except Exception as e:
            print(f"save_debug_info screenshot failed: {e}")
        try:
            content = await page.content()
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"HTML saved: {html_path}")
        except Exception as e:
            print(f"save_debug_info HTML failed: {e}")
    except Exception as e:
        print(f"save_debug_info error: {e}")

def load_auth_tokens_from_file() -> list[str]:
    tokens = []
    if not os.path.exists(AUTH_TOKENS_PATH):
        return tokens
    try:
        with open(AUTH_TOKENS_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                tokens.append(line)
    except Exception as e:
        print(f"Could not read {AUTH_TOKENS_PATH}: {e}")
    return tokens

def load_tweets_from_file() -> list[str]:
    tweets = []
    try:
        with open(QUOTE_TEXT_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                tweets.append(line)
    except Exception as e:
        print(f"Could not read {QUOTE_TEXT_PATH}: {e}")

    return tweets

async def quote_retweet(page, post_url, quote_text, image_path=None):
    try:
        print(f"Let's move on to the post: {post_url}")
        await page.goto(post_url)
        await page.wait_for_timeout(3000)

        retweet_selectors = [
            '[data-testid="retweet"]',
            '[aria-label="Repost"]',
            '[aria-label="Repost this post"]',
            'div[data-testid="retweet"]',
            'button[data-testid="retweet"]'
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
            print("Repost button not found")
            await save_debug_info(page, 'retweet_button_not_found')
            return False

        await retweet_button.click()
        await page.wait_for_timeout(2500)

        quote_selectors = [
            '[data-testid="Dropdown"] [role="menuitem"]:has-text("Quote")',
            '[data-testid="Dropdown"] [role="menuitem"]:has-text("Цитировать")',
            '[data-testid="Dropdown"] [role="menuitem"]:has-text("Cita")',
            '[data-testid="Dropdown"] [role="menuitem"]:nth-child(2)',
            'div[role="menuitem"]:has-text("Quote")',
            'div[role="menuitem"]:nth-child(2)'
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
            print("Citation button not found")
            await save_debug_info(page, 'quote_button_not_found')
            return False

        await quote_button.click()
        await page.wait_for_timeout(2500)

        textarea_selectors = [
            'div[role="textbox"][data-testid^="tweetTextarea"]',
            '[data-testid="tweetTextarea_0"] div[role="textbox"]',
            '[data-testid="tweetTextarea_1"] div[role="textbox"]',
            'div[aria-label="Tweet text"] div[role="textbox"]',
            'div[role="textbox"].public-DraftStyleDefault-block'
        ]

        textbox_selector = None
        for sel in textarea_selectors:
            try:
                await page.wait_for_selector(sel, timeout=2000)
                textbox_selector = sel
                break
            except:
                continue

        if not textbox_selector:
            print("Text input field not found")
            await save_debug_info(page, 'textbox_not_found')
            return False

        await page.click(textbox_selector)
        await asyncio.sleep(0.1)
        try:
            await page.keyboard.press('Control+A')
            await page.keyboard.press('Backspace')
        except Exception:
            try:
                await page.keyboard.press('Meta+A')
                await page.keyboard.press('Backspace')
            except:
                pass
        await page.wait_for_timeout(200)

        async def choose_first_suggestion():
            suggestion_containers = [
                '[data-testid="typeaheadDropdown"]',
                'div[role="listbox"]',
                'div[aria-haspopup="listbox"]',
                'div[role="menu"]'
            ]
            option_selectors = [
                '[role="option"]',
                'div[role="menuitem"]',
                'li',
                'div[role="option"]'
            ]
            for cont in suggestion_containers:
                try:
                    container = await page.wait_for_selector(cont, timeout=2500)
                    if not container:
                        continue
                    for opt in option_selectors:
                        try:
                            first = await container.query_selector(opt)
                            if first:
                                await first.click()
                                await page.wait_for_timeout(300)
                                return True
                        except:
                            continue
                except:
                    continue
            return False

        await page.focus(textbox_selector)
        words = quote_text.split(' ')
        for idx, word in enumerate(words):
            if word.startswith('@'):
                for ch in word:
                    await page.keyboard.type(ch, delay=100)
                await page.wait_for_timeout(700)
                chosen = await choose_first_suggestion()
                if not chosen:
                    print(f"The dropdown list for {word} didn’t appear — let’s move on")
            else:
                await page.keyboard.type(word, delay=40)

            if idx < len(words) - 1:
                await page.keyboard.type(' ', delay=20)

        await page.wait_for_timeout(500)

        if image_path:
            input_file = await page.query_selector('input[type="file"][data-testid="fileInput"]')
            if input_file:
                await input_file.set_input_files(image_path)
                await page.wait_for_timeout(2000)

        post_button_selectors = [
            'button[data-testid="tweetButtonInline"]',
            'button[data-testid="tweetButton"]',
            'div[data-testid="tweetButtonInline"]',
            'div[data-testid="tweetButton"]',
        ]

        post_clicked = False
        for sel in post_button_selectors:
            try:
                btns = await page.query_selector_all(sel)
                for btn in btns:
                    try:
                        if not await btn.is_visible():
                            continue
                        aria_disabled = await btn.get_attribute('aria-disabled')
                        disabled_attr = await btn.get_attribute('disabled')
                        if aria_disabled == 'true' or disabled_attr is not None:
                            continue
                        await btn.click()
                        post_clicked = True
                        break
                    except:
                        continue
                if post_clicked:
                    break
            except:
                continue

        if not post_clicked:
            print("The publish button was not found or is disabled (perhaps not all tags have been selected).")
            await save_debug_info(page, 'post_button_not_found')
            return False

        print("The quoted repost has been published!")
        await page.wait_for_timeout(2000)
        return True

    except Exception as e:
        print(f"Error in the quoted repost: {e}")
        try:
            await save_debug_info(page, 'exception_quote_retweet')
        except:
            pass
        return False

async def attempt_auth_token_login(context, page, auth_token, account_idx):
    """
    Пробуем войти через auth_token.
    Возвращает True, если вход успешен, False — если нет.
    """
    try:
        ok = await set_auth_token_cookie(context, auth_token)
        if ok:
            await page.goto("https://twitter.com/home")
            await page.wait_for_timeout(3000)
            await page.reload()
            await page.wait_for_timeout(2000)
            try:
                await page.wait_for_selector('[data-testid="SideNav_NewTweet_Button"]', timeout=7000)
                print(f"[Account {account_idx+1}] Login with auth_token successful!")
                return True
            except Exception as e:
                print(f"[Account {account_idx+1}] auth_token did not work: {e}")
    except Exception as e:
        print(f"[Account {account_idx+1}] Error attempting to log in with auth_token: {e}")
    return False


async def attempt_cookies_login(context, page, cookies_path, account_idx):
    """
    Пробуем войти через куки из файла.
    Возвращает True, если вход успешен, False — если нет.
    """
    try:
        cookies_loaded = await load_cookies_to_context(context, cookies_path)
        if cookies_loaded:
            await page.goto("https://twitter.com/home")
            await page.wait_for_timeout(3000)
            await page.reload()
            await page.wait_for_timeout(2000)
            try:
                await page.wait_for_selector('[data-testid="SideNav_NewTweet_Button"]', timeout=7000)
                print(f"[Account {account_idx+1}] Cookie login successful!")
                return True
            except Exception as e:
                print(f"[Account {account_idx+1}: Cookies are invalid: {e}")
    except Exception as e:
        print(f"[Account {account_idx+1}] Error loading cookies: {e}")
    return False


async def main():
    global CUSTOM_NUM_ACCOUNTS, CUSTOM_POST_INTERVAL

    num_accounts = CUSTOM_NUM_ACCOUNTS or NUM_ACCOUNTS
    post_interval = CUSTOM_POST_INTERVAL or POST_INTERVAL_SECONDS

    print("Launching auto-posting of quoted reposts!")

    auth_tokens = load_auth_tokens_from_file()
    tweets = load_tweets_from_file()

    print(f"Account count: {len(auth_tokens)}")
    print(f"Tweet count: {len(tweets)}")

    if len(tweets) < len(auth_tokens) * POSTS_NUM:
        print(f"⚠️ Not enough tweets. At least {len(auth_tokens) * POSTS_NUM} are needed, but there are {len(tweets)}.")

    num_accounts = len(auth_tokens)
    all_cookies_paths = [os.path.join(COOKIES_DIR, f"cookies_account{i+1}.json") for i in range(num_accounts)]

    post_to_quote = get_post_to_quote()
    if not post_to_quote:
        print("Error: post for quoting not found in the file post_to_quote.txt")
        return

    browsers = [None] * num_accounts
    contexts = [None] * num_accounts
    pages = [None] * num_accounts
    ACCOUNT_ERRORS = {}
    used_accounts = []
    used_tweet_indices = []

    async with async_playwright() as p:
        for i in range(0, num_accounts, BATCH_SIZE):
            print(f"\nProcessing accounts from {i+1} to {min(i+BATCH_SIZE, num_accounts)}...")

            for j in range(i, min(i + BATCH_SIZE, num_accounts)):
                if ACCOUNT_ERRORS.get(j) is not None:
                    print(f"[Account {j+1}] Skipped (error: {ACCOUNT_ERRORS.get(j)})")
                    continue

                browser = context = page = None
                try:
                    browser = await p.chromium.launch(headless=False)
                    context = await browser.new_context()
                    page = await context.new_page()

                    cookies_path = all_cookies_paths[j]
                    auth_token = auth_tokens[j] if j < len(auth_tokens) else None

                    cookies_loaded = False
                    if auth_token:
                        cookies_loaded = await attempt_auth_token_login(context, page, auth_token, j)

                    if not cookies_loaded and os.path.exists(cookies_path):
                        cookies_loaded = await attempt_cookies_login(context, page, cookies_path, j)

                    if not cookies_loaded:
                        print(f"[Account {j+1}] Login failed. Skipping.")
                        used_accounts.append(j)
                        continue

                    for n in range(POSTS_NUM):
                        quote_index = j * POSTS_NUM + n
                        if quote_index >= len(tweets):
                            print(f"[Account {j+1}] ❗ Not enough tweets for posting. idx {quote_index}")
                            break

                        quote_text = tweets[quote_index]
                        print(f"[Account {j+1}] ✍️ Tweet {n+1}: {quote_text[:50]}...")

                        try:
                            ok = await quote_retweet(page, post_to_quote, quote_text, None)
                            if ok:
                                used_tweet_indices.append(quote_index)
                                print(f"[Account {j+1}] Tweet {n+1} has been successfully published!")
                            else:
                                print(f"[Account {j+1}] Error publishing tweet {n+1}")
                        except Exception as e:
                            print(f"[Account {j+1}] Error publishing tweet: {e}")
                            break

                        await asyncio.sleep(1)

                except Exception as e:
                    print(f"[Account {j+1}] ⚠️ General Error: {e}")

                finally:
                    if browser:
                        try:
                            await browser.close()
                        except Exception:
                            pass
                    used_accounts.append(j)

        print("\n=== Deletion of Processed Accounts ===")
        for idx in sorted(set(used_accounts), reverse=True):
            if idx < len(auth_tokens):
                del auth_tokens[idx]

            if os.path.exists(all_cookies_paths[idx]):
                os.remove(all_cookies_paths[idx])
                print(f"[Account {idx+1}] 🗑 Cookies deleted")

            print(f"[Account {idx+1}] 🚫 account deleted")

        save_auth_tokens_to_file(auth_tokens)

        print("\n=== Deleting Published Tweets ===")
        used_tweet_indices = sorted(set(used_tweet_indices))
        tweets = [t for i, t in enumerate(tweets) if i not in used_tweet_indices]
        save_tweets_to_file(tweets)
        print(f"🧾 Removed {len(used_tweet_indices)} tweets")

def save_auth_tokens_to_file(tokens):
    with open(AUTH_TOKENS_PATH, "w", encoding="utf-8") as f:
        for t in tokens:
            f.write(t.strip() + "\n")

def save_tweets_to_file(tweets):
    with open(QUOTE_TEXT_PATH, "w", encoding="utf-8") as f:
        for t in tweets:
            f.write(t.strip() + "\n")

if __name__ == "__main__":
    asyncio.run(main())
