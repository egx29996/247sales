"""arxiv paper scraper using the public Atom feed API."""

from __future__ import annotations

import structlog
import httpx
import feedparser
from dataclasses import dataclass
from datetime import datetime, timezone

log = structlog.get_logger()

ARXIV_API = "http://export.arxiv.org/api/query"


@dataclass
class ArxivPaper:
    url: str
    title: str
    abstract: str
    authors: list[str]
    published_at: datetime | None


class ArxivScraper:
    """Scrapes arxiv for papers via the Atom API."""

    def __init__(self, timeout: int = 30) -> None:
        self._client = httpx.Client(timeout=timeout)

    def search(self, query: str, max_results: int = 10) -> list[ArxivPaper]:
        """Search arxiv papers."""
        try:
            resp = self._client.get(
                ARXIV_API,
                params={
                    "search_query": f"all:{query}",
                    "start": 0,
                    "max_results": max_results,
                    "sortBy": "submittedDate",
                    "sortOrder": "descending",
                },
            )
            resp.raise_for_status()
            feed = feedparser.parse(resp.text)
            return self._parse_feed(feed)
        except Exception as e:
            log.warning("arxiv_search_failed", query=query, error=str(e))
            return []

    def _parse_feed(self, feed: feedparser.FeedParserDict) -> list[ArxivPaper]:
        papers = []
        for entry in feed.entries:
            published = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                from time import mktime
                published = datetime.fromtimestamp(mktime(entry.published_parsed), tz=timezone.utc)
            authors = [a.get("name", "") for a in entry.get("authors", [])]
            papers.append(ArxivPaper(
                url=entry.get("link", ""),
                title=entry.get("title", "").replace("\n", " ").strip(),
                abstract=entry.get("summary", "").replace("\n", " ").strip(),
                authors=authors,
                published_at=published,
            ))
        log.info("arxiv_results", count=len(papers))
        return papers

    def close(self) -> None:
        self._client.close()
