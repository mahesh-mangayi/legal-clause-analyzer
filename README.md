# Distant Contradiction Auditor (DCA)

Find **two clauses in a contract that silently disagree** (or a clause vs. a statute), even across distant sections of long legal filings. Trained on [Better Call CLAUSE](https://github.com/clause-legal/clause-legal.github.io). This is an auditor decision aid, not legal advice.

---

## 🚀 Current Project Status & Architecture

DCA processes long contracts (20–100+ pages) using a **5-Stage Hierarchical Graph Pipeline**:

```
Raw Contract Text (20-100+ pages) 
  └─> Stage 1: Document Segmenter & Tree Parser (auditor/segment.py)
  └─> Stage 2: Candidate Graph Filter (Cross-refs, Shared Terms, Far Pairs) -> Top-K (~100-200 pairs)
  └─> Stage 3: Batched Cross-Encoder Pair Scorer (Legal-BERT in auditor/infer.py)
  └─> Stage 4: Contradiction Categorization & Ranking (Ambiguity, Inconsistency, Omission, etc.)
  └─> Stage 5: FastAPI Service (:8765) & Next.js Interactive Visual Explorer (:3847)
```

### 📊 Benchmark Summary

| Evaluation Level | Model / Backend | Metric | Score | Notes |
|---|---|---|:---:|---|
| **Pair Scorer** | TF–IDF Pair Logistic | Pair Test F1 | `0.483` | CPU Baseline |
| **Pair Scorer** | **Legal-BERT Fine-tuned** | **Pair Test F1** | **`0.849`** | GPU Fine-tuned (Colab T4) |
| **Document Level** | **DCA Long Contract Pipeline** | **Evaluated Docs** | **`18 contracts`** | 20+ page CUAD contracts |

---

## 📁 Repository Structure

| Path | Description |
|---|---|
| [`auditor/`](file:///c:/Users/madhu/OneDrive/Desktop/legal_project/contract-graph-risk/auditor) | Core auditor package: `segment.py` (clause parser & candidate graph), `infer.py` (batched Legal-BERT pair classifier), `api.py` (FastAPI backend), `align.py` (Jaccard span matching). |
| [`web/`](file:///c:/Users/madhu/OneDrive/Desktop/legal_project/contract-graph-risk/web) | Next.js 15 UI: Dashboard, Upload & Pipeline Timings, Results Table, Visual Conflict Explorer (Arc diagram), and Benchmark table. |
| [`notebooks/train_legalbert_colab.ipynb`](file:///c:/Users/madhu/OneDrive/Desktop/legal_project/contract-graph-risk/notebooks/train_legalbert_colab.ipynb) | Complete Google Colab notebook for fine-tuning Legal-BERT on GPU T4 with **Early Stopping (Patience = 3)** and full **Train/Val/Test** split evaluation. |
| [`scripts/`](file:///c:/Users/madhu/OneDrive/Desktop/legal_project/contract-graph-risk/scripts) | Data ingestion (`ingest_bcc.py`), Colab dataset packaging (`make_colab_subset.py`), test slice extraction (`make_llm_testset.py`), and document benchmark runner (`eval_documents.py`). |
| [`artifacts/`](file:///c:/Users/madhu/OneDrive/Desktop/legal_project/contract-graph-risk/artifacts) | Trained weights (`legalbert-dca/`, `tfidf_logreg.joblib`), evaluation benchmarks (`metrics.json`, `metrics_legalbert.json`, `doc_benchmark.json`), and dataset packages (`pairs_colab_full.jsonl.gz`). |

---

## 🛠️ Quick Start & Running Locally

### 1. Prerequisites & Virtual Environment

```bash
# Clone Better Call CLAUSE dataset (if not present)
git clone --depth 1 https://github.com/clause-legal/clause-legal.github.io.git data/clause-legal

# Setup Python environment
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -e .
```

### 2. Run Data Pipeline & Benchmarks (Optional)

```bash
# Ingest 143k pairs from Better Call CLAUSE
PYTHONPATH=. python scripts/ingest_bcc.py

# Package full dataset for Colab T4
PYTHONPATH=. python scripts/make_colab_subset.py --full

# Run long-document evaluation benchmark
PYTHONPATH=. python scripts/eval_documents.py --docs artifacts/llm_testset_long.jsonl --out artifacts/doc_benchmark.json
```

### 3. Launch Backend API

```bash
PYTHONPATH=. uvicorn auditor.api:app --host 127.0.0.1 --port 8765
```

### 4. Launch Next.js Visual UI

In a separate terminal:

```bash
cd web
npm install
npm run dev
```
Open **`http://127.0.0.1:3847`** in your browser.

---

## 🎓 Model Fine-Tuning on Google Colab

To fine-tune or re-train Legal-BERT on a free **GPU T4** instance:

1. Open Google Colab and upload [`notebooks/train_legalbert_colab.ipynb`](file:///c:/Users/madhu/OneDrive/Desktop/legal_project/contract-graph-risk/notebooks/train_legalbert_colab.ipynb).
2. Set Runtime type to **GPU (T4)**.
3. Upload [`artifacts/pairs_colab_full.jsonl.gz`](file:///c:/Users/madhu/OneDrive/Desktop/legal_project/contract-graph-risk/artifacts/pairs_colab_full.jsonl.gz) to Google Drive at `MyDrive/dca/pairs_colab_full.jsonl.gz` (or upload directly via the interactive file picker).
4. Run all cells (**Runtime** $\rightarrow$ **Run all**).
   * Includes **Train (114.4k)** / **Val (15.5k)** / **Test (13.3k)** contract-stratified splits.
   * Features **Early Stopping (Patience = 3 epochs)** monitoring validation F1 score.
5. Download the output `legalbert-dca/` directory and `metrics_legalbert.json` back into your local `artifacts/` folder.

---

## ✅ Completion Checklist & Optional Next Steps

- [x] **Full Data Ingestion Pipeline**: Ingested 143k pairs across 1,118 contracts.
- [x] **Batched Transformer Inference**: Refactored `PairAuditor` with PyTorch batching.
- [x] **FastAPI & Next.js Stack**: Backend API on `:8765` and Next.js frontend with Conflict Arc Explorer on `:3847`.
- [x] **Colab Early Stopping Notebook**: Configured `notebooks/train_legalbert_colab.ipynb` with `patience=3`.
- [ ] **Optional GPU Fine-Tuning**: Run `train_legalbert_colab.ipynb` on GPU T4 with `pairs_colab_full.jsonl.gz`.
- [ ] **Optional Zero-Shot LLM Evaluation**: Provide `NVIDIA_API_KEY` to evaluate `gpt-oss-120b` or Qwen on `llm_testset_long.jsonl`.
- [ ] **Production Deployment**: Deploy Next.js to Vercel and FastAPI service to Render / AWS / Modal.

---

## 📜 Citation
