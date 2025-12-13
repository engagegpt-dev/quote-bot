import httpx
import asyncio
import json

# Test script for Quote Bot API

BASE_URL = "http://localhost:8000"  # Change to your Codespace URL

async def test_api():
    async with httpx.AsyncClient() as client:
        
        # 1. Check status
        print("🔍 Checking bot status...")
        response = await client.get(f"{BASE_URL}/status")
        print(f"Status: {response.json()}")
        
        # 2. List accounts
        print("\n👥 Listing accounts...")
        response = await client.get(f"{BASE_URL}/accounts")
        print(f"Accounts: {response.json()}")
        
        # 3. Add new account (example)
        print("\n➕ Adding test account...")
        new_account = {
            "username": "testuser",
            "password": "testpass",
            "email": "test@example.com",
            "auth_token": "test_token_123",
            "totp_secret": "TESTTOTP123",
            "registration_year": 2020
        }
        response = await client.post(f"{BASE_URL}/accounts/add", json=new_account)
        print(f"Add account: {response.json()}")
        
        # 4. Start quote campaign
        print("\n🚀 Starting quote campaign...")
        campaign = {
            "tweet_url": "https://x.com/elonmusk/status/1234567890",
            "users_to_tag": ["user1", "user2", "user3"],
            "message": "Great post! 🚀",
            "account_ids": [1]  # Use only account ID 1
        }
        response = await client.post(f"{BASE_URL}/quote/start", json=campaign)
        print(f"Campaign: {response.json()}")
        
        # 5. Check logs
        await asyncio.sleep(2)
        print("\n📋 Getting logs...")
        response = await client.get(f"{BASE_URL}/logs")
        logs = response.json()["logs"]
        for log in logs[-5:]:  # Show last 5 logs
            print(f"  {log}")

if __name__ == "__main__":
    asyncio.run(test_api())