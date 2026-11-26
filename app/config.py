"""Settings, read from environment variables (set on Render, or in your shell locally)."""
import os

DATABASE_URL = os.environ.get("DATABASE_URL", "")
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# A cheap, fast model for per-entry work; a stronger one for the weekly report.
FAST_MODEL = os.environ.get("FAST_MODEL", "claude-haiku-5-5")
REPORT_MODEL = os.environ.get("REPORT_MODEL", "claude-sonnet-5-5")

# If set, the whole site asks for this password (any username works).
SITE_PASSWORD = os.environ.get("SITE_PASSWORD", "")

# How far back to collect on the first run, so trends have history on day one.
BACKFILL_DAYS = int(os.environ.get("BACKFILL_DAYS", "90"))

# How many weeks of history the trend view and report look at.
TREND_WEEKS = 8

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0 Safari/537.36 Undercurrent/1.0"
)
