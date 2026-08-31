#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from auditor.train_baseline import train_baseline


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pairs", type=Path, default=Path("artifacts/pairs.jsonl"))
    parser.add_argument("--out", type=Path, default=Path("artifacts"))
    args = parser.parse_args()
    metrics = train_baseline(args.pairs, args.out)
    print(json.dumps({k: v for k, v in metrics.items() if k != "dev"}, indent=2))
    print("--- dev ---")
    print(metrics.get("dev", {}).get("report", ""))
    print("--- test ---")
    print(metrics.get("test", {}).get("report", ""))


if __name__ == "__main__":
    main()
