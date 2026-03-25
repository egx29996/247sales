"""URL normalization and content deduplication."""

from __future__ import annotations

import hashlib
import re
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode

# Tracking parameters to strip from URLs
TRACKING_PARAMS = {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "ref", "source", "fbclid", "gclid"}


def normalize_url(url: str) -> str:
    """Normalize a URL by stripping tracking params and fragments."""
    try:
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        cleaned = {k: v for k, v in params.items() if k.lower() not in TRACKING_PARAMS}
        clean_query = urlencode(cleaned, doseq=True)
        return urlunparse((
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            parsed.path.rstrip("/"),
            parsed.params,
            clean_query,
            "",  # strip fragment
        ))
    except Exception:
        return url


def compute_simhash(text: str, hash_bits: int = 64) -> int:
    """Compute a SimHash fingerprint for text content."""
    tokens = _tokenize(text)
    if not tokens:
        return 0

    v = [0] * hash_bits
    for token in tokens:
        token_hash = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16) & ((1 << hash_bits) - 1)
        for i in range(hash_bits):
            if token_hash & (1 << i):
                v[i] += 1
            else:
                v[i] -= 1

    fingerprint = 0
    for i in range(hash_bits):
        if v[i] > 0:
            fingerprint |= 1 << i
    return fingerprint


def hamming_distance(hash1: int, hash2: int) -> int:
    """Compute the Hamming distance between two hashes."""
    return bin(hash1 ^ hash2).count("1")


def is_near_duplicate(new_hash: int, existing_hashes: list[int], threshold: int = 3) -> bool:
    """Check if content is a near-duplicate of any existing content."""
    for h in existing_hashes:
        if hamming_distance(new_hash, h) <= threshold:
            return True
    return False


def _tokenize(text: str) -> list[str]:
    """Simple whitespace + lowercase tokenizer."""
    text = re.sub(r"[^\w\s]", "", text.lower())
    return [w for w in text.split() if len(w) > 2]
