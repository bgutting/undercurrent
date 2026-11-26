"""The background worker: pops jobs off the queue and runs them, forever.

Job types:
  {"type": "ingest", "source": "*"}        fan out to every source
  {"type": "ingest", "source": "render"}   check one source
  {"type": "annotate"}                     tag a batch of new entries
  {"type": "report"}                       write the weekly report
"""
import logging
import time

from . import db, jobs, pipeline
from .sources import SOURCES

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("undercurrent")

MAX_ATTEMPTS = 3


def run(job: dict):
    t = job["type"]
    if t == "ingest" and job.get("source") == "*":
        jobs.done(job)
        for s in SOURCES:
            jobs.enqueue({"type": "ingest", "source": s["key"]})
    elif t == "ingest":
        new = pipeline.ingest(job["source"])
        jobs.done(job)
        if new:
            jobs.enqueue({"type": "annotate"})
    elif t == "annotate":
        _, remaining = pipeline.annotate_batch()
        jobs.done(job)
        if remaining:
            jobs.enqueue({"type": "annotate"})
    elif t == "report":
        pipeline.make_report()
        jobs.done(job)
    else:
        log.warning("unknown job %r", job)
        jobs.done(job)


def main():
    db.init_schema()
    log.info("worker started")
    if not db.source_counts():
        log.info("empty database: starting the first collection (backfill)")
        jobs.enqueue({"type": "ingest", "source": "*"})

    first_report_queued = False
    while True:
        job = jobs.pop(timeout=30)
        if job is None:
            continue
        log.info("job %s", job)
        try:
            run(job)
            # Once the first collection is fully done and tagged, write a first
            # report straight away instead of waiting for Monday. Only once per
            # worker start, so a failing report can't loop forever.
            if (not first_report_queued and jobs.depth() == 0
                    and db.count_reports() == 0 and db.source_counts()
                    and db.count_unannotated() == 0):
                first_report_queued = True
                jobs.enqueue({"type": "report"})
        except Exception:
            log.exception("job failed: %s", job)
            job["attempts"] = job.get("attempts", 0) + 1
            if job["attempts"] < MAX_ATTEMPTS:
                time.sleep(10 * job["attempts"])
                jobs.requeue(job)
            else:
                log.error("giving up on %s after %d attempts", job, MAX_ATTEMPTS)
                jobs.done(job)


if __name__ == "__main__":
    main()
