#!/usr/bin/env python3
"""Write a Drive-friendly dataset package for Colab T4."""

from __future__ import annotations

import argparse
import gzip
import json
import random
import shutil
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pairs", type=Path, default=Path("artifacts/pairs.jsonl"))
    parser.add_argument("--out", type=Path, default=Path("artifacts/pairs_colab_full.jsonl"))
    parser.add_argument("--full", action="store_true", help="Include all 143k pairs without capping")
    parser.add_argument("--train-cap", type=int, default=120000)
    parser.add_argument("--dev-cap", type=int, default=16000)
    parser.add_argument("--test-cap", type=int, default=16000)
    args = parser.parse_args()

    if not args.pairs.exists():
        raise SystemExit(f"Input file {args.pairs} not found. Run ingest_bcc.py first.")

    rng = random.Random(13)
    buckets = {"train": [], "dev": [], "test": []}
    with args.pairs.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            buckets.setdefault(row["split"], []).append(row)

    out_rows = []
    if args.full:
        for split, rows in buckets.items():
            rng.shuffle(rows)
            out_rows.extend(rows)
            print(f"{split}: kept all {len(rows)} rows")
    else:
        caps = {"train": args.train_cap, "dev": args.dev_cap, "test": args.test_cap}
        for split, rows in buckets.items():
            rng.shuffle(rows)
            pos = [r for r in rows if r.get("label") == 1]
            neg = [r for r in rows if r.get("label") == 0]
            cap = caps.get(split, len(rows))
            keep_pos = pos[: cap // 2]
            keep_neg = neg[: cap - len(keep_pos)]
            chosen = keep_pos + keep_neg
            rng.shuffle(chosen)
            out_rows.extend(chosen)
            print(f"{split}: kept {len(chosen)} of {len(rows)} (pos: {len(keep_pos)}, neg: {len(keep_neg)})")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as handle:
        for row in out_rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    print("Wrote uncompressed:", args.out, "bytes:", args.out.stat().st_size)

    gz_path = args.out.with_suffix(".jsonl.gz")
    with args.out.open("rb") as f_in, gzip.open(gz_path, "wb") as f_out:
        shutil.copyfileobj(f_in, f_out)

    print("Wrote gzipped package:", gz_path, "bytes:", gz_path.stat().st_size)


if __name__ == "__main__":
    main()
