from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

GAP_ORDER = ("same_section", "nearby", "far", "unknown")


def _tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]+", (text or "").lower()) if len(t) > 1}


def jaccard(a: str, b: str) -> float:
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def pair_similarity(pred: dict, gold: dict, threshold: float = 0.5) -> float:
    """Best of (a-a,b-b) vs swapped alignment; 0 if either span misses threshold."""
    sa, sb = pred.get("span_a") or "", pred.get("span_b") or ""
    ga, gb = gold.get("span_a") or "", gold.get("span_b") or ""
    direct = min(jaccard(sa, ga), jaccard(sb, gb))
    swapped = min(jaccard(sa, gb), jaccard(sb, ga))
    score = max(direct, swapped)
    return score if score >= threshold else 0.0


def match_pairs(
    predicted: list[dict],
    gold: list[dict],
    threshold: float = 0.5,
) -> tuple[list[tuple[int, int]], set[int], set[int]]:
    """Greedy one-to-one matching. Returns matches, unmatched pred idx, unmatched gold idx."""
    scored: list[tuple[float, int, int]] = []
    for i, pred in enumerate(predicted):
        for j, g in enumerate(gold):
            sim = pair_similarity(pred, g, threshold=threshold)
            if sim > 0:
                scored.append((sim, i, j))
    scored.sort(reverse=True)
    used_p, used_g = set(), set()
    matches = []
    for _, i, j in scored:
        if i in used_p or j in used_g:
            continue
        used_p.add(i)
        used_g.add(j)
        matches.append((i, j))
    unmatched_p = set(range(len(predicted))) - used_p
    unmatched_g = set(range(len(gold))) - used_g
    return matches, unmatched_p, unmatched_g


def document_prf(predicted: list[dict], gold: list[dict], threshold: float = 0.5) -> dict:
    matches, unmatched_p, unmatched_g = match_pairs(predicted, gold, threshold)
    tp = len(matches)
    fp = len(unmatched_p)
    fn = len(unmatched_g)
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    by_gap: dict[str, dict] = {k: {"tp": 0, "fn": 0} for k in GAP_ORDER}
    gold_matched = {j for _, j in matches}
    for j, g in enumerate(gold):
        bin_name = g.get("gap_bin") or "unknown"
        if bin_name not in by_gap:
            by_gap[bin_name] = {"tp": 0, "fn": 0}
        if j in gold_matched:
            by_gap[bin_name]["tp"] += 1
        else:
            by_gap[bin_name]["fn"] += 1
    recall_by_gap = {}
    for name, counts in by_gap.items():
        denom = counts["tp"] + counts["fn"]
        recall_by_gap[name] = counts["tp"] / denom if denom else 0.0
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "n_pred": len(predicted),
        "n_gold": len(gold),
        "recall_by_gap": recall_by_gap,
        "gap_counts": by_gap,
    }


def micro_average(per_doc: list[dict]) -> dict:
    tp = sum(d["tp"] for d in per_doc)
    fp = sum(d["fp"] for d in per_doc)
    fn = sum(d["fn"] for d in per_doc)
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    gap_tp: dict[str, int] = defaultdict(int)
    gap_fn: dict[str, int] = defaultdict(int)
    for d in per_doc:
        for k, c in (d.get("gap_counts") or {}).items():
            gap_tp[k] += c.get("tp", 0)
            gap_fn[k] += c.get("fn", 0)
    recall_by_gap = {}
    for name in sorted(set(gap_tp) | set(gap_fn)):
        denom = gap_tp[name] + gap_fn[name]
        recall_by_gap[name] = gap_tp[name] / denom if denom else 0.0
    return {
        "n_docs": len(per_doc),
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "recall_by_gap": recall_by_gap,
    }


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows
