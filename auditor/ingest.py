from __future__ import annotations

import hashlib
import json
import random
import re
from collections import defaultdict
from pathlib import Path

from auditor.schema import (
    contradiction_yes,
    gap_bin,
    is_legal,
    normalize_type,
    section_gap,
    truncate,
)

NEGATIVES_PER_POSITIVE = 3
HASH_MOD = 100


def _load_json(path: Path) -> list[dict]:
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except json.JSONDecodeError:
        return []
    if isinstance(data, dict):
        return [data]
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    return []


def _statute_text(pert: dict) -> str:
    for key in ("scraped_snippet_2", "scraped_snippet_1", "law_explanation", "law_citation"):
        value = pert.get(key)
        if isinstance(value, str) and value.strip():
            return truncate(value, 1800)
        if isinstance(value, list) and value:
            return truncate(str(value[0]), 1800)
    return ""


def _iter_records(bcc_root: Path):
    datasets = bcc_root / "datasets"
    for json_path in datasets.rglob("*.json"):
        if json_path.name == "simple_cleanup.py":
            continue
        rel = json_path.relative_to(datasets).as_posix()
        corpus = "nli" if rel.startswith("NLI") else "cuad"
        folder = json_path.parent.name.lower()
        kind_hint = "legal" if "legal" in folder else "in_text"
        for rec in _load_json(json_path):
            yield rec, corpus, kind_hint, json_path


def _split_for_contract(contract_id: str) -> str:
    digest = hashlib.md5(contract_id.encode("utf-8")).hexdigest()
    bucket = int(digest[:8], 16) % HASH_MOD
    if bucket < 80:
        return "train"
    if bucket < 90:
        return "dev"
    return "test"


def ingest(bcc_root: Path, out_path: Path, seed: int = 13) -> dict:
    rng = random.Random(seed)
    grouped: dict[str, list[dict]] = defaultdict(list)

    n_files = 0
    n_pos = 0
    skipped = 0

    for rec, corpus, kind_hint, _path in _iter_records(bcc_root):
        n_files += 1
        file_name = rec.get("file_name") or rec.get("filename") or _path.stem
        contract_id = re.sub(r"^perturbed_", "", str(file_name))
        perts = rec.get("perturbation") or rec.get("perturbations") or []
        if not isinstance(perts, list):
            continue
        for pert in perts:
            if not isinstance(pert, dict):
                continue
            if not contradiction_yes(pert.get("contradiction_exists")):
                skipped += 1
                continue
            raw_type = pert.get("type") or ""
            legal = is_legal(raw_type, pert) or kind_hint == "legal"
            text_a = truncate(pert.get("changed_text") or pert.get("original_text") or "")
            if legal:
                text_b = _statute_text(pert)
                kind = "legal"
            else:
                text_b = truncate(pert.get("contradicted_text") or "")
                kind = "in_text"
            if len(text_a) < 40 or len(text_b) < 40:
                skipped += 1
                continue
            loc_a = pert.get("location")
            loc_b = pert.get("contradicted_location") if not legal else pert.get("law_citation")
            gap = section_gap(str(loc_a) if loc_a else None, str(loc_b) if loc_b else None)
            example = {
                "contract_id": contract_id,
                "corpus": corpus,
                "kind": kind,
                "type": normalize_type(raw_type),
                "raw_type": raw_type,
                "text_a": text_a,
                "text_b": text_b,
                "location_a": loc_a,
                "location_b": loc_b,
                "section_gap": gap,
                "gap_bin": gap_bin(gap),
                "explanation": truncate(pert.get("justification") or pert.get("explanation") or "", 800),
                "label": 1,
            }
            grouped[contract_id].append(example)
            n_pos += 1

    rows: list[dict] = []
    all_ids = list(grouped.keys())
    for contract_id, positives in grouped.items():
        split = _split_for_contract(contract_id)
        other_pool = []
        for oid in rng.sample(all_ids, k=min(8, len(all_ids))):
            if oid == contract_id:
                continue
            other_pool.extend(grouped[oid][:2])
        for i, pos in enumerate(positives):
            row = dict(pos)
            row["split"] = split
            row["pair_id"] = f"{contract_id}::pos::{i}"
            rows.append(row)
            # in-file negatives: pair this A with another gold B if possible
            candidates = []
            for j, other in enumerate(positives):
                if i == j:
                    continue
                candidates.append(other["text_b"])
            while len(candidates) < NEGATIVES_PER_POSITIVE and other_pool:
                pick = rng.choice(other_pool)
                candidates.append(pick["text_b"])
            used = set()
            n_neg = 0
            for text_b in candidates:
                if text_b == pos["text_b"] or text_b in used:
                    continue
                used.add(text_b)
                neg = dict(pos)
                neg["text_b"] = text_b
                neg["label"] = 0
                neg["split"] = split
                neg["pair_id"] = f"{contract_id}::neg::{i}::{n_neg}"
                neg["explanation"] = ""
                rows.append(neg)
                n_neg += 1
                if n_neg >= NEGATIVES_PER_POSITIVE:
                    break

    rng.shuffle(rows)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    stats = {
        "json_files_seen": n_files,
        "positives": n_pos,
        "skipped": skipped,
        "rows": len(rows),
        "contracts": len(grouped),
        "by_split": {s: sum(1 for r in rows if r["split"] == s) for s in ("train", "dev", "test")},
        "by_kind_pos": {
            k: sum(1 for r in rows if r["label"] == 1 and r["kind"] == k)
            for k in ("in_text", "legal")
        },
        "by_type_pos": {
            t: sum(1 for r in rows if r["label"] == 1 and r["type"] == t)
            for t in sorted({r["type"] for r in rows})
        },
        "out_path": str(out_path),
    }
    (out_path.parent / "ingest_stats.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")
    return stats
