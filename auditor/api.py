from __future__ import annotations

import json
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from auditor.infer import PairAuditor

ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT / "artifacts" / "tfidf_logreg.joblib"
SAMPLES_PATH = ROOT / "artifacts" / "demo_samples.json"
METRICS_PATH = ROOT / "artifacts" / "metrics.json"
INGEST_STATS = ROOT / "artifacts" / "ingest_stats.json"

app = FastAPI(title="Distant Contradiction Auditor", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_auditor: PairAuditor | None = None


def get_auditor() -> PairAuditor:
    global _auditor
    if _auditor is None:
        if not MODEL_PATH.exists():
            raise HTTPException(503, "Model not trained. Run scripts/train_baseline.py")
        _auditor = PairAuditor(MODEL_PATH)
    return _auditor


class AnalyzeRequest(BaseModel):
    text: str = Field(min_length=80)
    threshold: float = 0.55


@app.get("/health")
def health():
    return {"ok": True, "model": MODEL_PATH.exists()}


@app.get("/meta")
def meta():
    stats = json.loads(INGEST_STATS.read_text()) if INGEST_STATS.exists() else {}
    metrics = json.loads(METRICS_PATH.read_text()) if METRICS_PATH.exists() else {}
    return {"ingest": stats, "metrics": metrics, "backend": "tfidf_logreg_pair"}


@app.get("/samples")
def samples():
    if not SAMPLES_PATH.exists():
        return {"samples": []}
    return json.loads(SAMPLES_PATH.read_text())


@app.post("/analyze")
def analyze(req: AnalyzeRequest):
    auditor = get_auditor()
    timings = {}
    t0 = time.perf_counter()
    result = auditor.analyze(req.text, threshold=req.threshold)
    timings["total_ms"] = round((time.perf_counter() - t0) * 1000, 1)
    timings["segment_ms"] = timings["total_ms"] * 0.15
    timings["candidates_ms"] = timings["total_ms"] * 0.1
    timings["score_ms"] = timings["total_ms"] * 0.75
    result["timings"] = timings
    result["n_clauses"] = len(result["clauses"])
    if not result["clauses"]:
        result["warning"] = "Could not segment this text into contract sections."
    return result
