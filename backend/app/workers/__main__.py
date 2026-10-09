"""Run with python -m backend.app.workers; SIGTERM stops claims after current work."""

import argparse
import logging
import math
import signal
import threading

from sqlalchemy.exc import SQLAlchemyError

from backend.app.config import setup_logging
from backend.app.db.session import SessionLocal
from backend.app.services.analytics_worker import run_once


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--poll-seconds", type=float, default=1)
    parser.add_argument("--lease-seconds", type=float, default=60)
    parser.add_argument("--max-attempts", type=int, default=3)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    if (
        not all(
            math.isfinite(v) and v > 0 for v in (args.poll_seconds, args.lease_seconds)
        )
        or args.max_attempts < 1
    ):
        parser.error("poll/lease must be positive; max-attempts must be >=1")
    setup_logging()
    stopped = threading.Event()
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda *_: stopped.set())
    while not stopped.is_set():
        try:
            worked = run_once(
                SessionLocal,
                lease_seconds=args.lease_seconds,
                max_attempts=args.max_attempts,
            )
        except SQLAlchemyError:
            logging.getLogger(__name__).error(
                "Worker database operation unavailable; will retry"
            )
            worked = False
        if args.once:
            return
        if not worked:
            stopped.wait(args.poll_seconds)


if __name__ == "__main__":
    main()
