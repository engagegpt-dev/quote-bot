from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
import asyncio
import json
import os
from typing import List, Optional
import uvicorn
from quote_retweet_bot_vps import QuoteRetweetBot

app = FastAPI(title="Quote Retweet Bot API", version="1.0.0")

# Models
class QuoteRequest(BaseModel):
    post_url: str
    quote_texts: List[str]
    auth_tokens: List[str]
    boost_enabled: bool = True

class BotStatus(BaseModel):
    is_running: bool
    tweets_sent: int
    errors: int
    last_activity: Optional[str]

class ConfigUpdate(BaseModel):
    twiboost_api_key: Optional[str] = None
    post_interval: Optional[int] = None
    batch_size: Optional[int] = None

# Global bot instance
bot = QuoteRetweetBot()

@app.get("/")
async def root():
    return {"message": "Quote Retweet Bot API", "status": "online"}

@app.post("/quote/start")
async def start_quote_campaign(request: QuoteRequest, background_tasks: BackgroundTasks):
    """Start a quote retweet campaign"""
    if bot.is_running:
        raise HTTPException(status_code=400, detail="Bot is already running")
    
    try:
        background_tasks.add_task(
            bot.run_campaign,
            request.post_url,
            request.quote_texts,
            request.auth_tokens,
            request.boost_enabled
        )
        return {"message": "Campaign started", "status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/quote/stop")
async def stop_campaign():
    """Stop the current campaign"""
    if not bot.is_running:
        raise HTTPException(status_code=400, detail="No campaign is running")
    
    bot.stop_campaign()
    return {"message": "Campaign stopped", "status": "success"}

@app.get("/status")
async def get_status() -> BotStatus:
    """Get bot status"""
    return BotStatus(
        is_running=bot.is_running,
        tweets_sent=bot.tweets_sent,
        errors=bot.errors,
        last_activity=bot.last_activity
    )

@app.post("/config/update")
async def update_config(config: ConfigUpdate):
    """Update bot configuration"""
    try:
        bot.update_config(config.dict(exclude_none=True))
        return {"message": "Configuration updated", "status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/logs")
async def get_logs():
    """Get recent logs"""
    return {"logs": bot.get_logs()}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)