from __future__ import annotations

from pathlib import Path

import joblib

from auditor.schema import CANONICAL_TYPES, gap_bin, truncate
from auditor.segment import candidate_pairs, segment_contract


def _confidence_label(score: float) -> str:
    if score >= 0.8:
        return "high"
    if score >= 0.65:
        return "medium"
    return "low"


class PairAuditor:
    """TF–IDF pair scorer. Input is a long contract; BERT never sees the full filing."""

    def __init__(self, model_path: Path, backend: str = "tfidf"):
        blob = joblib.load(model_path)
        self.conflict = blob["conflict"]
        self.type_pipe = blob["type_pipe"]
        self.type_encoder = blob["type_encoder"]
        self.backend = backend
        self._lb = None
        self._tok = None

    def attach_legalbert(self, checkpoint: Path) -> None:
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
        import torch

        self._tok = AutoTokenizer.from_pretrained(str(checkpoint))
        self._lb = AutoModelForSequenceClassification.from_pretrained(str(checkpoint))
        self._lb.eval()
        self._torch = torch
        self.backend = "legalbert"

    def score_pair(self, text_a: str, text_b: str) -> dict:
        return self.score_pairs_batch([(text_a, text_b)])[0]

    def score_pairs_batch(
        self,
        pair_texts: list[tuple[str, str]],
        batch_size: int = 16,
    ) -> list[dict]:
        if not pair_texts:
            return []

        joined_list = [f"{truncate(a)} [SEP] {truncate(b)}" for a, b in pair_texts]

        if self._lb is not None and self._tok is not None:
            scores = []
            for i in range(0, len(pair_texts), batch_size):
                chunk = pair_texts[i : i + batch_size]
                texts_a = [t[0][:1200] for t in chunk]
                texts_b = [t[1][:1200] for t in chunk]
                enc = self._tok(
                    texts_a,
                    texts_b,
                    padding=True,
                    truncation=True,
                    max_length=256,
                    return_tensors="pt",
                )
                with self._torch.no_grad():
                    logits = self._lb(**enc).logits
                    probs = self._torch.softmax(logits, dim=-1)[:, 1].tolist()
                    scores.extend(probs)
        else:
            probas = self.conflict.predict_proba(joined_list)[:, 1].tolist()
            scores = [float(p) for p in probas]

        type_ids = self.type_pipe.predict(joined_list)
        type_names = self.type_encoder.inverse_transform(type_ids)

        results = []
        for proba, type_name in zip(scores, type_names):
            t_str = str(type_name)
            if t_str not in CANONICAL_TYPES:
                t_str = "Inconsistency"
            results.append({"score": float(proba), "type": t_str})
        return results

    def analyze(
        self,
        text: str,
        threshold: float = 0.55,
        top_k: int = 8,
        max_pairs: int = 200,
        batch_size: int = 16,
    ) -> dict:
        clauses = segment_contract(text)
        pairs = candidate_pairs(clauses, max_pairs=max_pairs)
        pair_texts = [(clauses[i].text, clauses[j].text) for i, j, _ in pairs]
        scored_list = self.score_pairs_batch(pair_texts, batch_size=batch_size)

        findings = []
        for (i, j, reason), scored in zip(pairs, scored_list):
            a, b = clauses[i], clauses[j]
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
        kept = findings if top_k is None else findings[:top_k]
        return {
            "backend": self.backend,
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
            "findings": kept,
            "threshold": threshold,
        }


def load_auditor(root: Path | None = None) -> PairAuditor:
    root = root or Path(__file__).resolve().parents[1]
    model_path = root / "artifacts" / "tfidf_logreg.joblib"
    auditor = PairAuditor(model_path)
    lb = root / "artifacts" / "legalbert-dca"
    if (lb / "config.json").exists():
        try:
            auditor.attach_legalbert(lb)
        except Exception:
            auditor.backend = "tfidf"
    return auditor
