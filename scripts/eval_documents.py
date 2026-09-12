#!/usr/bin/env python3
"""Document-level eval: long contract in, JSON pairs out, Jaccard match to gold."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from auditor.align import document_prf, load_jsonl, micro_average
from auditor.infer import PairAuditor, load_auditor


def eval_auditor(
    docs: list[dict],
    auditor: PairAuditor,
    threshold: float,
    top_k: int,
    max_pairs: int,
    jaccard: float,
) -> dict:
    per = []
    for doc in docs:
        result = auditor.analyze(
            doc["text"],
            threshold=threshold,
            top_k=top_k,
            max_pairs=max_pairs,
        )
        stats = document_prf(result["findings"], doc.get("gold") or [], threshold=jaccard)
        stats["contract_id"] = doc.get("contract_id")
        stats["n_clauses"] = len(result["clauses"])
        stats["n_candidates"] = result["n_candidates"]
        per.append(stats)
    summary = micro_average(per)
    summary["backend"] = auditor.backend
    summary["threshold"] = threshold
    summary["jaccard"] = jaccard
    return {"summary": summary, "per_doc": per}


def eval_nvidia(docs: list[dict], model: str, jaccard: float, max_chars: int) -> dict:
    from auditor.llm_nvidia import predict_pairs as nvidia_predict
    per = []
    for doc in docs:
        text = doc["text"][:max_chars]
        findings = nvidia_predict(text, model=model)
        stats = document_prf(findings, doc.get("gold") or [], threshold=jaccard)
        stats["contract_id"] = doc.get("contract_id")
        stats["n_pred"] = len(findings)
        per.append(stats)
    summary = micro_average(per)
    summary["backend"] = model
    summary["jaccard"] = jaccard
    return {"summary": summary, "per_doc": per}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--docs", type=Path, default=Path("artifacts/llm_testset_long.jsonl"))
    parser.add_argument("--out", type=Path, default=Path("artifacts/doc_benchmark.json"))
    parser.add_argument("--threshold", type=float, default=0.55)
    parser.add_argument("--top-k", type=int, default=40)
    parser.add_argument("--max-pairs", type=int, default=200)
    parser.add_argument("--jaccard", type=float, default=0.5)
    parser.add_argument("--nvidia-model", type=str, default="")
    args = parser.parse_args()
    docs = load_jsonl(args.docs)
    auditor = load_auditor()
    payload = {"auditor": eval_auditor(docs, auditor, args.threshold, args.top_k, args.max_pairs, args.jaccard)}
    if args.nvidia_model:
        payload["nvidia"] = eval_nvidia(docs, args.nvidia_model, args.jaccard, 120000)
    args.out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({k: v["summary"] for k, v in payload.items()}, indent=2))


if __name__ == "__main__":
    main()
