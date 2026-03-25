"""Generic RSS/Atom feed scraper."""

from __future__ import annotations

import structlog
import httpx
import feedparser
from dataclasses import dataclass
from datetime import datetime, timezone

log = structlog.get_logger()


@dataclass
class FeedItem:
    url: str
    title: str
    text: str
    author: str
    published_at: datetime | None


class RSSScraper:
    """Scrapes RSS/Atom feeds."""

    def __init__(self, timeout: int = 30, user_agent: str = "247sales-bot/0.1") -> None:
        self._client = httpx.Client(
            timeout=timeout,
            headers={"User-Agent": user_agent},
        )

    def fetch_feed(self, feed_url: str, max_items: int = 20) -> list[FeedItem]:
        """Fetch and parse an RSS/Atom feed."""
        try:
            resp = self._client.get(feed_url)
            resp.raise_for_status()
            feed = feedparser.parse(resp.text)
            items = []
            for entry in feed.entries[:max_items]:
                published = None
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    from time import mktime
                    published = datetime.fromtimestamp(mktime(entry.published_parsed), tz=timezone.utc)
                items.append(FeedItem(
                    url=entry.get("link", ""),
                    title=entry.get("title", ""),
                    text=entry.get("summary", entry.get("description", "")),
                    author=entry.get("author", ""),
                    published_at=published,
                ))
            log.info("rss_results", feed=feed_url, count=len(items))
            return items
        except Exception as e:
            log.warning("rss_fetch_failed", feed=feed_url, error=str(e))
            return []

    def close(self) -> None:
        self._client.close()
