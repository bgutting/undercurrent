"""A tiny job queue on Render Key Value (Redis-compatible).

Jobs are JSON blobs pushed onto a list. The worker pops them one at a time.
A short-lived "pending" marker stops the same job piling up if, say, the
hourly cron runs while the worker is down.
"""
import json

import redis

from . import config

QUEUE = "undercurrent:jobs"
_r = None


def r():
    global _r
    if _r is None:
        _r = redis.Redis.from_url(config.REDIS_URL, decode_responses=True)
    return _r


def _pending_key(job: dict) -> str:
    return "undercurrent:pending:" + job["type"] + ":" + str(job.get("source", ""))


def enqueue(job: dict, dedupe: bool = True) -> bool:
    """Queue a job. Returns False if an identical job is already waiting."""
    job = {"attempts": 0, **job}
    if dedupe and not r().set(_pending_key(job), "1", nx=True, ex=3 * 3600):
        return False
    r().lpush(QUEUE, json.dumps(job))
    return True


def requeue(job: dict):
    r().lpush(QUEUE, json.dumps(job))


def pop(timeout: int = 30) -> dict | None:
    item = r().brpop(QUEUE, timeout=timeout)
    return json.loads(item[1]) if item else None


def done(job: dict):
    r().delete(_pending_key(job))


def depth() -> int:
    return r().llen(QUEUE)
