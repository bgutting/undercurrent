"""The three stages: ingest -> annotate -> report."""
import json
import logging
import re
from datetime import datetime, timedelta, timezone

from . import adapters, citations, config, db, llm, trends
from .fetch import FEED_ACCEPT, fetch
from .sources import BY_KEY, SOURCES
from .themes import THEMES

log = logging.getLogger("undercurrent")


class PageLooksEmpty(Exception):
    pass


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------- ingest ----

def _ingest_page(src: dict, html: str, now: datetime) -> tuple[list, str | None]:
    lines = adapters.page_lines(html)
    if sum(len(x) for x in lines) < 1500:
        raise PageLooksEmpty(
            "The page came back almost empty. It probably builds its content with "
            "JavaScript, which a plain fetch can't run."
        )
    state = db.get_state(src["key"])
    previous = json.loads(state["snapshot"]) if state and state.get("snapshot") else None
    snapshot = json.dumps(lines)
    first_run = previous is None

    if first_run:
        text = "\n".join(lines)[:25000]          # newest entries are at the top
    else:
        added = adapters.new_lines(previous, lines)
        if sum(len(x) for x in added) < 25:      # nothing meaningful changed
            return [], snapshot
        text = "\n".join(added)[:30000]

    items = llm.extract_entries(src["name"], text, first_run, now.date().isoformat())
    out = []
    for it in items:
        when = adapters.resolve_page_date(it.get("date"), now, first_run)
        if when is None:
            if first_run:
                continue    # undated items on the first pass are probably old; skip
            when = now      # undated and newly appeared: we noticed it now
        title = str(it["title"]).strip()
        out.append(adapters.RawEntry(
            uid=adapters.make_uid(title.lower(), it.get("date") or ""),
            title=title,
            url=src["url"],
            published_at=when,
            body=adapters.clip(str(it.get("body") or "")),
        ))
    return out, snapshot


def ingest(key: str) -> int:
    """Fetch one source and store any new entries. Returns how many were new."""
    src = BY_KEY[key]
    now = now_utc()
    snapshot = None
    try:
        text = fetch(src["url"], accept=FEED_ACCEPT) if src["kind"] == "feed" else fetch(src["url"])
        if src["kind"] == "feed":
            raw = adapters.parse_feed(text)
        elif src["kind"] == "render":
            raw = adapters.parse_render_changelog(text)
        else:
            raw, snapshot = _ingest_page(src, text, now)
        if src["kind"] != "page" and not raw:
            raise ValueError("Fetched fine but found no entries; the format may have changed.")

        cutoff = now - timedelta(days=config.BACKFILL_DAYS)
        raw = [e for e in raw
               if adapters.matches_include(e.title, src.get("include"))
               and (e.published_at is None or e.published_at >= cutoff)]
        n = db.insert_entries(key, raw)
        db.record_check(key, ok=True, new=n, snapshot=snapshot)
        log.info("ingest %s: %d candidates, %d new", key, len(raw), n)
        return n
    except Exception as e:
        db.record_check(key, ok=False, error=f"{type(e).__name__}: {e}"[:500])
        raise


# -------------------------------------------------------------- annotate ----

def annotate_batch(size: int = 15) -> tuple[int, int]:
    """Annotate up to `size` entries. Returns (done, remaining)."""
    rows = db.unannotated(size)
    if not rows:
        return 0, 0
    for r in rows:
        r["source_name"] = BY_KEY.get(r["source"], {}).get("name", r["source"])
    result = llm.annotate(rows)
    for r in rows:
        db.save_annotation(r["id"], result.get(str(r["id"])))
    remaining = db.count_unannotated()
    log.info("annotated %d entries, %d remaining", len(rows), remaining)
    return len(rows), remaining


# ---------------------------------------------------------------- report ----

def _stats_text(rising, broad, hist_weeks) -> str:
    out = []
    if hist_weeks < 4:
        out.append(f"NOTE: only about {hist_weeks} week(s) of history exist, so 'rising' "
                   "comparisons are weak. Say so if you mention trends.")
    out.append("Rising themes (last 2 weeks vs. the 6 before; breadth = distinct companies):")
    out += [f"- {r['theme']}: {r['recent']} entries vs. baseline {r['baseline']} "
            f"(x{r['ratio']}), breadth {r['breadth']} ({', '.join(r['sources'])})" for r in rising] or ["- none"]
    out.append("Broad themes (3+ companies in the last 2 weeks):")
    out += [f"- {b['theme']}: {b['breadth']} companies ({', '.join(b['sources'])})" for b in broad] or ["- none"]
    return "\n".join(out)


def _threads_section(md: str) -> str:
    m = re.search(r"(?ms)^## Cross-source threads\s*\n(.*?)(?=^## |\Z)", md or "")
    return m.group(1).strip() if m else ""


def make_report() -> int | None:
    end = now_utc()
    start = end - timedelta(days=7)
    entries = db.entries_between(start, end)

    rows = db.theme_rows(end - timedelta(weeks=config.TREND_WEEKS))
    table = trends.weekly_table(rows, end, config.TREND_WEEKS)
    rising = trends.rising_themes(table)
    broad = trends.broad_themes(table)
    hist = trends.history_weeks(rows, end)

    for e in entries:
        s = BY_KEY.get(e["source"], {})
        e["source_name"] = s.get("name", e["source"])
        e["layer"] = s.get("layer", "")
        e["source_url"] = s.get("url")

    by_source = {s["key"]: 0 for s in SOURCES}
    for e in entries:
        by_source[e["source"]] = by_source.get(e["source"], 0) + 1
    quiet = [BY_KEY[k]["name"] for k, n in by_source.items() if n == 0 and k in BY_KEY]

    # Most important first; cap what we send so the prompt stays a sane size.
    picked = sorted(entries, key=lambda e: (-(e.get("importance") or 1), -e["when"].timestamp()))[:150]
    period = f"{start:%b %d} – {end:%b %d, %Y}"

    previous = db.latest_report()
    if picked:
        md = llm.write_report(picked, _stats_text(rising, broad, hist),
                              _threads_section(previous["markdown"]) if previous else "", period)
        md, dropped = citations.enforce_threads(md, {e["id"]: e["source"] for e in picked})
    else:
        md = ("## The week in one paragraph\n\nNo new entries from any source this week.\n\n"
              f"{citations.THREADS_HEADING}\n\n{citations.NOTHING}\n")
        dropped = 0

    cited = {int(i) for i in citations.CITE.findall(md)}
    stats = {
        "period": period,
        "entry_count": len(entries),
        "by_source": {BY_KEY[k]["name"]: n for k, n in by_source.items() if k in BY_KEY},
        "quiet": quiet,
        "rising": rising,
        "broad": broad,
        "history_weeks": hist,
        "dropped_threads": dropped,
        "citations": {str(e["id"]): {"source_name": e["source_name"], "url": e.get("url"),
                                     "source_url": e["source_url"]}
                      for e in picked if e["id"] in cited},
    }
    rid = db.insert_report(start, end, md, stats, config.REPORT_MODEL)
    log.info("report %d written (%d entries, %d threads dropped)", rid, len(entries), dropped)
    return rid


def theme_names() -> list[str]:
    return list(THEMES)
