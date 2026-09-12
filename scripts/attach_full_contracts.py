#!/usr/bin/env python3
"""Attach CUAD full_contract_txt to the frozen LLM test slice (same contract_ids)."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", s.lower())[:80]


def _index_full_txt(txt_dir: Path) -> dict[str, Path]:
    return {_norm(p.stem): p for p in txt_dir.glob("*.txt")}


def _match(contract_id: str, index: dict[str, Path]) -> Path | None:
    key = _norm(contract_id)
    if key in index:
        return index[key]
    for k, path in index.items():
        if key[:50] in k or k[:50] in key:
            return path
    return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--slice", type=Path, default=Path("artifacts/llm_testset.jsonl"))
    parser.add_argument(
        "--txt-dir",
        type=Path,
        default=Path("data/clause-legal/datasets/CUAD_Dataset/full_contract_txt"),
    )
    parser.add_argument("--out-full", type=Path, default=Path("artifacts/llm_testset_full.jsonl"))
    parser.add_argument("--out-long", type=Path, default=Path("artifacts/llm_testset_long.jsonl"))
    parser.add_argument("--long-chars", type=int, default=60_000, help="~20 pages at 3k chars/page")
    parser.add_argument("--max-chars", type=int, default=120_000, help="NVIDIA prompt cap")
    args = parser.parse_args()
    if not args.slice.exists():
        raise SystemExit(f"missing frozen slice {args.slice}")
    if not args.txt_dir.exists():
        raise SystemExit(f"missing {args.txt_dir}; clone BCC with git -c core.longpaths=true")

    index = _index_full_txt(args.txt_dir)
    full_rows = []
    long_rows = []
    n_cuad = n_hit = 0
    with args.slice.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("corpus") != "cuad":
                continue
            n_cuad += 1
            path = _match(row["contract_id"], index)
            if path is None:
                continue
            n_hit += 1
            raw = path.read_text(encoding="utf-8", errors="replace")
            text = raw if len(raw) <= args.max_chars else raw[: args.max_chars - 1] + "…"
            attached = dict(row)
            attached["text"] = text
            attached["text_chars"] = len(text)
            attached["source_txt"] = str(path)
            attached["full_chars"] = len(raw)
            attached["truncated_for_prompt"] = len(raw) > args.max_chars
            full_rows.append(attached)
            if len(raw) >= args.long_chars:
                long_rows.append(attached)

    args.out_full.parent.mkdir(parents=True, exist_ok=True)
    with args.out_full.open("w", encoding="utf-8") as handle:
        for row in full_rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    with args.out_long.open("w", encoding="utf-8") as handle:
        for row in long_rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    stats = {
        "n_cuad_in_slice": n_cuad,
        "n_attached_full": n_hit,
        "n_long_ge_20_pages": len(long_rows),
        "long_chars_threshold": args.long_chars,
        "max_prompt_chars": args.max_chars,
        "out_full": str(args.out_full),
        "out_long": str(args.out_long),
        "note": "Same frozen contract_ids. Full CUAD text for NVIDIA; do not add unlabeled EDGAR.",
    }
    Path("artifacts/llm_testset_full_stats.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
