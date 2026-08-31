#!/usr/bin/env python3
"""Build pairs.jsonl from a local Better Call CLAUSE clone."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from auditor.ingest import ingest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--bcc-root",
        type=Path,
        default=Path("data/clause-legal"),
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("artifacts/pairs.jsonl"),
    )
    args = parser.parse_args()
    if not args.bcc_root.exists():
        raise SystemExit(
            f"BCC clone not found at {args.bcc_root}. "
            "git clone --depth 1 https://github.com/clause-legal/clause-legal.github.io.git data/clause-legal"
        )
    stats = ingest(args.bcc_root, args.out)
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
