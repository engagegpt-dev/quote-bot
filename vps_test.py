#!/usr/bin/env python3
"""
VPS Compatibility Test for Playwright Quote Bot
Run this script on your VPS to verify compatibility
"""

import asyncio
import sys
import subprocess
import platform
from playwright.async_api import async_playwright

async def test_playwright():
    """Test Playwright installation and browser functionality"""
    print("🧪 Testing Playwright...")
    
    try:
        async with async_playwright() as p:
            print("✅ Playwright imported successfully")
            
            # Test browser launch
            browser = await p.chromium.launch(headless=True)
            print("✅ Chromium browser launched")
            
            # Test page creation
            page = await browser.new_page()
            print("✅ Page created")
            
            # Test navigation
            await page.goto("https://httpbin.org/get")
            print("✅ Navigation works")
            
            # Test JavaScript execution
            result = await page.evaluate("() => navigator.userAgent")
            print(f"✅ JavaScript execution: {result[:50]}...")
            
            await browser.close()
            print("✅ Browser closed properly")
            
        return True
    except Exception as e:
        print(f"❌ Playwright test failed: {e}")
        return False

def test_system_requirements():
    """Test system requirements"""
    print("🔍 Checking system requirements...")
    
    # Check OS
    os_info = platform.system()
    print(f"OS: {os_info}")
    
    # Check Python version
    python_version = sys.version
    print(f"Python: {python_version}")
    
    # Check memory
    try:
        with open('/proc/meminfo', 'r') as f:
            meminfo = f.read()
            for line in meminfo.split('\n'):
                if 'MemTotal' in line:
                    mem_kb = int(line.split()[1])
                    mem_gb = mem_kb / 1024 / 1024
                    print(f"RAM: {mem_gb:.1f} GB")
                    if mem_gb < 1.5:
                        print("⚠️  Warning: Less than 1.5GB RAM may cause issues")
                    else:
                        print("✅ RAM sufficient")
                    break
    except:
        print("❓ Could not check RAM")
    
    # Check disk space
    try:
        result = subprocess.run(['df', '-h', '/'], capture_output=True, text=True)
        print(f"Disk space: {result.stdout.split()[10]} available")
    except:
        print("❓ Could not check disk space")

def install_dependencies():
    """Install required dependencies"""
    print("📦 Installing dependencies...")
    
    commands = [
        "pip install playwright fastapi uvicorn httpx",
        "playwright install chromium",
        "playwright install-deps"
    ]
    
    for cmd in commands:
        print(f"Running: {cmd}")
        try:
            result = subprocess.run(cmd.split(), capture_output=True, text=True)
            if result.returncode == 0:
                print("✅ Success")
            else:
                print(f"❌ Failed: {result.stderr}")
        except Exception as e:
            print(f"❌ Error: {e}")

async def test_twitter_access():
    """Test Twitter/X access"""
    print("🐦 Testing Twitter/X access...")
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            # Test Twitter access
            await page.goto("https://x.com", timeout=30000)
            title = await page.title()
            print(f"✅ Twitter accessible: {title}")
            
            await browser.close()
        return True
    except Exception as e:
        print(f"❌ Twitter access failed: {e}")
        return False

async def main():
    """Run all tests"""
    print("🚀 VPS Compatibility Test for Quote Retweet Bot")
    print("=" * 50)
    
    # System requirements
    test_system_requirements()
    print()
    
    # Install dependencies
    install_dependencies()
    print()
    
    # Test Playwright
    playwright_ok = await test_playwright()
    print()
    
    # Test Twitter access
    twitter_ok = await test_twitter_access()
    print()
    
    # Final result
    print("📊 Test Results:")
    print(f"Playwright: {'✅ PASS' if playwright_ok else '❌ FAIL'}")
    print(f"Twitter Access: {'✅ PASS' if twitter_ok else '❌ FAIL'}")
    
    if playwright_ok and twitter_ok:
        print("\n🎉 VPS is compatible! You can deploy the Quote Bot.")
    else:
        print("\n⚠️  VPS has compatibility issues. Check the errors above.")

if __name__ == "__main__":
    asyncio.run(main())