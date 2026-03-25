"""Agent that monitors agentic AI tips, features, and trends across multiple sources."""

from __future__ import annotations

import structlog

from src.agents.base import BaseAgent
from src.config import Settings
from src.db.models import AgentType, SourceType
from src.scrapers.twitter import TwitterScraper
from src.scrapers.reddit import RedditScraper
from src.scrapers.hackernews import HackerNewsScraper
from src.scrapers.arxiv_scraper import ArxivScraper
from src.scrapers.rss import RSSScraper

log = structlog.get_logger()

# Search queries for agentic AI content
TWITTER_QUERIES = [
    "agentic AI tips",
    "AI agents framework",
    "LLM agents tools",
    "Claude agent SDK",
    "AI automation workflow",
]

TWITTER_ACCOUNTS = [
    "AnthropicAI",
    "OpenAI",
    "LangChainAI",
    "llaboratory_ai",
    "CrewAIInc",
]

REDDIT_SUBREDDITS = [
    ("MachineLearning", "agentic AI"),
    ("LocalLLaMA", "agent"),
    ("artificial", "AI agent"),
    ("ChatGPT", "agent tips"),
    ("ClaudeAI", "agent"),
]

HN_QUERIES = [
    "agentic AI",
    "AI agent framework",
    "LLM agent",
]

ARXIV_QUERIES = [
    "agentic AI",
    "LLM agent",
    "autonomous AI agent",
]

RSS_FEEDS = [
    "https://blog.langchain.dev/rss/",
    "https://lilianweng.github.io/index.xml",
    "https://simonwillison.net/atom/everything/",
    "https://www.latent.space/feed",
]


class AITrendsAgent(BaseAgent):
    """Collects cutting-edge agentic AI tips, features, and trends."""

    agent_type = AgentType.AI_TRENDS

    def __init__(self, config: Settings, summarizer, notifiers: list) -> None:
        super().__init__(config, summarizer, notifiers)
        self.twitter = TwitterScraper(
            bearer_token=config.TWITTER_BEARER_TOKEN,
            nitter_instances=config.NITTER_INSTANCES,
            timeout=config.REQUEST_TIMEOUT,
            user_agent=config.USER_AGENT,
        )
        self.reddit = RedditScraper(timeout=config.REQUEST_TIMEOUT, user_agent=config.USER_AGENT)
        self.hn = HackerNewsScraper(timeout=config.REQUEST_TIMEOUT)
        self.arxiv = ArxivScraper(timeout=config.REQUEST_TIMEOUT)
        self.rss = RSSScraper(timeout=config.REQUEST_TIMEOUT, user_agent=config.USER_AGENT)

    def collect(self) -> list[dict]:
        items: list[dict] = []

        # Twitter search
        for query in TWITTER_QUERIES:
            for tweet in self.twitter.search_tweets(query, max_results=10):
                items.append({
                    "url": tweet.url,
                    "title": tweet.text[:120],
                    "text": tweet.text,
                    "author": tweet.author,
                    "source": SourceType.TWITTER,
                    "published_at": tweet.created_at,
                })

        # Twitter accounts
        for account in TWITTER_ACCOUNTS:
            for tweet in self.twitter.get_user_tweets(account, max_results=10):
                items.append({
                    "url": tweet.url,
                    "title": tweet.text[:120],
                    "text": tweet.text,
                    "author": tweet.author,
                    "source": SourceType.TWITTER,
                    "published_at": tweet.created_at,
                })

        # Reddit
        for subreddit, query in REDDIT_SUBREDDITS:
            for post in self.reddit.search_subreddit(subreddit, query, limit=10):
                items.append({
                    "url": post.url,
                    "title": post.title,
                    "text": post.text or post.title,
                    "author": post.author,
                    "source": SourceType.REDDIT,
                    "published_at": post.created_at,
                })

        # Hacker News
        for query in HN_QUERIES:
            for post in self.hn.search(query, limit=10):
                items.append({
                    "url": post.url,
                    "title": post.title,
                    "text": post.text or post.title,
                    "author": post.author,
                    "source": SourceType.HACKERNEWS,
                    "published_at": post.created_at,
                })

        # arxiv
        for query in ARXIV_QUERIES:
            for paper in self.arxiv.search(query, max_results=5):
                items.append({
                    "url": paper.url,
                    "title": paper.title,
                    "text": paper.abstract,
                    "author": ", ".join(paper.authors[:3]),
                    "source": SourceType.ARXIV,
                    "published_at": paper.published_at,
                })

        # RSS feeds
        for feed_url in RSS_FEEDS:
            for item in self.rss.fetch_feed(feed_url, max_items=10):
                items.append({
                    "url": item.url,
                    "title": item.title,
                    "text": item.text,
                    "author": item.author,
                    "source": SourceType.RSS,
                    "published_at": item.published_at,
                })

        log.info("ai_trends_collected", total=len(items))
        return items
