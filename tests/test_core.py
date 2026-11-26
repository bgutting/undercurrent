"""Tests for the parts that don't need a database, queue, or API key.

Run with:  python -m pytest -q
"""
import json
import sys
import types
from datetime import datetime, timedelta, timezone

from app import adapters, citations, trends
from app.rendering import render_markdown

NOW = datetime(2026, 11, 26, 14, 0, tzinfo=timezone.utc)

RSS = """<?xml version="1.0"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom"><channel>
<title>Claude Platform release notes</title><link>https://x</link><description>d</description>
<atom:link rel="self" href="https://x/feed.xml"/>
<item><title>Claude Platform release notes — November 23, 2026</title>
<link>https://x/overview#web-search-counts</link><guid isPermaLink="true">https://x/overview#web-search-counts</guid>
<pubDate>Mon, 23 Nov 2026 00:00:00 GMT</pubDate>
<description>&lt;ul&gt;&lt;li&gt;The Analytics API now reports &lt;strong&gt;web search counts&lt;/strong&gt;.&lt;/li&gt;&lt;/ul&gt;</description></item>
<item><title>Claude Platform release notes — November 23, 2026</title>
<link>https://x/overview#connector-counts</link><guid isPermaLink="true">https://x/overview#connector-counts</guid>
<pubDate>Mon, 23 Nov 2026 00:00:00 GMT</pubDate><description>Connector sign-in counts.</description></item>
</channel></rss>"""

ATOM = """<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"><title>Vercel News</title>
<entry><title>Workflow is 10x faster, again</title><id>https://vercel.com/blog/workflow-10x</id>
<link href="https://vercel.com/blog/workflow-10x"/><updated>2026-11-25T17:00:00.000Z</updated>
<summary type="html">&lt;p&gt;Faster steps.&lt;/p&gt;</summary></entry>
</feed>"""

RENDER_MD = """# Render Changelog

Last generated: 2026-11-26

## Tooling releases

### Render CLI

- Version: v2.30.0
- Date: 2026-11-20
- URL: https://github.com/render-oss/cli/releases

## Core changelog feed

### Use custom base images with Render Sandboxes

- Date: 2026-11-25
- Change type: Improved
- URL: https://render.com/changelog/use-custom-base-images-with-render-sandboxes

You can now bring your own base image.

### Fine-grained API keys now generally available

- Date: 2026-11-18
- Change type: New
- URL: https://render.com/changelog/fine-grained-api-keys-now-generally-available

Scope keys to services.
"""


def test_rss():
    es = adapters.parse_feed(RSS)
    assert len(es) == 2
    assert es[0].uid != es[1].uid                     # same titles, different guids
    assert "web search counts" in es[0].body         # escaped HTML was unescaped and stripped
    assert "<" not in es[0].body
    assert es[0].published_at == datetime(2026, 11, 23, tzinfo=timezone.utc)


def test_atom():
    es = adapters.parse_feed(ATOM)
    assert es[0].title == "Workflow is 10x faster, again"
    assert es[0].url == "https://vercel.com/blog/workflow-10x"
    assert es[0].published_at.year == 2026 and es[0].body == "Faster steps."


def test_render_markdown_changelog():
    es = adapters.parse_render_changelog(RENDER_MD)
    assert [e.title for e in es] == ["Use custom base images with Render Sandboxes",
                                     "Fine-grained API keys now generally available"]
    assert es[0].body == "You can now bring your own base image."
    assert es[1].meta["change_type"] == "New"


def test_include_filter():
    pats = [r"Bedrock", r"AgentCore"]
    assert adapters.matches_include("Amazon Bedrock adds X", pats)
    assert not adapters.matches_include("Amazon EC2 M8g in Tel Aviv", pats)
    assert adapters.matches_include("anything", None)


def test_page_lines_and_diff():
    html = """<html><body><nav>Home Docs Pricing</nav><main>
      <h2>November 25, 2026</h2><p>Sandbox events UI.</p>
      <h2>November 12, 2026</h2><p>Cost attribution.</p>
      <script>var x=1</script></main><footer>© Modal</footer></body></html>"""
    lines = adapters.page_lines(html)
    assert "Home Docs Pricing" not in lines and "var x=1" not in lines
    assert lines[0] == "November 25, 2026"
    newer = ["November 30, 2026", "GPU snapshots."] + lines
    assert adapters.new_lines(lines, newer) == ["November 30, 2026", "GPU snapshots."]


