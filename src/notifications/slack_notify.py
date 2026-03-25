"""Slack notification via incoming webhook."""

from __future__ import annotations

import httpx
import structlog

log = structlog.get_logger()


class SlackNotifier:
    def __init__(self, webhook_url: str) -> None:
        self.webhook_url = webhook_url

    def send(self, subject: str, body_html: str, body_text: str) -> bool:
        """Send a Slack message via webhook."""
        try:
            payload = {
                "blocks": [
                    {"type": "header", "text": {"type": "plain_text", "text": subject[:150]}},
                    {"type": "section", "text": {"type": "mrkdwn", "text": body_text[:3000]}},
                ]
            }
            resp = httpx.post(self.webhook_url, json=payload, timeout=15)
            resp.raise_for_status()
            log.info("slack_sent", subject=subject)
            return True
        except Exception as e:
            log.error("slack_send_failed", error=str(e))
            return False
