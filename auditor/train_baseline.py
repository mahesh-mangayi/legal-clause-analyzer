from __future__ import annotations

import json
from pathlib import Path

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, f1_score, precision_recall_fscore_support
from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.preprocessing import LabelEncoder


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _pair_text(row: dict) -> str:
    return f"{row['text_a']} [SEP] {row['text_b']}"


def _f1_by_bin(y_true, y_pred, bins: list[str]) -> dict[str, float]:
    out: dict[str, float] = {}
    for name in sorted(set(bins)):
        idx = [i for i, b in enumerate(bins) if b == name]
        if not idx:
            continue
        yt = [y_true[i] for i in idx]
        yp = [y_pred[i] for i in idx]
        out[name] = round(float(f1_score(yt, yp, zero_division=0)), 4)
    return out


def train_baseline(pairs_path: Path, out_dir: Path) -> dict:
    rows = load_jsonl(pairs_path)
    train = [r for r in rows if r["split"] == "train"]
    dev = [r for r in rows if r["split"] == "dev"]
    test = [r for r in rows if r["split"] == "test"]
    # CPU-friendly cap; Colab uses the full / subset jsonl with Legal-BERT
    if len(train) > 28000:
        pos = [r for r in train if r["label"] == 1]
        neg = [r for r in train if r["label"] == 0]
        train = pos[:14000] + neg[:14000]
    if len(dev) > 4000:
        dev = dev[:4000]
    if len(test) > 5000:
        test = test[:5000]

    vectorizer = FeatureUnion(
        [
            (
                "word",
                TfidfVectorizer(max_features=40000, ngram_range=(1, 2), min_df=2, sublinear_tf=True),
            ),
            (
                "char",
                TfidfVectorizer(analyzer="char", ngram_range=(3, 5), max_features=40000, min_df=3),
            ),
        ]
    )
    clf = LogisticRegression(max_iter=200, class_weight="balanced", C=1.0)
    pipe = Pipeline([("tfidf", vectorizer), ("clf", clf)])
    pipe.fit([_pair_text(r) for r in train], [r["label"] for r in train])

    pos_train = [r for r in train if r["label"] == 1]
    type_encoder = LabelEncoder()
    type_encoder.fit([r["type"] for r in pos_train])
    type_pipe = Pipeline(
        [
            (
                "tfidf",
                TfidfVectorizer(max_features=50000, ngram_range=(1, 2), min_df=2, sublinear_tf=True),
            ),
            ("clf", LogisticRegression(max_iter=200, class_weight="balanced")),
        ]
    )
    type_pipe.fit([_pair_text(r) for r in pos_train], type_encoder.transform([r["type"] for r in pos_train]))

    def eval_split(name: str, split_rows: list[dict]) -> dict:
        if not split_rows:
            return {}
        texts = [_pair_text(r) for r in split_rows]
        y = [r["label"] for r in split_rows]
        pred = pipe.predict(texts)
        proba = pipe.predict_proba(texts)[:, 1]
        p, rec, f1, _ = precision_recall_fscore_support(y, pred, average="binary", zero_division=0)
        pos_idx = [i for i, r in enumerate(split_rows) if r["label"] == 1]
        type_f1 = None
        if pos_idx:
            type_true = type_encoder.transform([split_rows[i]["type"] for i in pos_idx])
            type_pred = type_pipe.predict([texts[i] for i in pos_idx])
            type_f1 = round(float(f1_score(type_true, type_pred, average="macro", zero_division=0)), 4)
        bins = [split_rows[i]["gap_bin"] for i in pos_idx] if pos_idx else []
        y_pos = [1] * len(pos_idx)
        pred_pos = [int(pred[i]) for i in pos_idx]
        return {
            "n": len(split_rows),
            "precision": round(float(p), 4),
            "recall": round(float(rec), 4),
            "f1": round(float(f1), 4),
            "type_macro_f1_on_gold_positives": type_f1,
            "f1_by_gap_bin_gold_positives": _f1_by_bin(y_pos, pred_pos, bins) if bins else {},
            "mean_positive_score": round(float(sum(proba[i] for i in pos_idx) / max(len(pos_idx), 1)), 4),
            "report": classification_report(y, pred, digits=3, zero_division=0),
        }

    metrics = {
        "model": "tfidf_logreg_pair",
        "dev": eval_split("dev", dev),
        "test": eval_split("test", test),
        "n_train": len(train),
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {"conflict": pipe, "type_pipe": type_pipe, "type_encoder": type_encoder},
        out_dir / "tfidf_logreg.joblib",
    )
    (out_dir / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return metrics