def test_page_dates():
    assert adapters.resolve_page_date("2026-11-03", NOW).day == 3
    assert adapters.resolve_page_date("2026-11", NOW) == NOW            # current month, later check -> now
    assert adapters.resolve_page_date("2026-11", NOW, first_run=True).day == 15   # backfill -> mid-month
    assert adapters.resolve_page_date("2026-09", NOW).day == 15         # older month -> mid-month
    assert adapters.resolve_page_date(None, NOW) is None
    assert adapters.resolve_page_date("soon", NOW) is None


def _rows():
    rows = []
    # sandboxes: quiet for weeks, then 3 companies in the last two weeks
    for days, src in [(1, "render"), (3, "vercel"), (9, "modal"), (10, "render"), (50, "modal")]:
        rows.append(("sandboxes", src, NOW - timedelta(days=days)))
    # models: steady
    for w in range(8):
        rows.append(("models", "openai", NOW - timedelta(days=7 * w + 2)))
    return rows


def test_trends():
    table = trends.weekly_table(_rows(), NOW, 8)
    assert table["sandboxes"]["counts"][0] == 2 and table["sandboxes"]["counts"][1] == 2
    rising = trends.rising_themes(table)
    assert [r["theme"] for r in rising] == ["sandboxes"]
    assert rising[0]["breadth"] == 3
    assert trends.broad_themes(table)[0]["theme"] == "sandboxes"
    assert trends.history_weeks(_rows(), NOW) == 7


REPORT = """## The week in one paragraph

Busy week for sandboxes [E1].

## Cross-source threads

- **Sandboxes go mainstream.** Render and Vercel both shipped sandbox features [E1] [E2].
- **Only one company.** Render did a thing [E1] [E3].
- **No evidence.** Everyone loves agents.

## Source by source

### Render
- Custom base images [E1] [E99]
"""


def test_enforce_threads():
    md, dropped = citations.enforce_threads(REPORT, {1: "render", 2: "vercel", 3: "render"})
    assert dropped == 2
    assert "Sandboxes go mainstream" in md
    assert "Only one company" not in md and "No evidence" not in md
    assert "## Source by source" in md


def test_enforce_threads_all_dropped():
    md, dropped = citations.enforce_threads(
        "## Cross-source threads\n\n- **Vibes.** [E1]\n\n## Source by source\n\n- x [E1]\n", {1: "render"})
    assert dropped == 1 and citations.NOTHING in md


def test_render_report_html():
    md, _ = citations.enforce_threads(REPORT, {1: "render", 2: "vercel", 3: "render"})
    cites = {"1": {"source_name": "Render", "url": "https://render.com/c/1", "source_url": None},
             "2": {"source_name": "Vercel", "url": None, "source_url": "https://vercel.com/atom"}}
    out = render_markdown(md + "\n<script>alert(1)</script>", cites)
    assert '<a href="https://render.com/c/1">Render↗</a>' in out
    assert '<a href="https://vercel.com/atom">Vercel↗</a>' in out
    assert "[E99]" not in out and "<script>" not in out


# ------------------------------------------------ pipeline, with fakes ----

class FakeDB(types.ModuleType):
    def __init__(self):
        super().__init__("app.db")
        self.state, self.entries, self.reports = {}, [], []

    def get_state(self, s): return self.state.get(s)
    def record_check(self, s, ok, error=None, new=0, snapshot=None):
        st = self.state.setdefault(s, {})
        st.update(ok=ok, last_error=error, last_new=new)
        if snapshot is not None:
            st["snapshot"] = snapshot
    def insert_entries(self, s, es):
        known = {(e["source"], e["uid"]) for e in self.entries}
        n = 0
        for e in es:
            if (s, e.uid) not in known:
                self.entries.append({"id": len(self.entries) + 1, "source": s, "uid": e.uid, "title": e.title,
                                     "url": e.url, "published_at": e.published_at, "body": e.body})
                n += 1
        return n
    def entries_between(self, a, b):
        return [dict(e, when=e["published_at"], importance=2, themes=["sandboxes"], headline=e["title"])
                for e in self.entries if a <= e["published_at"] < b]
    def theme_rows(self, since): return [("sandboxes", e["source"], e["published_at"]) for e in self.entries]
    def latest_report(self): return None
    def insert_report(self, a, b, md, stats, model):
        self.reports.append((md, stats)); return len(self.reports)


