"""Fetching web pages. Uses only the standard library."""
import urllib.request

from . import config


class FetchError(Exception):
    pass


def fetch(url: str, timeout: int = 30) -> str:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": config.USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml,text/markdown,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            charset = resp.headers.get_content_charset() or "utf-8"
    except Exception as e:  # network errors, 4xx/5xx, timeouts
        raise FetchError(f"{type(e).__name__}: {e}") from e
    return raw.decode(charset, errors="replace")
