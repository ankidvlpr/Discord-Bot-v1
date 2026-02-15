# 🤖 Discord Bounty Bot - Fully Deployable

A production-ready Discord bot that posts RentAHuman bounties with location-based alerts. **NO API KEY REQUIRED** for testing - includes built-in mock API!

## ✨ Features

✅ **Zero Setup Testing** - Built-in mock API, no keys needed  
✅ **One-Command Deploy** - Docker Compose for instant deployment  
✅ **Production Ready** - Async code, retry logic, error handling  
✅ **Location Alerts** - Subscribe to specific locations (Remote, NYC, SF, etc.)  
✅ **Rich Embeds** - Beautiful Discord embeds with all bounty details  
✅ **Permission Controls** - Only admins can configure bot  
✅ **Easy API Swap** - Switch from mock to real API with one config change  

---

## 🚀 Quick Start (2 Minutes)

### Prerequisites
- Docker & Docker Compose installed
- Discord bot token ([Get one here](https://discord.com/developers/applications))

### Deploy Now

```bash
# 1. Copy environment file
cp .env.example .env

# 2. Add your Discord token to .env
# Edit .env and set: DISCORD_TOKEN=your_token_here

# 3. Start everything
docker-compose up -d

# 4. View logs
docker-compose logs -f
```

**That's it!** Your bot is now running with a mock API generating realistic bounty data.

---

## 📱 Discord Commands

```
/setchannel #bounties           Set notification channel
/subscribe Remote               Subscribe to remote bounties
/subscribe San Francisco        Subscribe to SF bounties
/subscriptions                  View active subscriptions
/unsubscribe Remote             Unsubscribe from location
/status                         Check bot configuration
```

---

## 🧪 Testing the Mock API

The bot comes with a built-in mock API that generates realistic bounty data:

```bash
# API docs
http://localhost:8000/docs

# Get bounties
curl http://localhost:8000/bounties

# Check health
curl http://localhost:8000/health

# Filter by location
curl "http://localhost:8000/bounties?location=Remote"
```

---

## 🔄 Switch to Production API

When you're ready to use the real RentAHuman API:

1. Get your API key from RentAHuman
2. Update `.env`:
```env
USE_MOCK_API=false
API_URL=https://api.rentahuman.ai/bounties
API_KEY=your_api_key_here
```
3. Restart: `docker-compose restart bot`

Done! Bot now uses real data.

---

## 📖 Full Documentation

- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Complete deployment guide
- **[CODE_REVIEW.md](CODE_REVIEW.md)** - Code quality analysis
- **Mock API** - Test API with realistic data
- **Production Bot** - Ready for real deployment

---

## 🏗️ Architecture

```
┌─────────────────┐      ┌──────────────────┐
│   Mock API      │◄─────┤  Discord Bot     │
│  (Testing)      │      │  (Production)    │
│                 │      │                  │
│ - FastAPI       │      │ - discord.py     │
│ - Auto-gen data │      │ - aiosqlite      │
│ - No auth       │      │ - Retry logic    │
└─────────────────┘      └──────────────────┘
```

### Tech Stack
- **Bot**: Python 3.11, discord.py 2.3+, aiosqlite, tenacity
- **Mock API**: FastAPI, uvicorn
- **Database**: SQLite (easily upgradeable to PostgreSQL)
- **Deployment**: Docker, Docker Compose

---

## 📊 What Makes This Production-Ready?

✅ **Async/Await** - Non-blocking operations throughout  
✅ **Error Handling** - Try-catch blocks everywhere  
✅ **Retry Logic** - Automatic retry with exponential backoff  
✅ **Timeout Handling** - Never hangs on slow APIs  
✅ **Permission Checks** - Admin-only configuration commands  
✅ **Structured Logging** - Track everything that happens  
✅ **Rate Limit Aware** - Detects and handles API rate limits  
✅ **Database Abstraction** - Easy to swap SQLite for PostgreSQL  
✅ **Config Validation** - Fails fast with clear error messages  
✅ **Docker Support** - Containerized and portable  

---

## 🎯 Use Cases

- **Job Board Alerts** - Notify your team of new opportunities
- **Freelance Tracking** - Monitor bounties in specific locations
- **Community Engagement** - Share bounties with Discord communities
- **Personal Notifications** - Get alerts for your preferred work
- **Testing Discord Bots** - Use mock API to test bot development

---

## 🔧 Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DISCORD_TOKEN` | ✅ Yes | - | Discord bot token |
| `USE_MOCK_API` | No | `true` | Use mock API or real API |
| `API_URL` | No | `http://localhost:8000/bounties` | API endpoint |
| `API_KEY` | No | - | API key (for real API) |
| `POLL_INTERVAL` | No | `60` | Seconds between polls |

---

## 📈 Roadmap

### ✅ Phase 1 - Complete
- [x] Mock API for testing
- [x] Docker deployment
- [x] Location-based subscriptions
- [x] Retry logic
- [x] Permission checks
- [x] Rich embeds

### 🚧 Phase 2 - Production Hardening
- [ ] PostgreSQL support
- [ ] Structured logging (structlog)
- [ ] Health endpoint for monitoring
- [ ] Graceful shutdown handling
- [ ] Rate limit analytics

### 💡 Phase 3 - Feature Expansion
- [ ] Web dashboard
- [ ] Per-user DM alerts
- [ ] Reward filtering
- [ ] Keyword matching
- [ ] Daily digest mode

---

## 🤝 Contributing

This is a production-ready template. Feel free to:
- Fork and customize for your needs
- Add new features
- Improve documentation
- Report issues

---

## 📝 License

MIT License - Free to use and modify

---

## 🆘 Need Help?

Check out **[DEPLOYMENT.md](DEPLOYMENT.md)** for:
- Detailed setup instructions
- Troubleshooting guide
- Cloud deployment options (Fly.io, Railway, Heroku)
- Performance optimization tips
- Scaling strategies

---

## 🎉 Credits

Built with:
- [discord.py](https://github.com/Rapptz/discord.py) - Discord API wrapper
- [FastAPI](https://fastapi.tiangolo.com/) - Modern web framework
- [aiosqlite](https://github.com/omnilib/aiosqlite) - Async SQLite
- [tenacity](https://github.com/jd/tenacity) - Retry library

---

**Ready to deploy?** See [DEPLOYMENT.md](DEPLOYMENT.md) for the complete guide!