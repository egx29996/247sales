"""Twitter/X scraper using API v2 free tier with Nitter RSS fallback."""

from __future__ import annotations

import structlog
import httpx
import feedparser
from dataclasses import dataclass
from datetime import datetime, timezone

from src.utils.rate_limiter import RateLimiter

log = structlog.get_logger()


@dataclass
class TweetData:
    url: str
    text: str
    author: str
    created_at: datetime | None


class TwitterScraper:
    """Scrapes Twitter via API v2 (free tier) with Nitter RSS fallback."""

    def __init__(
        self,
        bearer_token: str = "",
        nitter_instances: list[str] | None = None,
        timeout: int = 30,
        user_agent: str = "247sales-bot/0.1",
    ) -> None:
        self.bearer_token = bearer_token
        self.nitter_instances = nitter_instances or ["nitter.net"]
        self.timeout = timeout
        self.user_agent = user_agent
        self._rate_limiter = RateLimiter(max_tokens=1, refill_seconds=900)  # 1 req / 15 min
        self._client = httpx.Client(timeout=timeout, headers={"User-Agent": user_agent})

    def search_tweets(self, query: str, max_results: int = 10) -> list[TweetData]:
        """Search recent tweets. Tries API v2 first, then Nitter RSS."""
        if self.bearer_token:
            try:
                return self._search_api_v2(query, max_results)
            except Exception as e:
                log.warning("twitter_api_failed", error=str(e), query=query)

        return self._search_nitter_rss(query, max_results)

    def get_user_tweets(self, username: str, max_results: int = 20) -> list[TweetData]:
        """Get recent tweets from a specific user via Nitter RSS."""
        return self._get_user_nitter_rss(username, max_results)

    def _search_api_v2(self, query: str, max_results: int) -> list[TweetData]:
        """Use Twitter API v2 recent search endpoint."""
        if not self._rate_limiter.acquire(timeout=5):
            log.info("twitter_rate_limited", query=query)
            return []

        resp = self._client.get(
            "https://api.twitter.com/2/tweets/search/recent",
            params={
                "query": f"{query} -is:retweet lang:en",
                "max_results": min(max_results, 10),
                "tweet.fields": "created_at,author_id,text",
                "expansions": "author_id",
                "user.fields": "username",
            },
            headers={"Authorization": f"Bearer {self.bearer_token}"},
        )

        # Update rate limiter from headers
        self._rate_limiter.update_from_headers(
            remaining=_int_or_none(resp.headers.get("x-rate-limit-remaining")),
            reset_time=_int_or_none(resp.headers.get("x-rate-limit-reset")),
        )

        resp.raise_for_status()
        data = resp.json()

        users = {}
        if "includes" in data and "users" in data["includes"]:
            users = {u["id"]: u["username"] for u in data["includes"]["users"]}

        tweets = []
        for tweet in data.get("data", []):
            author = users.get(tweet.get("author_id"), "unknown")
            created = None
            if "created_at" in tweet:
                created = datetime.fromisoformat(tweet["created_at"].replace("Z", "+00:00"))
            tweets.append(TweetData(
                url=f"https://twitter.com/{author}/status/{tweet['id']}",
                text=tweet["text"],
                author=author,
                created_at=created,
            ))
        log.info("twitter_api_results", query=query, count=len(tweets))
        return tweets

    def _search_nitter_rss(self, query: str, max_results: int) -> list[TweetData]:
        """Fallback: search via Nitter RSS."""
        for instance in self.nitter_instances:
            try:
                url = f"https://{instance}/search/rss?f=tweets&q={query}"
                resp = self._client.get(url)
                if resp.status_code != 200:
                    continue
                feed = feedparser.parse(resp.text)
                tweets = self._parse_nitter_feed(feed, max_results)
                if tweets:
                    log.info("nitter_search_results", instance=instance, query=query, count=len(tweets))
                    return tweets
            except Exception as e:
                log.warning("nitter_instance_failed", instance=instance, error=str(e))
                continue
        log.warning("all_nitter_instances_failed", query=query)
        return []

    def _get_user_nitter_rss(self, username: str, max_results: int) -> list[TweetData]:
        """Get user timeline via Nitter RSS."""
        for instance in self.nitter_instances:
            try:
                url = f"https://{instance}/{username}/rss"
                resp = self._client.get(url)
                if resp.status_code != 200:
                    continue
                feed = feedparser.parse(resp.text)
                tweets = self._parse_nitter_feed(feed, max_results)
                if tweets:
                    log.info("nitter_user_results", instance=instance, user=username, count=len(tweets))
                    return tweets
            except Exception as e:
                log.warning("nitter_user_failed", instance=instance, user=username, error=str(e))
                continue
        return []

    def _parse_nitter_feed(self, feed: feedparser.FeedParserDict, max_results: int) -> list[TweetData]:
        tweets = []
        for entry in feed.entries[:max_results]:
            created = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                from time import mktime
                created = datetime.fromtimestamp(mktime(entry.published_parsed), tz=timezone.utc)
            author = entry.get("author", entry.get("dc_creator", "unknown"))
            # Clean author (Nitter formats as @username)
            if author.startswith("@"):
                author = author[1:]
            tweets.append(TweetData(
                url=entry.get("link", ""),
                text=entry.get("title", entry.get("summary", "")),
                author=author,
                created_at=created,
            ))
        return tweets

    def close(self) -> None:
        self._client.close()


def _int_or_none(val: str | None) -> int | None:
    if val is None:
        return None
    try:
        return int(val)
    except ValueError:
        return None
