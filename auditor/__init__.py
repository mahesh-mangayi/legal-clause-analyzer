"""Distant Contradiction Auditor."""

__all__ = [
    "CANONICAL_TYPES",
    "PairAuditor",
    "candidate_pairs",
    "ingest",
    "segment_contract",
    "train_baseline",
]


def __getattr__(name: str):
    if name == "ingest":
        from auditor.ingest import ingest as _ingest

        return _ingest
    if name == "PairAuditor":
        from auditor.infer import PairAuditor as _PairAuditor

        return _PairAuditor
    if name == "CANONICAL_TYPES":
        from auditor.schema import CANONICAL_TYPES as _types

        return _types
    if name in ("candidate_pairs", "segment_contract"):
        from auditor import segment

        return getattr(segment, name)
    if name == "train_baseline":
        from auditor.train_baseline import train_baseline as _train

        return _train
    raise AttributeError(name)
