"""Postgres access. Plain SQL, no ORM, so it's easy to read."""
from contextlib import contextmanager
from datetime import datetime

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS entries (
    id            BIGSERIAL PRIMARY KEY,
    source        TEXT NOT NULL,
    uid           TEXT NOT NULL,
    title         TEXT NOT NULL,
    url           TEXT,
    published_at  TIMESTAMPTZ,
    body          TEXT NOT NULL DEFAULT '',
    meta          JSONB NOT NULL DEFAULT '{}',
    headline      TEXT,
    summary       TEXT,
    themes        TEXT[] NOT NULL DEFAULT '{}',
    importance    SMALLINT,
    kind          TEXT,
    annotated_at  TIMESTAMPTZ,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (source, uid)
);
CREATE INDEX IF NOT EXISTS entries_when ON entries ((COALESCE(published_at, created_at)));
CREATE INDEX IF NOT EXISTS entries_unannotated ON entries (id) WHERE annotated_at IS NULL;

CREATE TABLE IF NOT EXISTS source_state (
    source        TEXT PRIMARY KEY,
    last_checked  TIMESTAMPTZ,
    last_ok       TIMESTAMPTZ,
    last_error    TEXT,
    last_new      INTEGER NOT NULL DEFAULT 0,
    snapshot      TEXT
);

