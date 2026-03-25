"""Entry point: starts the scheduler and runs both agents continuously."""

from __future__ import annotations

import signal
import sys
import time

import structlog

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from src.config import Settings
from src.db.session import init_db
from src.utils.logging_config import setup_logging
from src.processing.summarizer import get_summarizer
from src.notifications.email_notify import EmailNotifier
from src.notifications.slack_notify import SlackNotifier
from src.notifications.telegram_notify import TelegramNotifier
from src.agents.ai_trends import AITrendsAgent
from src.agents.twitter_seo import TwitterSEOAgent

log = structlog.get_logger()


def build_notifiers(config: Settings) -> list:
    """Build list of configured notification channels."""
    notifiers = []
    if config.email_configured:
        notifiers.append(EmailNotifier(
            host=config.SMTP_HOST,
            port=config.SMTP_PORT,
            user=config.SMTP_USER,
            password=config.SMTP_PASS,
            from_addr=config.SMTP_FROM,
            to_addrs=config.smtp_recipients,
        ))
        log.info("notifier_enabled", channel="email")

    if config.slack_configured:
        notifiers.append(SlackNotifier(webhook_url=config.SLACK_WEBHOOK_URL))
        log.info("notifier_enabled", channel="slack")

    if config.telegram_configured:
        notifiers.append(TelegramNotifier(
            bot_token=config.TELEGRAM_BOT_TOKEN,
            chat_id=config.TELEGRAM_CHAT_ID,
        ))
        log.info("notifier_enabled", channel="telegram")

    if not notifiers:
        log.warning("no_notifiers_configured", hint="Set SMTP, Slack, or Telegram vars in .env")

    return notifiers


def main() -> None:
    setup_logging()
    config = Settings()
    init_db(config.DATABASE_URL)

    summarizer = get_summarizer(
        mode=config.SUMMARIZER_MODE,
        api_key=config.OPENAI_API_KEY,
        base_url=config.OPENAI_BASE_URL,
        model=config.OPENAI_MODEL,
    )
    notifiers = build_notifiers(config)

    ai_agent = AITrendsAgent(config, summarizer, notifiers)
    seo_agent = TwitterSEOAgent(config, summarizer, notifiers)

    scheduler = BackgroundScheduler(timezone=config.TIMEZONE)

    # Collection jobs (scrape on schedule)
    scheduler.add_job(
        ai_agent.run_collection,
        CronTrigger.from_crontab(config.AI_TRENDS_CRON),
        id="ai_trends_collect",
        name="AI Trends Collection",
    )
    scheduler.add_job(
        seo_agent.run_collection,
        CronTrigger.from_crontab(config.TWITTER_SEO_CRON),
        id="twitter_seo_collect",
        name="Twitter SEO Collection",
    )

    # Daily digest jobs
    scheduler.add_job(
        ai_agent.run_digest,
        CronTrigger.from_crontab(config.DIGEST_CRON),
        id="ai_trends_digest",
        name="AI Trends Daily Digest",
    )
    scheduler.add_job(
        seo_agent.run_digest,
        CronTrigger.from_crontab(config.DIGEST_CRON),
        id="twitter_seo_digest",
        name="Twitter SEO Daily Digest",
    )

    scheduler.start()
    log.info("scheduler_started", jobs=[j.name for j in scheduler.get_jobs()])

    # Run initial collection on startup
    log.info("running_initial_collection")
    try:
        ai_agent.run_collection()
    except Exception as e:
        log.error("initial_ai_collection_failed", error=str(e))
    try:
        seo_agent.run_collection()
    except Exception as e:
        log.error("initial_seo_collection_failed", error=str(e))

    # Block until interrupted
    def shutdown(signum, frame):
        log.info("shutting_down")
        scheduler.shutdown(wait=False)
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    log.info("agents_running", message="Press Ctrl+C to stop")
    while True:
        time.sleep(60)


if __name__ == "__main__":
    main()
