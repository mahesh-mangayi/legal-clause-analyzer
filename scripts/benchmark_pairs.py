#!/usr/bin/env python3
"""Pair-level benchmark comparing Base Legal-BERT vs. Our Fine-Tuned Legal-BERT (DCA) using Colab evaluation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch
from tqdm import tqdm
from transformers import AutoModelForSequenceClassification, AutoTokenizer

try:
    from sklearn.metrics import f1_score as sklearn_f1, precision_recall_fscore_support
except ImportError:
    sklearn_f1 = None
    precision_recall_fscore_support = None


def compute_metrics_fallback(labels: list[int], preds: list[int]) -> tuple[float, float, float]:
    tp = sum(1 for l, p in zip(labels, preds) if l == 1 and p == 1)
    fp = sum(1 for l, p in zip(labels, preds) if l == 0 and p == 1)
    fn = sum(1 for l, p in zip(labels, preds) if l == 1 and p == 0)

    p = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    r = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * p * r / (p + r) if (p + r) > 0 else 0.0
    return p, r, f1


def load_test_pairs(dataset_path: Path) -> list[dict]:
    if str(dataset_path).endswith(".gz"):
        import gzip

        with gzip.open(dataset_path, "rt", encoding="utf-8") as handle:
            rows = [json.loads(line) for line in handle if line.strip()]
    else:
        rows = [json.loads(line) for line in dataset_path.read_text(encoding="utf-8").splitlines() if line.strip()]

    test_rows = [r for r in rows if r.get("split") == "test"]
    return test_rows


def evaluate_pair_model(
    model_path_or_name: str,
    test_rows: list[dict],
    batch_size: int = 32,
    max_len: int = 256,
    device: str = "cpu",
) -> dict:
    print(f"\nLoading model: {model_path_or_name}...")
    tok = AutoTokenizer.from_pretrained(model_path_or_name)
    model = AutoModelForSequenceClassification.from_pretrained(model_path_or_name, num_labels=2)
    model.to(device)
    model.eval()

    all_preds = []
    all_labels = []

    pbar = tqdm(range(0, len(test_rows), batch_size), desc=f"Evaluating {Path(model_path_or_name).name}")
    for i in pbar:
        chunk = test_rows[i : i + batch_size]
        texts_a = [r["text_a"][:1200] for r in chunk]
        texts_b = [r["text_b"][:1200] for r in chunk]
        labels = [int(r["label"]) for r in chunk]

        enc = tok(
            texts_a,
            texts_b,
            truncation=True,
            max_length=max_len,
            padding=True,
            return_tensors="pt",
        )
        enc = {k: v.to(device) for k, v in enc.items()}

        with torch.no_grad():
            logits = model(**enc).logits
            preds = torch.argmax(logits, dim=-1).cpu().tolist()

        all_preds.extend(preds)
        all_labels.extend(labels)

    if precision_recall_fscore_support is not None:
        p, r, f1, _ = precision_recall_fscore_support(all_labels, all_preds, average="binary", zero_division=0)
    else:
        p, r, f1 = compute_metrics_fallback(all_labels, all_preds)

    # Gap bin F1 breakdown for gold positives
    by_bin: dict[str, dict] = {}
    for i, row in enumerate(test_rows):
        if int(row["label"]) != 1:
            continue
        bin_name = row.get("gap_bin", "unknown")
        by_bin.setdefault(bin_name, {"yt": [], "yp": []})
        by_bin[bin_name]["yt"].append(1)
        by_bin[bin_name]["yp"].append(all_preds[i])

    gap_f1 = {}
    for k, v in by_bin.items():
        if sklearn_f1 is not None:
            gap_f1[k] = float(sklearn_f1(v["yt"], v["yp"], zero_division=0))
        else:
            _, _, f1_val = compute_metrics_fallback(v["yt"], v["yp"])
            gap_f1[k] = f1_val

    return {
        "model": model_path_or_name,
        "n_test": len(test_rows),
        "precision": float(p),
        "recall": float(r),
        "f1": float(f1),
        "f1_by_gap": gap_f1,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Pair-level benchmark comparing Base Legal-BERT vs Fine-Tuned Legal-BERT.")
    parser.add_argument("--dataset", type=Path, default=None, help="Dataset file (pairs_colab_full.jsonl.gz / pairs_colab.jsonl.gz / pairs.jsonl)")
    parser.add_argument("--finetuned-path", type=Path, default=Path("artifacts/legalbert-dca"), help="Path to fine-tuned Legal-BERT model")
    parser.add_argument("--base-model", type=str, default="nlpaueb/legal-bert-base-uncased", help="Base Legal-BERT HuggingFace model name")
    parser.add_argument("--batch-size", type=int, default=32, help="Evaluation batch size")
    args = parser.parse_args()

    candidates = [
        args.dataset,
        Path("artifacts/pairs_colab_full.jsonl.gz"),
        Path("artifacts/pairs_colab.jsonl.gz"),
        Path("artifacts/pairs.jsonl"),
    ]
    dataset_path = next((p for p in candidates if p is not None and p.exists()), None)
    if dataset_path is None:
        raise SystemExit("Missing dataset file. Run scripts/make_colab_subset.py first.")

    test_rows = load_test_pairs(dataset_path)
    print(f"Loaded {len(test_rows)} test pairs from {dataset_path}")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")

    # 1. Base Legal-BERT
    base_metrics = evaluate_pair_model(args.base_model, test_rows, batch_size=args.batch_size, device=device)

    # 2. Our Fine-Tuned Legal-BERT
    if not args.finetuned_path.exists():
        raise SystemExit(f"Fine-tuned model directory {args.finetuned_path} not found.")

    ft_metrics = evaluate_pair_model(str(args.finetuned_path), test_rows, batch_size=args.batch_size, device=device)

    print("\n" + "=" * 70)
    print("PAIR-LEVEL BENCHMARK COMPARISON (SAME COLAB EVALUATION PROCESS)")
    print("=" * 70)
    print(f"{'Model':<35} | {'Precision':<10} | {'Recall':<10} | {'Pair F1':<10}")
    print("-" * 70)
    for m in [base_metrics, ft_metrics]:
        name = "Base Legal-BERT (nlpaueb)" if m["model"] == args.base_model else "Our Fine-Tuned Legal-BERT (DCA)"
        print(f"{name:<35} | {m['precision']:.4f}     | {m['recall']:.4f}   | {m['f1']:.4f}")
    print("=" * 70)

    print("\n--- Breakdown: F1 Score by Clause Section Gap ---")
    print(f"{'Model':<35} | {'Same Section':<12} | {'Nearby':<10} | {'Far':<10}")
    print("-" * 70)
    for m in [base_metrics, ft_metrics]:
        name = "Base Legal-BERT (nlpaueb)" if m["model"] == args.base_model else "Our Fine-Tuned Legal-BERT (DCA)"
        g = m["f1_by_gap"]
        same = f"{g.get('same_section', 0):.4f}"
        near = f"{g.get('nearby', 0):.4f}"
        far = f"{g.get('far', 0):.4f}"
        print(f"{name:<35} | {same:<12} | {near:<10} | {far:<10}")
    print("=" * 70)


if __name__ == "__main__":
    main()
