# Quote Retweet Bot

Automated quote retweet system with TwiBoost integration.

## 🚀 Quick Start with GitHub Codespaces

1. Click "Code" → "Codespaces" → "Create codespace"
2. Wait for setup (2-3 minutes)
3. Run: `python api_server.py`
4. API available at forwarded port 8000

## 📡 API Usage

### Start Campaign
```bash
curl -X POST "http://localhost:8000/quote/start" \
  -H "Content-Type: application/json" \
  -d '{
    "post_url": "https://x.com/user/status/123",
    "quote_texts": ["@user1 Great post!", "@user2 Amazing!"],
    "auth_tokens": ["token1", "token2"],
    "boost_enabled": true
  }'
```

### Check Status
```bash
curl "http://localhost:8000/status"
```

### Stop Campaign
```bash
curl -X POST "http://localhost:8000/quote/stop"
```

## 🔧 Configuration

Update config via API:
```bash
curl -X POST "http://localhost:8000/config/update" \
  -H "Content-Type: application/json" \
  -d '{
    "twiboost_api_key": "your_key",
    "post_interval": 3600
  }'
```

## 📊 Monitoring

- Logs: `GET /logs`
- Status: `GET /status`
- API Docs: `http://localhost:8000/docs`