#!/usr/bin/env python3
"""Freeze a document-level LLM eval slice from held-out test contracts only."""

from __future__ import annotations

import argparse
import json
import random
from collections import defaultdict
from pathlib import Path

def _load_positive_test_rows(pairs_path: Path) -> list[dict]:
    rows = []
    with pairs_path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("split") != "test" or int(row.get("label", 0)) != 1:
                continue
            rows.append(row)
    return rows


def _document_from_rows(contract_id: str, rows: list[dict], text_limit: int) -> dict:
    chunks: list[str] = []
    seen: set[str] = set()
    gold = []
    kinds = []
    corpora = []
    gap_bins = []
    for row in rows:
        corpora.append(row.get("corpus") or "unknown")
        kinds.append(row.get("kind") or "in_text")
        gap_bins.append(row.get("gap_bin") or "unknown")
        loc_a = str(row.get("location_a") or "Clause A")
        loc_b = str(row.get("location_b") or "Clause B")
        for loc, text in ((loc_a, row["text_a"]), (loc_b, row["text_b"])):
            key = f"{loc}\n{text}"
            if key in seen:
                continue
            seen.add(key)
            chunks.append(key)
        gold.append(
            {
                "span_a": row["text_a"],
                "span_b": row["text_b"],
                "type": row.get("type") or "Inconsistency",
                "kind": row.get("kind") or "in_text",
                "gap_bin": row.get("gap_bin") or "unknown",
                "location_a": row.get("location_a"),
                "location_b": row.get("location_b"),
            }
        )
    corpus = max(set(corpora), key=corpora.count)
    kind = max(set(kinds), key=kinds.count)
    for preferred in ("nearby", "far", "same_section", "unknown"):
        if preferred in gap_bins:
            gap_bin = preferred
            break
    else:
        gap_bin = "unknown"
    text = "\n\n".join(chunks)
    return {
        "contract_id": contract_id,
        "split": "test",
        "corpus": corpus,
        "kind": kind,
        "gap_bin": gap_bin,
        "n_gold": len(gold),
        "gold": gold,
        "text": text if len(text) <= text_limit else text[: text_limit - 1] + "…",
        "text_chars": min(len(text), text_limit),
        "stratum": f"{corpus}|{kind}|{gap_bin}",
    }


def _stratified_sample(docs: list[dict], n: int, rng: random.Random) -> list[dict]:
    if len(docs) <= n:
        return docs
    by_stratum: dict[str, list[dict]] = defaultdict(list)
    for doc in docs:
        by_stratum[doc["stratum"]].append(doc)
    for bucket in by_stratum.values():
        rng.shuffle(bucket)
    chosen: list[dict] = []
    keys = sorted(by_stratum)
    while len(chosen) < n and any(by_stratum[k] for k in keys):
        for key in keys:
            if len(chosen) >= n:
                break
            if by_stratum[key]:
                chosen.append(by_stratum[key].pop())
    return chosen


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pairs", type=Path, default=None)
    parser.add_argument("--out", type=Path, default=Path("artifacts/llm_testset.jsonl"))
    parser.add_argument("--n-docs", type=int, default=150)
    parser.add_argument("--text-limit", type=int, default=24000)
    parser.add_argument("--seed", type=int, default=13)
    args = parser.parse_args()
    candidates = [
        args.pairs,
        Path("artifacts/pairs.jsonl"),
        Path("artifacts/pairs_colab.jsonl"),
    ]
    pairs_path = next((p for p in candidates if p is not None and p.exists()), None)
    if pairs_path is None:
        raise SystemExit(
            "Need artifacts/pairs.jsonl or artifacts/pairs_colab.jsonl. "
            "Run ingest_bcc.py then make_colab_subset.py."
        )

    rng = random.Random(args.seed)
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in _load_positive_test_rows(pairs_path):
        grouped[row["contract_id"]].append(row)

    docs = [
        _document_from_rows(cid, rows, args.text_limit)
        for cid, rows in grouped.items()
        if rows
    ]
    sampled = _stratified_sample(docs, args.n_docs, rng)
    sampled.sort(key=lambda d: d["contract_id"])

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as handle:
        for doc in sampled:
            handle.write(json.dumps(doc, ensure_ascii=False) + "\n")

    stats = {
        "source_pairs": str(pairs_path),
        "seed": args.seed,
        "n_test_contracts_available": len(docs),
        "n_docs": len(sampled),
        "n_gold_pairs": sum(d["n_gold"] for d in sampled),
        "by_corpus": {},
        "by_kind": {},
        "by_gap_bin": {},
        "note": (
            "Test contract_ids only. Document text is reconstructed from gold spans "
            "(full BCC files if pairs.jsonl came from ingest). Do not resample after LLM runs."
        ),
    }
    for key in ("corpus", "kind", "gap_bin"):
        counts: dict[str, int] = defaultdict(int)
        for doc in sampled:
            counts[str(doc[key])] += 1
        stats[f"by_{key}"] = dict(sorted(counts.items()))
    stats_path = args.out.with_name("llm_testset_stats.json")
    stats_path.write_text(json.dumps(stats, indent=2), encoding="utf-8")
    print(json.dumps(stats, indent=2))
    print("wrote", args.out, "bytes", args.out.stat().st_size)


if __name__ == "__main__":
    main()
