"""Base agent class with shared collection and digest logic."""

from __future__ import annotations

import structlog
from abc import ABC, abstractmethod
from datetime import datetime, timezone, timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from src.config import Settings
from src.db.models import AgentType, Article, DigestLog
from src.db.session import get_session
from src.processing.dedup import normalize_url, compute_simhash, is_near_duplicate

log = structlog.get_logger()


class BaseAgent(ABC):
    """Abstract base agent for scraping, deduplicating, and digesting content."""

    agent_type: AgentType

    def __init__(self, config: Settings, summarizer, notifiers: list) -> None:
        self.config = config
        self.summarizer = summarizer
        self.notifiers = notifiers

    @abstractmethod
    def collect(self) -> list[dict]:
        """Collect raw items from sources. Each dict has: url, title, text, author, source, published_at."""
        ...

    def run_collection(self) -> int:
        """Run collection, dedup, and store. Returns count of new articles."""
        log.info("collection_start", agent=self.agent_type.value)
        raw_items = self.collect()
        log.info("collection_raw", agent=self.agent_type.value, count=len(raw_items))

        session = get_session()
        new_count = 0

        # Get recent simhashes for dedup
        week_ago = datetime.now(timezone.utc) - timedelta(days=7)
        existing_hashes = [
            row[0] for row in session.execute(
                select(Article.simhash).where(
                    Article.agent == self.agent_type,
                    Article.collected_at >= week_ago,
                    Article.simhash.isnot(None),
                )
            ).all()
        ]

        for item in raw_items:
            url = normalize_url(item.get("url", ""))
            if not url:
                continue

            text = item.get("text", "")
            simhash = compute_simhash(text) if text else None
            duplicate = False
            if simhash and existing_hashes:
                duplicate = is_near_duplicate(simhash, existing_hashes)

            article = Article(
                agent=self.agent_type,
                source=item.get("source"),
                url=url,
                title=item.get("title", "")[:1024],
                content_text=text,
                author=item.get("author"),
                published_at=item.get("published_at"),
                simhash=simhash,
                is_duplicate=duplicate,
            )

            try:
                session.add(article)
                session.commit()
                new_count += 1
                if simhash:
                    existing_hashes.append(simhash)
            except IntegrityError:
                session.rollback()  # URL already exists
            except Exception as e:
                session.rollback()
                log.warning("article_save_failed", url=url, error=str(e))

        session.close()
        log.info("collection_done", agent=self.agent_type.value, new=new_count, total_raw=len(raw_items))
        return new_count

    def run_digest(self) -> None:
        """Generate and send daily digest of unsent, non-duplicate articles."""
        log.info("digest_start", agent=self.agent_type.value)
        session = get_session()

        articles = session.execute(
            select(Article).where(
                Article.agent == self.agent_type,
                Article.sent_in_digest == False,  # noqa: E712
                Article.is_duplicate == False,  # noqa: E712
            ).order_by(Article.collected_at.desc()).limit(50)
        ).scalars().all()

        if not articles:
            log.info("digest_empty", agent=self.agent_type.value)
            session.close()
            return

        # Generate summaries for articles that don't have one
        for article in articles:
            if not article.summary and article.content_text:
                article.summary = self.summarizer.summarize(article.content_text)
                session.commit()

        # Build digest
        items = [
            {
                "title": a.title,
                "text": a.content_text,
                "summary": a.summary,
                "source": a.source.value if hasattr(a.source, "value") else a.source,
                "url": a.url,
                "author": a.author,
            }
            for a in articles
        ]

        digest_text = self.summarizer.summarize_digest(items)
        agent_label = "Agentic AI Trends" if self.agent_type == AgentType.AI_TRENDS else "SEO & Marketing"
        subject = f"Daily Digest: {agent_label} ({datetime.now(timezone.utc).strftime('%Y-%m-%d')})"

        # Build HTML version
        digest_html = f"<h2>{subject}</h2><pre>{digest_text}</pre>"

        # Send via all configured notifiers
        for notifier in self.notifiers:
            channel = type(notifier).__name__
            try:
                success = notifier.send(subject, digest_html, digest_text)
                session.add(DigestLog(
                    agent=self.agent_type,
                    article_count=len(articles),
                    channel=channel,
                    status="success" if success else "failed",
                ))
            except Exception as e:
                session.add(DigestLog(
                    agent=self.agent_type,
                    article_count=len(articles),
                    channel=channel,
                    status="failed",
                    error_message=str(e),
                ))
                log.error("digest_notify_failed", channel=channel, error=str(e))

        # Mark articles as sent
        for article in articles:
            article.sent_in_digest = True
        session.commit()
        session.close()
        log.info("digest_sent", agent=self.agent_type.value, count=len(articles))