def _pipeline_with_fakes(monkeypatch, page_html, extracted):
    fake = FakeDB()
    monkeypatch.setitem(sys.modules, "psycopg", types.ModuleType("psycopg"))
    monkeypatch.setitem(sys.modules, "app.db", fake)
    import app
    monkeypatch.setattr(app, "db", fake, raising=False)
    sys.modules.pop("app.pipeline", None)
    monkeypatch.delattr(app, "pipeline", raising=False)
    from app import pipeline
    monkeypatch.setattr(pipeline, "fetch", lambda url, accept=None: page_html)
    monkeypatch.setattr(pipeline, "now_utc", lambda: NOW)
    calls = []
    def fake_extract(name, text, first, today):
        calls.append((first, text)); return extracted.pop(0)
    monkeypatch.setattr(pipeline.llm, "extract_entries", fake_extract)
    return pipeline, fake, calls


def test_page_ingest_flow(monkeypatch):
    filler = "<p>" + ("Older release notes text. " * 80) + "</p>"
    page1 = f"<main><h2>November 20, 2026</h2><p>Sandbox events UI.</p>{filler}</main>"
    page2 = f"<main><h2>November 25, 2026</h2><p>GPU memory snapshots.</p><h2>November 20, 2026</h2><p>Sandbox events UI.</p>{filler}</main>"
    extracted = [
        [{"title": "Sandbox events UI", "date": "2026-11-20", "body": "x"},
         {"title": "Undated old thing", "date": None, "body": "y"}],
        [{"title": "GPU memory snapshots", "date": "2026-11-25", "body": "z"}],
    ]
    pipeline, fake, calls = _pipeline_with_fakes(monkeypatch, page1, extracted)
    assert pipeline.ingest("modal") == 1                  # undated item skipped on first run
    assert calls[0][0] is True
    monkeypatch.setattr(pipeline, "fetch", lambda url, accept=None: page2)
    assert pipeline.ingest("modal") == 1
    assert calls[1][0] is False and "GPU memory snapshots." in calls[1][1]
    assert "Sandbox events UI." not in calls[1][1]         # only new lines sent
    assert pipeline.ingest("modal") == 0                   # unchanged page: no model call
    assert len(calls) == 2


def test_page_empty_is_flagged(monkeypatch):
    pipeline, fake, _ = _pipeline_with_fakes(monkeypatch, "<main><div id=root></div></main>", [])
    try:
        pipeline.ingest("openai")
        raise AssertionError("should raise")
    except pipeline.PageLooksEmpty:
        pass
    assert "JavaScript" in fake.state["openai"]["last_error"]


def test_feed_ingest_with_filter(monkeypatch):
    aws = """<rss version="2.0"><channel>
    <item><title>Amazon Bedrock adds a model</title><link>https://a/1</link><pubDate>Tue, 24 Nov 2026 10:00:00 GMT</pubDate><description>d</description></item>
    <item><title>Amazon EC2 M8g in Tel Aviv</title><link>https://a/2</link><pubDate>Tue, 24 Nov 2026 10:00:00 GMT</pubDate><description>d</description></item>
    <item><title>AgentCore old news</title><link>https://a/3</link><pubDate>Mon, 01 Jun 2026 10:00:00 GMT</pubDate><description>d</description></item>
    </channel></rss>"""
    pipeline, fake, _ = _pipeline_with_fakes(monkeypatch, aws, [])
    assert pipeline.ingest("aws") == 1                     # filtered + older than backfill window
    assert fake.entries[0]["title"] == "Amazon Bedrock adds a model"


def test_report_flow(monkeypatch):
    pipeline, fake, _ = _pipeline_with_fakes(monkeypatch, RENDER_MD, [])
    pipeline.ingest("render")
    seen = {}
    def fake_write(entries, stats_text, last, period):
        seen["stats"] = stats_text
        ids = [e["id"] for e in entries]
        return (f"## The week in one paragraph\n\nx [E{ids[0]}]\n\n## Cross-source threads\n\n"
                f"- **Solo.** [E{ids[0]}] [E{ids[-1]}]\n\n## Source by source\n\n### Render\n- y [E{ids[0]}]\n")
    monkeypatch.setattr(pipeline.llm, "write_report", fake_write)
    pipeline.make_report()
    md, stats = fake.reports[0]
    assert citations.NOTHING in md and stats["dropped_threads"] == 1   # both cites are Render
    assert "only about" in seen["stats"]                               # thin history is flagged
    assert "Google Gemini" in stats["quiet"]
    json.dumps(stats)                                                  # must be storable as JSON


def test_parse_json_salvages_truncated_list():
    from app.llm import parse_json
    assert parse_json('```json\n[{"a": 1}, {"b": 2}]\n```') == [{"a": 1}, {"b": 2}]
    assert parse_json('[{"a": 1}, {"b": {"c": 2}}, {"d": "cut off mid-str') == [{"a": 1}, {"b": {"c": 2}}]
    assert parse_json('Here you go: {"12": {"headline": "x"}}') == {"12": {"headline": "x"}}
