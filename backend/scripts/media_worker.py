#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.database import SessionLocal  # noqa: E402
from app.services.media_pipeline import run_media_processing_batch  # noqa: E402


def _run_once(batch_size: int) -> dict:
    db = SessionLocal()
    try:
        return run_media_processing_batch(db, batch_size=batch_size)
    finally:
        db.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Background media processing worker")
    parser.add_argument("--once", action="store_true", help="Process one batch and exit")
    parser.add_argument(
        "--interval-seconds",
        type=float,
        default=3.0,
        help="Polling interval when running in loop mode",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=20,
        help="Maximum media items per batch run",
    )
    args = parser.parse_args()

    while True:
        stats = _run_once(args.batch_size)
        print(json.dumps(stats, ensure_ascii=False))
        if args.once:
            return 0
        time.sleep(max(0.1, args.interval_seconds))


if __name__ == "__main__":
    raise SystemExit(main())
