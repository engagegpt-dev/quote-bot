import httpx
import asyncio
import json

class QuoteBotClient:
    def __init__(self, base_url: str = "http://your-vps-ip:8000"):
        self.base_url = base_url
        
    async def start_campaign(self, post_url: str, quote_texts: list, auth_tokens: list, boost_enabled: bool = True):
        """Start a quote retweet campaign"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/quote/start",
                json={
                    "post_url": post_url,
                    "quote_texts": quote_texts,
                    "auth_tokens": auth_tokens,
                    "boost_enabled": boost_enabled
                }
            )
            return response.json()
    
    async def get_status(self):
        """Get bot status"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/status")
            return response.json()
    
    async def stop_campaign(self):
        """Stop current campaign"""
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{self.base_url}/quote/stop")
            return response.json()
    
    async def get_logs(self):
        """Get recent logs"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/logs")
            return response.json()

# Example usage
async def main():
    client = QuoteBotClient("http://your-vps-ip:8000")
    
    # Start campaign
    result = await client.start_campaign(
        post_url="https://x.com/username/status/123456789",
        quote_texts=[
            "@user1 Great post! Community-led protocols > everything else.",
            "@user2 Totally agree! Community-led protocols > everything else.",
            "@user3 This is the way! Community-led protocols > everything else."
        ],
        auth_tokens=[
            "your_auth_token_1",
            "your_auth_token_2", 
            "your_auth_token_3"
        ],
        boost_enabled=True
    )
    print("Campaign started:", result)
    
    # Check status
    status = await client.get_status()
    print("Status:", status)
    
    # Get logs
    logs = await client.get_logs()
    print("Logs:", logs)

if __name__ == "__main__":
    asyncio.run(main())