CREATE TABLE IF NOT EXISTS reports (
    id            BIGSERIAL PRIMARY KEY,
    period_start  TIMESTAMPTZ NOT NULL,
    period_end    TIMESTAMPTZ NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    markdown      TEXT NOT NULL,
    stats         JSONB NOT NULL DEFAULT '{}',
    model         TEXT
);
"""

WHEN = "COALESCE(published_at, created_at)"


@contextmanager
def conn():
    if not config.DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not set")
    c = psycopg.connect(config.DATABASE_URL, row_factory=dict_row, autocommit=True)
    try:
        yield c
    finally:
        c.close()


def init_schema():
    with conn() as c:
        c.execute(SCHEMA)


# ---------------------------------------------------------- source state ----

def get_state(source: str) -> dict | None:
    with conn() as c:
        return c.execute("SELECT * FROM source_state WHERE source=%s", (source,)).fetchone()


def all_states() -> dict[str, dict]:
    with conn() as c:
        return {r["source"]: r for r in c.execute("SELECT * FROM source_state").fetchall()}


def record_check(source: str, ok: bool, error: str | None = None, new: int = 0,
                 snapshot: str | None = None):
    with conn() as c:
        c.execute(
            """
            INSERT INTO source_state (source, last_checked, last_ok, last_error, last_new, snapshot)
            VALUES (%(s)s, now(), CASE WHEN %(ok)s THEN now() END, %(err)s, %(new)s, %(snap)s)
            ON CONFLICT (source) DO UPDATE SET
                last_checked = now(),
                last_ok      = CASE WHEN %(ok)s THEN now() ELSE source_state.last_ok END,
                last_error   = %(err)s,
                last_new     = %(new)s,
                snapshot     = COALESCE(%(snap)s, source_state.snapshot)
            """,
            {"s": source, "ok": ok, "err": error, "new": new, "snap": snapshot},
        )


def reset_source(source: str):
    """Forget everything about a source so it gets collected from scratch."""
    with conn() as c:
        c.execute("DELETE FROM entries WHERE source=%s", (source,))
        c.execute("DELETE FROM source_state WHERE source=%s", (source,))


# --------------------------------------------------------------- entries ----

def insert_entries(source: str, entries) -> int:
    """Insert RawEntry objects; already-known ones are skipped. Returns count inserted."""
    inserted = 0
    with conn() as c:
        for e in entries:
            cur = c.execute(
                """
                INSERT INTO entries (source, uid, title, url, published_at, body, meta)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (source, uid) DO NOTHING
                """,
                (source, e.uid, e.title[:500], e.url, e.published_at, e.body, Jsonb(e.meta)),
            )
            inserted += cur.rowcount
    return inserted


def count_entries(source: str) -> int:
    with conn() as c:
        return c.execute("SELECT count(*) AS n FROM entries WHERE source=%s", (source,)).fetchone()["n"]


def unannotated(limit: int) -> list[dict]:
    with conn() as c:
        return c.execute(
            "SELECT * FROM entries WHERE annotated_at IS NULL ORDER BY id LIMIT %s", (limit,)
        ).fetchall()


def count_unannotated() -> int:
    with conn() as c:
        return c.execute("SELECT count(*) AS n FROM entries WHERE annotated_at IS NULL").fetchone()["n"]


def save_annotation(entry_id: int, a: dict | None):
    """Save an annotation. a=None marks the entry done without one (so it isn't retried forever)."""
    a = a or {"headline": None, "summary": None, "themes": [], "importance": 1, "kind": "other"}
    with conn() as c:
        c.execute(
            """UPDATE entries SET headline=%s, summary=%s, themes=%s, importance=%s, kind=%s,
                   annotated_at=now() WHERE id=%s""",
            (a["headline"], a["summary"], a["themes"], a["importance"], a["kind"], entry_id),
        )


def entries_between(start: datetime, end: datetime) -> list[dict]:
    with conn() as c:
        return c.execute(
            f"""SELECT *, {WHEN} AS "when" FROM entries
                WHERE {WHEN} >= %s AND {WHEN} < %s AND annotated_at IS NOT NULL
                ORDER BY {WHEN} DESC""",
            (start, end),
        ).fetchall()


def theme_rows(since: datetime) -> list[tuple]:
    """(theme, source, when) for every theme tag since a date."""
    with conn() as c:
        rows = c.execute(
            f"""SELECT unnest(themes) AS theme, source, {WHEN} AS "when"
                FROM entries WHERE {WHEN} >= %s""",
            (since,),
        ).fetchall()
    return [(r["theme"], r["source"], r["when"]) for r in rows]


def recent_entries(source: str | None, theme: str | None, limit: int = 200) -> list[dict]:
    where, args = ["TRUE"], []
    if source:
        where.append("source = %s")
        args.append(source)
    if theme:
        where.append("%s = ANY(themes)")
        args.append(theme)
    args.append(limit)
    with conn() as c:
        return c.execute(
            f"""SELECT *, {WHEN} AS "when" FROM entries WHERE {' AND '.join(where)}
                ORDER BY {WHEN} DESC LIMIT %s""",
            args,
        ).fetchall()


def source_counts() -> dict[str, dict]:
    with conn() as c:
        rows = c.execute(
            f"""SELECT source,
                       count(*) FILTER (WHERE {WHEN} >= now() - interval '7 days')  AS week,
                       count(*) FILTER (WHERE {WHEN} >= now() - interval '90 days') AS quarter,
                       count(*) AS total
                FROM entries GROUP BY source"""
        ).fetchall()
    return {r["source"]: r for r in rows}


# --------------------------------------------------------------- reports ----

def insert_report(start, end, markdown: str, stats: dict, model: str) -> int:
    with conn() as c:
        return c.execute(
            """INSERT INTO reports (period_start, period_end, markdown, stats, model)
               VALUES (%s, %s, %s, %s, %s) RETURNING id""",
            (start, end, markdown, Jsonb(stats), model),
        ).fetchone()["id"]


def latest_report() -> dict | None:
    with conn() as c:
        return c.execute("SELECT * FROM reports ORDER BY created_at DESC LIMIT 1").fetchone()


def get_report(report_id: int) -> dict | None:
    with conn() as c:
        return c.execute("SELECT * FROM reports WHERE id=%s", (report_id,)).fetchone()


def list_reports() -> list[dict]:
    with conn() as c:
        return c.execute(
            "SELECT id, period_start, period_end, created_at FROM reports ORDER BY created_at DESC"
        ).fetchall()


def count_reports() -> int:
    with conn() as c:
        return c.execute("SELECT count(*) AS n FROM reports").fetchone()["n"]
