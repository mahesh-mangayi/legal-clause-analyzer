# Distant Contradiction Auditor

Find **two places in a contract that silently disagree** (or a clause vs a statute). Trained on [Better Call CLAUSE](https://github.com/clause-legal/clause-legal.github.io). This is a reviewer aid, not legal advice.

BCC labels **pairs**, not 3-hop graphs. The model scores clause pairs. Structure (section order, cross-references, shared terms) only decides **which pairs to score**.

## What is in this repo

| Path | Role |
|---|---|
| `auditor/` | Ingest, segmenter, TF–IDF pair scorer, FastAPI |
| `scripts/` | `ingest_bcc.py`, `train_baseline.py`, Colab subset, demo samples |
| `notebooks/train_legalbert_colab.ipynb` | Legal-BERT fine-tune on a **T4** |
| `web/` | Five-page demo |
| `artifacts/` | Metrics, CPU model, `pairs_colab.jsonl.gz` for Drive |

Do not commit the full CLAUSE clone (`data/clause-legal/`) or the 257MB `pairs.jsonl`.

## Local demo (CPU)

```bash
# CLAUSE clone (once)
git clone --depth 1 https://github.com/clause-legal/clause-legal.github.io.git data/clause-legal

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .

PYTHONPATH=. python scripts/ingest_bcc.py          # artifacts/pairs.jsonl
PYTHONPATH=. python scripts/make_colab_subset.py
PYTHONPATH=. python scripts/export_demo_samples.py
PYTHONPATH=. python scripts/train_baseline.py      # artifacts/tfidf_logreg.joblib

PYTHONPATH=. uvicorn auditor.api:app --host 127.0.0.1 --port 8765
```

In another terminal:

```bash
cd web
npm install
npm run dev   # http://127.0.0.1:3847
```

Pages: Dashboard, Upload (CLAUSE samples + pipeline timings), Results, Conflict Explorer (document-order arc), Benchmark.

## Legal-BERT on Colab T4

1. Upload `artifacts/pairs_colab.jsonl.gz` to `Drive/MyDrive/dca/`.
2. Open `notebooks/train_legalbert_colab.ipynb`, runtime GPU T4.
3. Download `legalbert-dca/` + `metrics_legalbert.json` when done.

T4 settings in the notebook: `fp16`, batch 8, accum 4, `max_length=256`, 2 epochs.

No OpenAI/Gemini key is required for detection.

## Cite

Roy Choudhury et al. Better Call CLAUSE, EACL 2026 Findings. Dataset CC BY 4.0 via CUAD / ContractNLI.
