"""Tests for deduplication logic."""

from src.processing.dedup import normalize_url, compute_simhash, hamming_distance, is_near_duplicate


def test_normalize_url_strips_tracking():
    url = "https://example.com/article?id=1&utm_source=twitter&utm_medium=social"
    assert normalize_url(url) == "https://example.com/article?id=%5B%271%27%5D"


def test_normalize_url_strips_fragment():
    url = "https://example.com/page#section"
    assert "section" not in normalize_url(url)


def test_normalize_url_lowercases_host():
    url = "https://EXAMPLE.COM/Path"
    normalized = normalize_url(url)
    assert "example.com" in normalized


def test_simhash_similar_texts():
    text1 = "The quick brown fox jumps over the lazy dog"
    text2 = "The quick brown fox leaps over the lazy dog"
    h1 = compute_simhash(text1)
    h2 = compute_simhash(text2)
    assert hamming_distance(h1, h2) < 10  # similar texts should have low distance


def test_simhash_different_texts():
    text1 = "Machine learning is transforming the world"
    text2 = "The weather today is sunny and warm"
    h1 = compute_simhash(text1)
    h2 = compute_simhash(text2)
    assert hamming_distance(h1, h2) > 5  # different texts should have high distance


def test_is_near_duplicate():
    h1 = compute_simhash("Agentic AI is the future of automation and productivity")
    h2 = compute_simhash("Agentic AI is the future of automation and efficiency")
    h3 = compute_simhash("Cooking pasta requires boiling water and salt")
    assert is_near_duplicate(h2, [h1], threshold=5)
    assert not is_near_duplicate(h3, [h1], threshold=5)
