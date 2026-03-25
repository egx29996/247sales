"""Reddit scraper using the public JSON API (no auth required)."""

from __future__ import annotations

import structlog
import httpx
from dataclasses import dataclass
from datetime import datetime, timezone

log = structlog.get_logger()


@dataclass
class RedditPost:
    url: str
    title: str
    text: str
    author: str
    subreddit: str
    score: int
    created_at: datetime | None


class RedditScraper:
    """Scrapes Reddit using the public .json API."""

    def __init__(self, timeout: int = 30, user_agent: str = "247sales-bot/0.1") -> None:
        self.timeout = timeout
        self._client = httpx.Client(
            timeout=timeout,
            headers={"User-Agent": user_agent},
        )

    def search_subreddit(self, subreddit: str, query: str, sort: str = "new", limit: int = 25) -> list[RedditPost]:
        """Search a subreddit for posts matching the query."""
        try:
            resp = self._client.get(
                f"https://www.reddit.com/r/{subreddit}/search.json",
                params={"q": query, "sort": sort, "limit": limit, "restrict_sr": "on", "t": "day"},
            )
            resp.raise_for_status()
            return self._parse_listing(resp.json())
        except Exception as e:
            log.warning("reddit_search_failed", subreddit=subreddit, query=query, error=str(e))
            return []

    def get_hot_posts(self, subreddit: str, limit: int = 25) -> list[RedditPost]:
        """Get hot posts from a subreddit."""
        try:
            resp = self._client.get(
                f"https://www.reddit.com/r/{subreddit}/hot.json",
                params={"limit": limit},
            )
            resp.raise_for_status()
            return self._parse_listing(resp.json())
        except Exception as e:
            log.warning("reddit_hot_failed", subreddit=subreddit, error=str(e))
            return []

    def _parse_listing(self, data: dict) -> list[RedditPost]:
        posts = []
        for child in data.get("data", {}).get("children", []):
            d = child.get("data", {})
            if d.get("is_self", False):
                text = d.get("selftext", "")
            else:
                text = d.get("title", "")
            posts.append(RedditPost(
                url=f"https://reddit.com{d.get('permalink', '')}",
                title=d.get("title", ""),
                text=text,
                author=d.get("author", "unknown"),
                subreddit=d.get("subreddit", ""),
                score=d.get("score", 0),
                created_at=datetime.fromtimestamp(d.get("created_utc", 0), tz=timezone.utc) if d.get("created_utc") else None,
            ))
        log.info("reddit_results", count=len(posts))
        return posts

    def close(self) -> None:
        self._client.close()
