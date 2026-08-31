#!/usr/bin/env python3
"""Write a Drive-friendly subset for Colab T4 (~50-80MB uncompressed)."""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pairs", type=Path, default=Path("artifacts/pairs.jsonl"))
    parser.add_argument("--out", type=Path, default=Path("artifacts/pairs_colab.jsonl"))
    parser.add_argument("--train-cap", type=int, default=24000)
    parser.add_argument("--dev-cap", type=int, default=3000)
    parser.add_argument("--test-cap", type=int, default=4000)
    args = parser.parse_args()
    rng = random.Random(13)
    buckets = {"train": [], "dev": [], "test": []}
    with args.pairs.open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            buckets.setdefault(row["split"], []).append(row)
    caps = {"train": args.train_cap, "dev": args.dev_cap, "test": args.test_cap}
    out_rows = []
    for split, rows in buckets.items():
        rng.shuffle(rows)
        # keep all positives first then fill negatives
        pos = [r for r in rows if r["label"] == 1]
        neg = [r for r in rows if r["label"] == 0]
        cap = caps.get(split, len(rows))
        keep_pos = pos[: cap // 2]
        keep_neg = neg[: cap - len(keep_pos)]
        chosen = keep_pos + keep_neg
        rng.shuffle(chosen)
        out_rows.extend(chosen)
        print(split, "kept", len(chosen), "of", len(rows))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as handle:
        for row in out_rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    print("wrote", args.out, "bytes", args.out.stat().st_size)


if __name__ == "__main__":
    main()
