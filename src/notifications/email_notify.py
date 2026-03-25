"""Email notification via SMTP."""

from __future__ import annotations

import smtplib
import structlog
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

log = structlog.get_logger()


class EmailNotifier:
    def __init__(self, host: str, port: int, user: str, password: str, from_addr: str, to_addrs: list[str]) -> None:
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.from_addr = from_addr
        self.to_addrs = to_addrs

    def send(self, subject: str, body_html: str, body_text: str) -> bool:
        """Send an email digest."""
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.from_addr
            msg["To"] = ", ".join(self.to_addrs)

            msg.attach(MIMEText(body_text, "plain"))
            msg.attach(MIMEText(body_html, "html"))

            with smtplib.SMTP(self.host, self.port) as server:
                server.starttls()
                server.login(self.user, self.password)
                server.sendmail(self.from_addr, self.to_addrs, msg.as_string())

            log.info("email_sent", to=self.to_addrs, subject=subject)
            return True
        except Exception as e:
            log.error("email_send_failed", error=str(e))
            return False
