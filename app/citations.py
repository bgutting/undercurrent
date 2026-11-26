"""Keeping the report honest.

The model cites entries as [E123]. This module:
  - turns citations into links,
  - drops citations to entries that don't exist,
  - removes any cross-source thread that doesn't cite at least two
    different companies (otherwise it isn't cross-source — it's a hunch).
"""
import re

CITE = re.compile(r"\[E(\d+)\]")
THREADS_HEADING = "## Cross-source threads"
NOTHING = "_Nothing connects across companies this week. That's allowed, and it's useful to know._"


def _split_sections(md: str) -> list[tuple[str, str]]:
    """[(heading_line_or_empty, body), ...] split on level-2 headings."""
    parts = re.split(r"(?m)^(## .*)$", md)
    out = [("", parts[0])]
    for i in range(1, len(parts), 2):
        out.append((parts[i].strip(), parts[i + 1] if i + 1 < len(parts) else ""))
    return out


def _blocks(body: str) -> list[str]:
    """Split a section into bullets / paragraphs."""
    blocks, cur = [], []
    for line in body.split("\n"):
        starts_bullet = re.match(r"^\s*([-*]|\d+\.)\s+", line) and not line.startswith("  ")
        if (not line.strip() or starts_bullet) and cur:
            blocks.append("\n".join(cur))
            cur = []
        if line.strip():
            cur.append(line)
    if cur:
        blocks.append("\n".join(cur))
    return blocks


def enforce_threads(md: str, entry_sources: dict[int, str]) -> tuple[str, int]:
    """Drop threads lacking citations from >= 2 companies. Returns (md, dropped)."""
    dropped = 0
    out = []
    for heading, body in _split_sections(md):
        if heading.lower().startswith(THREADS_HEADING.lower()):
            kept = []
            for block in _blocks(body):
                ids = [int(x) for x in CITE.findall(block)]
                companies = {entry_sources[i] for i in ids if i in entry_sources}
                if len(companies) >= 2:
                    kept.append(block)
                elif block.strip().startswith("_") and not ids:
                    continue  # a 'nothing this week' line from the model; we add our own
                else:
                    dropped += 1
            body = "\n\n" + ("\n\n".join(kept) if kept else NOTHING) + "\n\n"
        out.append((heading + "\n" if heading else "") + body)
    return "".join(out), dropped


def link_citations(md: str, entries: dict[int, dict]) -> str:
    """[E12] -> a small link labelled with the company name. Unknown ids vanish."""
    def repl(m):
        i = int(m.group(1))
        e = entries.get(i)
        if not e:
            return ""
        label = e["source_name"]
        url = e.get("url") or e.get("source_url") or "#"
        return f"[{label}↗]({url})"
    return CITE.sub(repl, md)
