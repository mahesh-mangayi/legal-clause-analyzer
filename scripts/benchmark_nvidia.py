#!/usr/bin/env python3
"""Benchmark NVIDIA Build LLMs (API first) then the local DCA Auditor pipeline with tqdm progress bars."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from tqdm import tqdm

from auditor.align import document_prf, load_jsonl, micro_average
from auditor.infer import load_auditor
from auditor.llm_nvidia import predict_pairs as nvidia_predict


def load_env_file(env_path: Path = Path(".env")) -> None:
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        key = key.strip()
        val = val.strip().strip("'\"")
        if key and not os.environ.get(key):
            os.environ[key] = val


def main() -> None:
    load_env_file()

    parser = argparse.ArgumentParser(description="Benchmark NVIDIA LLMs (DeepSeek / Nemotron) on legal contracts.")
    parser.add_argument("--model", type=str, default="deepseek-ai/deepseek-v4-pro-0813", help="NVIDIA Build model name")
    parser.add_argument("--api-key", type=str, default="", help="NVIDIA API key (or set NVIDIA_API_KEY env var / .env)")
    parser.add_argument("--docs", type=Path, default=Path("artifacts/llm_testset_long.jsonl"), help="Contract testset")
    parser.add_argument("--out", type=Path, default=Path("artifacts/doc_benchmark.json"), help="Output benchmark file")
    parser.add_argument("--jaccard", type=float, default=0.5, help="Span matching threshold")
    parser.add_argument("--max-chars", type=int, default=120000, help="Contract character limit per LLM prompt")
    args = parser.parse_args()

    if args.api_key:
        os.environ["NVIDIA_API_KEY"] = args.api_key

    key = os.environ.get("NVIDIA_API_KEY") or os.environ.get("NGC_API_KEY")
    if not key:
        raise RuntimeError(
            "Missing NVIDIA API Key!\n"
            "Please provide your API key via any of the following methods:\n"
            "  1. In PowerShell: $env:NVIDIA_API_KEY=\"nvapi-...\"\n"
            "  2. In a .env file at repo root: NVIDIA_API_KEY=nvapi-...\n"
            "  3. Command argument: python scripts/benchmark_nvidia.py --api-key \"nvapi-...\""
        )

    if not args.docs.exists():
        raise RuntimeError(f"Test set file {args.docs} not found. Run scripts/make_llm_testset.py first.")

    docs = load_jsonl(args.docs)
    print(f"Loaded {len(docs)} test contracts from {args.docs}")

    payload = {}
    if args.out.exists():
        try:
            payload = json.loads(args.out.read_text(encoding="utf-8"))
        except Exception:
            payload = {}

    # STEP 1: NVIDIA API Evaluation First
    print(f"\n[1/2] Running NVIDIA API Evaluation ({args.model})...")
    nvidia_per = []
    pbar_api = tqdm(docs, desc="NVIDIA API Eval", unit="doc")
    for doc in pbar_api:
        cid = str(doc.get("contract_id", "doc"))
        pbar_api.set_postfix_str(cid[:30])
        text = doc["text"][: args.max_chars]
        try:
            findings = nvidia_predict(text, model=args.model)
        except Exception as e:
            tqdm.write(f"  Error querying NVIDIA API for {cid[:30]}: {e}")
            if "401" in str(e) or "Unauthorized" in str(e):
                raise RuntimeError(
                    "\n[HTTP 401 Unauthorized] Invalid or Expired NVIDIA API Key!\n"
                    "Please get a valid API key from https://build.nvidia.com and set it via:\n"
                    "  1. In a .env file at repo root: NVIDIA_API_KEY=nvapi-your-key\n"
                    "  2. In PowerShell: $env:NVIDIA_API_KEY=\"nvapi-your-key\"\n"
                    "  3. Flag: python scripts/benchmark_nvidia.py --api-key \"nvapi-your-key\""
                ) from e
            findings = []
        stats = document_prf(findings, doc.get("gold") or [], threshold=args.jaccard)
        stats["contract_id"] = cid
        stats["n_pred"] = len(findings)
        nvidia_per.append(stats)

    nvidia_summary = micro_average(nvidia_per)
    nvidia_summary["backend"] = args.model
    nvidia_summary["jaccard"] = args.jaccard
    payload["nvidia"] = {"summary": nvidia_summary, "per_doc": nvidia_per}

    # STEP 2: Local DCA Model Evaluation
    auditor = load_auditor()
    print(f"\n[2/2] Running Local DCA Auditor Model Evaluation ({auditor.backend})...")
    auditor_per = []
    pbar_dca = tqdm(docs, desc="DCA Model Eval", unit="doc")
    for doc in pbar_dca:
        cid = str(doc.get("contract_id", "doc"))
        pbar_dca.set_postfix_str(cid[:30])
        res = auditor.analyze(doc["text"], threshold=0.55, top_k=40, max_pairs=200)
        stats = document_prf(res["findings"], doc.get("gold") or [], threshold=args.jaccard)
        stats["contract_id"] = cid
        stats["n_clauses"] = len(res["clauses"])
        stats["n_candidates"] = res["n_candidates"]
        auditor_per.append(stats)

    auditor_summary = micro_average(auditor_per)
    auditor_summary["backend"] = auditor.backend
    auditor_summary["jaccard"] = args.jaccard
    payload["auditor"] = {"summary": auditor_summary, "per_doc": auditor_per}

    # Save Results
    args.out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\nSaved benchmark results to {args.out}")

    # Summary Table
    print("\n" + "=" * 65)
    print("BENCHMARK SUMMARY COMPARISON")
    print("=" * 65)
    print(f"{'Model / Pipeline':<35} | {'Precision':<10} | {'Recall':<10} | {'F1 Score':<10}")
    print("-" * 70)
    for k, v in [("NVIDIA " + args.model, nvidia_summary), ("DCA Auditor (" + auditor.backend + ")", auditor_summary)]:
        p = f"{v.get('precision', 0):.4f}"
        r = f"{v.get('recall', 0):.4f}"
        f1 = f"{v.get('f1', 0):.4f}"
        print(f"{k:<35} | {p:<10} | {r:<10} | {f1:<10}")
    print("=" * 65)


if __name__ == "__main__":
    main()
