"""Turning fetched content into entries.

Every adapter produces the same shape (a RawEntry), so the rest of the
pipeline never needs to know where an entry came from.
"""
import hashlib
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from email.utils import parsedate_to_datetime

from bs4 import BeautifulSoup


@dataclass
class RawEntry:
    uid: str                      # stable id within the source, for de-duplication
    title: str
    url: str | None = None
    published_at: datetime | None = None
    body: str = ""
    meta: dict = field(default_factory=dict)


def make_uid(*parts: str) -> str:
    return hashlib.sha1("|".join(p or "" for p in parts).encode()).hexdigest()[:20]


def html_to_text(html: str) -> str:
    if not html:
        return ""
    return BeautifulSoup(html, "html.parser").get_text(" ", strip=True)


def clip(text: str, n: int = 1500) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    return text if len(text) <= n else text[: n - 1] + "…"


def matches_include(title: str, patterns: list[str] | None) -> bool:
    if not patterns:
        return True
    return any(re.search(p, title, re.I) for p in patterns)


# ---------------------------------------------------------------- feeds ----

def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    value = value.strip()
    try:
        dt = parsedate_to_datetime(value)  # RSS style: "Mon, 23 Nov 2026 00:00:00 GMT"
    except (TypeError, ValueError):
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))  # Atom style
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _child(el, name: str):
    for c in el:
        if _local(c.tag) == name:
            return c
    return None


def _child_text(el, *names: str) -> str:
    for name in names:
        c = _child(el, name)
        if c is not None and (c.text or "").strip():
            return c.text.strip()
    return ""


def parse_feed(xml_text: str) -> list[RawEntry]:
    """Parse RSS 2.0 or Atom into entries."""
    root = ET.fromstring(xml_text.encode("utf-8"))
    entries: list[RawEntry] = []
    root_name = _local(root.tag)

    if root_name == "rss":
        channel = _child(root, "channel")
        items = [c for c in (channel if channel is not None else []) if _local(c.tag) == "item"]
        for it in items:
            title = _child_text(it, "title")
            link = _child_text(it, "link")
            guid = _child_text(it, "guid")
            body = html_to_text(_child_text(it, "encoded", "description"))
            entries.append(RawEntry(
                uid=make_uid(guid or link or title),
                title=title or clip(body, 120),
                url=link or None,
                published_at=_parse_date(_child_text(it, "pubDate", "date")),
                body=clip(body),
            ))
    elif root_name == "feed":
        for it in (c for c in root if _local(c.tag) == "entry"):
            title = html_to_text(_child_text(it, "title"))
            link = None
            for c in it:
                if _local(c.tag) == "link" and c.get("rel", "alternate") == "alternate":
                    link = c.get("href")
                    break
            ident = _child_text(it, "id")
            body = html_to_text(_child_text(it, "content", "summary"))
            entries.append(RawEntry(
                uid=make_uid(ident or link or title),
                title=title or clip(body, 120),
                url=link,
                published_at=_parse_date(_child_text(it, "published", "updated")),
                body=clip(body),
            ))
    else:
        raise ValueError(f"Not an RSS or Atom feed (root element <{root_name}>)")
    return entries


# --------------------------------------------------- Render changelog.md ----

_RENDER_ENTRY = re.compile(
    r"^### (?P<title>[^\n]+)\n\s*"
    r"- Date: (?P<date>\d{4}-\d{2}-\d{2})[ \t]*\n"
    r"(?:- Change type: (?P<type>[^\n]*)\n)?"
    r"(?:- URL: (?P<url>\S+)[ \t]*\n)?"
    r"(?P<body>.*?)(?=^#{2,3} |\Z)",
    re.M | re.S,
)


def parse_render_changelog(md: str) -> list[RawEntry]:
    out = []
    for m in _RENDER_ENTRY.finditer(md.replace("\r\n", "\n")):
        d = date.fromisoformat(m["date"])
        title = m["title"].strip()
        out.append(RawEntry(
            uid=make_uid(m["url"] or title),
            title=title,
            url=m["url"],
            published_at=datetime(d.year, d.month, d.day, tzinfo=timezone.utc),
            body=clip(m["body"]),
            meta={"change_type": (m["type"] or "").strip()},
        ))
    return out


# ------------------------------------------------------------ web pages ----

_DROP_TAGS = ["script", "style", "noscript", "svg", "nav", "header", "footer", "aside", "form", "button"]


def page_lines(html: str) -> list[str]:
    """Readable lines of a page, top to bottom, without menus and scripts."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(_DROP_TAGS):
        tag.decompose()
    main = soup.find("main") or soup.find("article") or soup.body or soup
    lines = []
    seen = set()
    for raw in main.get_text("\n").split("\n"):
        line = re.sub(r"\s+", " ", raw).strip()
        if len(line) < 3 or line in seen:
            continue
        seen.add(line)
        lines.append(line)
    return lines


def new_lines(previous: list[str], current: list[str]) -> list[str]:
    """Lines present now that weren't there before, in page order.

    Comparing as a set (rather than a positional diff) means entries that
    merely moved down the page don't count as new.
    """
    prev = set(previous)
    return [ln for ln in current if ln not in prev]


def resolve_page_date(value: str | None, now: datetime) -> datetime | None:
    """Dates from the model come back as YYYY-MM-DD, YYYY-MM, or null.

    A month-only date in the current month is treated as 'just now' (we
    noticed it this week); an older month-only date goes mid-month so it
    lands in roughly the right week of the trend history.
    """
    if not value:
        return None
    value = value.strip()
    try:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            d = date.fromisoformat(value)
            return datetime(d.year, d.month, d.day, tzinfo=timezone.utc)
        if re.fullmatch(r"\d{4}-\d{2}", value):
            y, m = map(int, value.split("-"))
            if (y, m) == (now.year, now.month):
                return now
            return datetime(y, m, 15, tzinfo=timezone.utc)
    except ValueError:
        return None
    return None
