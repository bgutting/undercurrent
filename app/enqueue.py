"""What the cron jobs run. They don't do the work; they just queue it.

  python -m app.enqueue ingest    # check every source
  python -m app.enqueue report    # write the weekly report
"""
import sys

from . import jobs


def main():
    what = sys.argv[1] if len(sys.argv) > 1 else ""
    if what == "ingest":
        job = {"type": "ingest", "source": "*"}
    elif what == "report":
        job = {"type": "report"}
    else:
        sys.exit("usage: python -m app.enqueue ingest|report")
    queued = jobs.enqueue(job)
    print(("queued " if queued else "already queued, skipped ") + str(job))


if __name__ == "__main__":
    main()
