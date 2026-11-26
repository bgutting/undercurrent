"""The website: reports, sources, entries, themes."""
import base64
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from . import config, db, jobs, trends
from .rendering import ago, render_markdown
from .sources import BY_KEY, SOURCES
from .themes import THEMES

HERE = Path(__file__).parent
app = FastAPI(title="Undercurrent")
app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")
templates = Jinja2Templates(directory=HERE / "templates")


@app.on_event("startup")
def startup():
    db.init_schema()


# ------------------------------------------------------------ password ----

@app.middleware("http")
async def password_gate(request: Request, call_next):
    if not config.SITE_PASSWORD or request.url.path == "/healthz":
        return await call_next(request)
    header = request.headers.get("authorization", "")
    if header.startswith("Basic "):
        try:
            _, _, pw = base64.b64decode(header[6:]).decode().partition(":")
            if secrets.compare_digest(pw, config.SITE_PASSWORD):
                return await call_next(request)
        except Exception:
            pass
    return Response("Password required", status_code=401,
                    headers={"WWW-Authenticate": 'Basic realm="Undercurrent"'})


# ------------------------------------------------------------- helpers ----

templates.env.filters["ago"] = ago
templates.env.globals["THEMES"] = THEMES


def page(request: Request, name: str, **ctx):
    ctx.setdefault("msg", request.query_params.get("msg"))
    ctx["nav"] = name.split(".")[0]
    return templates.TemplateResponse(request, name, ctx)


def back(path: str, msg: str):
    return RedirectResponse(f"{path}?msg={quote(msg)}", status_code=303)


# -------------------------------------------------------------- pages -----

@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.get("/")
def home(request: Request):
    report = db.latest_report()
    if report:
        return show_report(request, report)
    counts = db.source_counts()
    return page(request, "empty.html", total=sum(c["total"] for c in counts.values()),
                unannotated=db.count_unannotated(), queue=_safe_depth())


@app.get("/reports")
def reports(request: Request):
    return page(request, "reports.html", reports=db.list_reports())


@app.get("/reports/{report_id}")
def report(request: Request, report_id: int):
    r = db.get_report(report_id)
    if not r:
        raise HTTPException(404)
    return show_report(request, r)


def show_report(request: Request, r: dict):
    stats = r["stats"] or {}
    active = sum(1 for n in (stats.get("by_source") or {}).values() if n)
    return page(request, "report.html", report=r, stats=stats, active=active,
                body=render_markdown(r["markdown"], stats.get("citations")))


@app.get("/sources")
def sources(request: Request):
    states, counts = db.all_states(), db.source_counts()
    rows = []
    for s in SOURCES:
        st = states.get(s["key"]) or {}
        rows.append({**s, "state": st, "counts": counts.get(s["key"]) or {"week": 0, "quarter": 0, "total": 0}})
    return page(request, "sources.html", rows=rows, queue=_safe_depth())


@app.get("/entries")
def entries(request: Request, source: str | None = None, theme: str | None = None):
    rows = db.recent_entries(source or None, theme or None)
    for r in rows:
        r["source_name"] = BY_KEY.get(r["source"], {}).get("name", r["source"])
    return page(request, "entries.html", rows=rows, source=source, theme=theme, sources=SOURCES)


@app.get("/themes")
def themes(request: Request):
    end = datetime.now(timezone.utc)
    rows = db.theme_rows(end - timedelta(weeks=config.TREND_WEEKS))
    table = trends.weekly_table(rows, end, config.TREND_WEEKS)
    weeks = [(end - timedelta(days=7 * (i + 1))) for i in range(config.TREND_WEEKS)]
    peak = max([max(d["counts"]) for d in table.values()] + [1])
    ordered = sorted(
        ({"theme": t, "counts": d["counts"], "breadth": len(d["sources"][0] | d["sources"][1])}
         for t, d in table.items()),
        key=lambda r: (-sum(r["counts"][:2]), -sum(r["counts"])),
    )
    return page(request, "themes.html", table=ordered, weeks=weeks, peak=peak,
                rising=trends.rising_themes(table), history=trends.history_weeks(rows, end))


# ------------------------------------------------------------ actions -----

@app.post("/actions/check-all")
def check_all():
    jobs.enqueue({"type": "ingest", "source": "*"})
    return back("/sources", "Queued a check of every source.")


@app.post("/actions/check/{key}")
def check_one(key: str):
    if key not in BY_KEY:
        raise HTTPException(404)
    jobs.enqueue({"type": "ingest", "source": key})
    return back("/sources", f"Queued a check of {BY_KEY[key]['name']}.")


@app.post("/actions/report")
def make_report():
    queued = jobs.enqueue({"type": "report"})
    msg = ("Queued. The report usually takes a minute or two; refresh this page."
           if queued else "A report is already being written.")
    return back("/reports", msg)


def _safe_depth():
    try:
        return jobs.depth()
    except Exception:
        return None
