"""Telegram notification via Bot API."""

from __future__ import annotations

import httpx
import structlog

log = structlog.get_logger()


class TelegramNotifier:
    def __init__(self, bot_token: str, chat_id: str) -> None:
        self.bot_token = bot_token
        self.chat_id = chat_id

    def send(self, subject: str, body_html: str, body_text: str) -> bool:
        """Send a Telegram message."""
        try:
            # Telegram has a 4096 char limit per message
            message = f"<b>{subject}</b>\n\n{body_text}"
            if len(message) > 4096:
                message = message[:4090] + "..."

            resp = httpx.post(
                f"https://api.telegram.org/bot{self.bot_token}/sendMessage",
                json={
                    "chat_id": self.chat_id,
                    "text": message,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": True,
                },
                timeout=15,
            )
            resp.raise_for_status()
            log.info("telegram_sent", chat_id=self.chat_id, subject=subject)
            return True
        except Exception as e:
            log.error("telegram_send_failed", error=str(e))
            return False
