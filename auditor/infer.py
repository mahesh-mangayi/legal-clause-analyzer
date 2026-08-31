from __future__ import annotations

from pathlib import Path

import joblib

from auditor.schema import CANONICAL_TYPES, gap_bin, truncate
from auditor.segment import candidate_pairs, segment_contract


class PairAuditor:
    def __init__(self, model_path: Path):
        blob = joblib.load(model_path)
        self.conflict = blob["conflict"]
        self.type_pipe = blob["type_pipe"]
        self.type_encoder = blob["type_encoder"]

    def score_pair(self, text_a: str, text_b: str) -> dict:
        joined = f"{truncate(text_a)} [SEP] {truncate(text_b)}"
        proba = float(self.conflict.predict_proba([joined])[0][1])
        type_id = int(self.type_pipe.predict([joined])[0])
        type_name = str(self.type_encoder.inverse_transform([type_id])[0])
        if type_name not in CANONICAL_TYPES:
            type_name = "Inconsistency"
        return {"score": proba, "type": type_name}

    def analyze(self, text: str, threshold: float = 0.55, top_k: int = 8) -> dict:
        clauses = segment_contract(text)
        pairs = candidate_pairs(clauses)
        findings = []
        for i, j, reason in pairs:
            a, b = clauses[i], clauses[j]
            scored = self.score_pair(a.text, b.text)
            if scored["score"] < threshold:
                continue
            findings.append(
                {
                    "span_a": a.text[:900],
                    "span_b": b.text[:900],
                    "heading_a": a.heading,
                    "heading_b": b.heading,
                    "clause_id_a": a.clause_id,
                    "clause_id_b": b.clause_id,
                    "order_a": a.order,
                    "order_b": b.order,
                    "kind": "in_text",
                    "type": scored["type"],
                    "score": round(scored["score"], 4),
                    "confidence": _confidence_label(scored["score"]),
                    "candidate_reason": reason,
                    "gap_bin": gap_bin(abs(a.order - b.order)),
                    "section_gap": abs(a.order - b.order),
                }
            )
        findings.sort(key=lambda x: x["score"], reverse=True)
        return {
            "clauses": [
                {
                    "clause_id": c.clause_id,
                    "heading": c.heading,
                    "text": c.text[:1200],
                    "order": c.order,
                    "start": c.start,
                    "end": c.end,
                }
                for c in clauses
            ],
            "n_candidates": len(pairs),
            "findings": findings[:top_k],
            "threshold": threshold,
        }


def _confidence_label(score: float) -> str:
    if score >= 0.8:
        return "high"
    if score >= 0.65:
        return "medium"
    return "low"
