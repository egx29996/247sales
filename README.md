# 247sales AI Agents

Two automated agents that run 24/7 and send you daily digests:

1. **Agentic AI Trends Agent** — Monitors Twitter, Reddit, Hacker News, arxiv, and RSS feeds for cutting-edge agentic AI tips, features, and trends
2. **Twitter SEO/Marketing Agent** — Scrapes Twitter/X for SEO and digital marketing tips, tricks, and strategies from top influencers

## Quick Start

### 1. Clone and configure

```bash
cp .env.example .env
# Edit .env with your credentials
```

### 2. Required: Set up at least one notification channel

**Email (Gmail example):**
```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=you@gmail.com
SMTP_PASS=your-app-password    # Use Gmail App Password, not your regular password
SMTP_FROM=you@gmail.com
SMTP_TO=you@gmail.com
```

**Slack:**
```env
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

**Telegram:**
```env
TELEGRAM_BOT_TOKEN=123456:ABC-DEF    # From @BotFather
TELEGRAM_CHAT_ID=your-chat-id        # From @userinfobot
```

### 3. Optional: Twitter API (improves Twitter scraping)

Get a free bearer token at https://developer.twitter.com/
```env
TWITTER_BEARER_TOKEN=your-bearer-token
```

Without this, the agents will use Nitter RSS as a fallback.

### 4. Run with Docker (recommended)

```bash
docker compose up -d
```

### 5. Or run locally

```bash
pip install .
python -m src.main
```

## How It Works

| Agent | Sources | Collection Frequency | Digest Time |
|-------|---------|---------------------|-------------|
| AI Trends | Twitter, Reddit, HN, arxiv, RSS | Every 2 hours | Daily 8 AM |
| SEO/Marketing | Twitter search + influencer feeds | Every 15 minutes | Daily 8 AM |

- All collected content is stored in a local SQLite database (`data/247sales.db`)
- Content is automatically deduplicated using URL normalization + SimHash
- Summaries are generated using extractive summarization (free) or optionally via LLM
- Daily digests are sent via your configured notification channel(s)

## Customization

### Change schedules (in .env)

```env
AI_TRENDS_CRON=0 */2 * * *     # Every 2 hours
TWITTER_SEO_CRON=*/15 * * * *   # Every 15 minutes
DIGEST_CRON=0 8 * * *           # Daily at 8 AM
TIMEZONE=America/New_York
```

### Use LLM for better summaries

```env
SUMMARIZER_MODE=llm
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```

Also works with Ollama or any OpenAI-compatible API:
```env
OPENAI_BASE_URL=http://localhost:11434/v1
OPENAI_MODEL=llama3
```

### Add/remove search queries and accounts

Edit the lists in `src/agents/ai_trends.py` and `src/agents/twitter_seo.py`.

## Architecture

```
src/
├── main.py              # Entry point + scheduler
├── config.py            # Settings from .env
├── agents/              # AI Trends + SEO agents
├── scrapers/            # Twitter, Reddit, HN, arxiv, RSS
├── processing/          # Dedup + summarization
├── notifications/       # Email, Slack, Telegram
├── db/                  # SQLite via SQLAlchemy
└── utils/               # Rate limiter, logging
```
