"""Agent that scrapes Twitter/X for SEO and marketing tips and tricks."""

from __future__ import annotations

import structlog

from src.agents.base import BaseAgent
from src.config import Settings
from src.db.models import AgentType, SourceType
from src.scrapers.twitter import TwitterScraper

log = structlog.get_logger()

# SEO/Marketing search queries
SEO_QUERIES = [
    "SEO tips 2025",
    "SEO strategy",
    "Google ranking tips",
    "content marketing tips",
    "link building strategy",
    "technical SEO",
    "keyword research tips",
    "on-page SEO",
    "local SEO tips",
    "digital marketing strategy",
]

# Known SEO/marketing influencers on Twitter
SEO_ACCOUNTS = [
    "aaborchev",       # Aleyda Solis - SEO
    "randfish",        # Rand Fishkin - SparkToro
    "JohnMu",          # John Mueller - Google
    "Marie_Haynes",    # Marie Haynes - SEO
    "stonetemple",     # Eric Enge - SEO
    "rustybrick",      # Barry Schwartz - Search Engine Roundtable
    "sengineland",     # Search Engine Land
    "seaborchev",      # Search Engine Journal
    "naborchev",       # Neil Patel
    "BrianEDean",      # Brian Dean - Backlinko
    "CyrusShepard",    # Cyrus Shepard - Zyppy
    "lilyray",         # Lily Ray - SEO
    "gaborchev",       # Glenn Gabe - SEO
    "KevinIndig",      # Kevin Indig - Growth/SEO
    "MorningScore",    # Morningscore - SEO tool
]


class TwitterSEOAgent(BaseAgent):
    """Scrapes Twitter specifically for SEO and marketing tips."""

    agent_type = AgentType.TWITTER_SEO

    def __init__(self, config: Settings, summarizer, notifiers: list) -> None:
        super().__init__(config, summarizer, notifiers)
        self.twitter = TwitterScraper(
            bearer_token=config.TWITTER_BEARER_TOKEN,
            nitter_instances=config.NITTER_INSTANCES,
            timeout=config.REQUEST_TIMEOUT,
            user_agent=config.USER_AGENT,
        )

    def collect(self) -> list[dict]:
        items: list[dict] = []

        # Search for SEO/marketing queries
        for query in SEO_QUERIES:
            for tweet in self.twitter.search_tweets(query, max_results=10):
                items.append({
                    "url": tweet.url,
                    "title": tweet.text[:120],
                    "text": tweet.text,
                    "author": tweet.author,
                    "source": SourceType.TWITTER,
                    "published_at": tweet.created_at,
                })

        # Get tweets from known SEO influencers
        for account in SEO_ACCOUNTS:
            for tweet in self.twitter.get_user_tweets(account, max_results=10):
                items.append({
                    "url": tweet.url,
                    "title": tweet.text[:120],
                    "text": tweet.text,
                    "author": tweet.author,
                    "source": SourceType.TWITTER,
                    "published_at": tweet.created_at,
                })

        log.info("twitter_seo_collected", total=len(items))
        return items
