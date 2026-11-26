"""Small display helpers shared by the website (kept free of web-framework imports)."""
import html
from datetime import datetime, timezone

import markdown as md_lib

from . import citations


def render_markdown(text: str, cites: dict | None) -> str:
    text = citations.link_citations(text or "", {int(k): v for k, v in (cites or {}).items()})
    # Block any raw HTML the model might emit, but keep '>' for blockquotes.
    text = html.escape(text, quote=False).replace("&gt;", ">")
    return md_lib.markdown(text, extensions=["tables", "sane_lists"])


def ago(dt: datetime | None) -> str:
    if not dt:
        return "never"
    s = (datetime.now(timezone.utc) - dt).total_seconds()
    if s < 90:
        return "just now"
    if s < 5400:
        return f"{int(s // 60)} min ago"
    if s < 129600:
        return f"{int(s // 3600)} h ago"
    return f"{int(s // 86400)} days ago"
