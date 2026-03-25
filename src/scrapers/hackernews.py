"""Hacker News scraper using the Algolia Search API."""

from __future__ import annotations

import structlog
import httpx
from dataclasses import dataclass
from datetime import datetime, timezone

log = structlog.get_logger()

HN_SEARCH_URL = "https://hn.algolia.com/api/v1/search_by_date"


@dataclass
class HNPost:
    url: str
    title: str
    text: str
    author: str
    points: int
    created_at: datetime | None


class HackerNewsScraper:
    """Searches Hacker News via the Algolia API."""

    def __init__(self, timeout: int = 30) -> None:
        self._client = httpx.Client(timeout=timeout)

    def search(self, query: str, limit: int = 20) -> list[HNPost]:
        """Search HN stories and comments by query."""
        try:
            resp = self._client.get(
                HN_SEARCH_URL,
                params={"query": query, "tags": "story", "hitsPerPage": limit},
            )
            resp.raise_for_status()
            return self._parse_results(resp.json())
        except Exception as e:
            log.warning("hn_search_failed", query=query, error=str(e))
            return []

    def _parse_results(self, data: dict) -> list[HNPost]:
        posts = []
        for hit in data.get("hits", []):
            story_url = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}"
            created = None
            if hit.get("created_at"):
                try:
                    created = datetime.fromisoformat(hit["created_at"].replace("Z", "+00:00"))
                except (ValueError, TypeError):
                    pass
            posts.append(HNPost(
                url=story_url,
                title=hit.get("title", ""),
                text=hit.get("story_text") or hit.get("title", ""),
                author=hit.get("author", "unknown"),
                points=hit.get("points", 0) or 0,
                created_at=created,
            ))
        log.info("hn_results", count=len(posts))
        return posts

    def close(self) -> None:
        self._client.close()
