"""Content summarization - extractive (free) or LLM-based."""

from __future__ import annotations

import structlog

log = structlog.get_logger()


class ExtractiveSummarizer:
    """Extractive summarization using sumy (no API key needed)."""

    def __init__(self, sentence_count: int = 3) -> None:
        self.sentence_count = sentence_count
        self._initialized = False

    def _ensure_init(self) -> None:
        if not self._initialized:
            import nltk
            try:
                nltk.data.find("tokenizers/punkt_tab")
            except LookupError:
                nltk.download("punkt_tab", quiet=True)
            self._initialized = True

    def summarize(self, text: str) -> str:
        """Summarize a single piece of text."""
        if len(text.split()) < 30:
            return text  # too short to summarize

        self._ensure_init()
        try:
            from sumy.parsers.plaintext import PlaintextParser
            from sumy.nlp.tokenizers import Tokenizer
            from sumy.summarizers.lsa import LsaSummarizer

            parser = PlaintextParser.from_string(text, Tokenizer("english"))
            summarizer = LsaSummarizer()
            sentences = summarizer(parser.document, self.sentence_count)
            return " ".join(str(s) for s in sentences)
        except Exception as e:
            log.warning("extractive_summarize_failed", error=str(e))
            # Fallback: return first N words
            words = text.split()
            return " ".join(words[:100]) + ("..." if len(words) > 100 else "")

    def summarize_digest(self, items: list[dict]) -> str:
        """Create a digest summary from multiple items."""
        lines = []
        for i, item in enumerate(items, 1):
            title = item.get("title", "Untitled")
            source = item.get("source", "unknown")
            summary = item.get("summary") or self.summarize(item.get("text", ""))
            url = item.get("url", "")
            lines.append(f"{i}. [{source.upper()}] {title}\n   {summary}\n   {url}\n")
        return "\n".join(lines)


class LLMSummarizer:
    """Summarization using OpenAI-compatible API."""

    def __init__(self, api_key: str, base_url: str, model: str) -> None:
        self.api_key = api_key
        self.base_url = base_url
        self.model = model

    def summarize(self, text: str) -> str:
        if len(text.split()) < 30:
            return text
        try:
            import httpx
            resp = httpx.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": "Summarize the following content in 2-3 concise sentences. Focus on key insights and actionable takeaways."},
                        {"role": "user", "content": text[:4000]},
                    ],
                    "max_tokens": 200,
                },
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        except Exception as e:
            log.warning("llm_summarize_failed", error=str(e))
            words = text.split()
            return " ".join(words[:100]) + ("..." if len(words) > 100 else "")

    def summarize_digest(self, items: list[dict]) -> str:
        """Create an LLM-powered digest summary."""
        content_block = "\n\n".join(
            f"[{item.get('source', 'unknown').upper()}] {item.get('title', '')}: {item.get('text', '')[:500]}"
            for item in items[:20]
        )
        try:
            import httpx
            resp = httpx.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": "You are a daily digest curator. Summarize these articles into a concise, well-organized daily briefing with key trends and actionable insights. Group by theme. Use bullet points."},
                        {"role": "user", "content": content_block},
                    ],
                    "max_tokens": 1000,
                },
                timeout=60,
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        except Exception as e:
            log.warning("llm_digest_failed", error=str(e))
            # Fallback to basic listing
            return ExtractiveSummarizer().summarize_digest(items)


def get_summarizer(mode: str, api_key: str = "", base_url: str = "", model: str = ""):
    """Factory to create the right summarizer based on config."""
    if mode == "llm" and api_key:
        return LLMSummarizer(api_key=api_key, base_url=base_url, model=model)
    return ExtractiveSummarizer()
