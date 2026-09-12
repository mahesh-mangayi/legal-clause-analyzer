import { Nav } from "@/components/nav";
import { fetchMeta } from "@/lib/api";

export const dynamic = "force-dynamic";

type PairTest = {
  n?: number;
  precision?: number;
  recall?: number;
  f1?: number;
  type_macro_f1_on_gold_positives?: number | null;
  f1_by_gap_bin_gold_positives?: Record<string, number>;
};

type LegalBert = {
  model?: string;
  test_precision?: number;
  test_recall?: number;
  test_f1?: number;
  n_test?: number;
  f1_by_gap_bin_gold_positives?: Record<string, number>;
};

export default async function BenchmarkPage() {
  let metrics: {
    model?: string;
    n_train?: number;
    test?: PairTest;
    legalbert?: LegalBert;
  } = {};
  let error: string | null = null;
  try {
    const meta = await fetchMeta();
    metrics = meta.metrics || {};
  } catch {
    error = "Start the API to load live metrics, or read artifacts/metrics.json.";
  }

  const test = metrics.test || {};
  const lb = metrics.legalbert || {};
  const tfidfBins = test.f1_by_gap_bin_gold_positives || {};
  const bertBins = lb.f1_by_gap_bin_gold_positives || {};
  const gapKeys = ["same_section", "nearby", "far", "unknown"];

  const rows = [
    {
      name: "TF–IDF pair logistic (this demo)",
      f1: test.f1,
      precision: test.precision,
      recall: test.recall,
      typeF1: test.type_macro_f1_on_gold_positives,
      notes: `${metrics.n_train ?? "—"} train pairs · CPU · n_test ${test.n ?? "—"}`,
    },
    {
      name: "Legal-BERT pair classifier (Colab T4)",
      f1: lb.test_f1,
      precision: lb.test_precision,
      recall: lb.test_recall,
      typeF1: "—",
      notes: lb.test_f1
        ? `${lb.model ?? "legal-bert"} · 2 epochs · n_test ${lb.n_test ?? "—"}`
        : "Missing artifacts/metrics_legalbert.json",
    },
    {
      name: "gpt-oss-120b (NVIDIA Build)",
      f1: "—",
      precision: "—",
      recall: "—",
      typeF1: "—",
      notes: "Document-level JSON on frozen llm_testset.jsonl — not yet run",
    },
    {
      name: "Nemotron / Qwen chat (NVIDIA Build)",
      f1: "—",
      precision: "—",
      recall: "—",
      typeF1: "—",
      notes: "Same prompt and test docs as gpt-oss-120b",
    },
  ];

  return (
    <div className="min-h-full">
      <Nav current="/benchmark" />
      <main className="mx-auto max-w-6xl px-4 py-8">
        <h1 className="font-serif text-3xl">Benchmark</h1>
        <p className="mt-3 max-w-3xl text-sm leading-6 text-[var(--muted)]">
          TF–IDF and Legal-BERT are <strong>pair classifiers</strong> (two spans in, conflict or
          not). NVIDIA rows are a different job: list disagreeing pairs from the full truncated
          contract. Gap F1 is the paper claim. Precision matters: dumping 40 guesses inflates
          recall and still fails as a reviewer.
        </p>
        {error ? <p className="mt-4 text-sm text-[var(--accent)]">{error}</p> : null}
        <div className="mt-8 overflow-x-auto rounded-xl border border-[var(--line)] bg-white">
          <table className="min-w-full text-left text-sm">
            <thead className="border-b border-[var(--line)] text-xs uppercase tracking-wide text-[var(--muted)]">
              <tr>
                <th className="px-4 py-3">Model</th>
                <th className="px-4 py-3">Precision</th>
                <th className="px-4 py-3">Recall</th>
                <th className="px-4 py-3">Pair F1</th>
                <th className="px-4 py-3">Type F1</th>
                <th className="px-4 py-3">Notes</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.name} className="border-b border-[var(--line)] last:border-0">
                  <td className="px-4 py-3 font-medium">{r.name}</td>
                  <td className="px-4 py-3 font-mono">{fmt(r.precision)}</td>
                  <td className="px-4 py-3 font-mono">{fmt(r.recall)}</td>
                  <td className="px-4 py-3 font-mono">{fmt(r.f1)}</td>
                  <td className="px-4 py-3 font-mono">{fmt(r.typeF1)}</td>
                  <td className="px-4 py-3 text-[var(--muted)]">{r.notes}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <h2 className="mt-10 font-serif text-2xl">Gold-positive F1 by section gap</h2>
        <p className="mt-2 text-sm text-[var(--muted)]">
          Nearby pairs are the harder bin. Legal-BERT and TF–IDF use the Colab/CPU pair test
          slices, not the document LLM slice.
        </p>
        <div className="mt-4 overflow-x-auto rounded-xl border border-[var(--line)] bg-white">
          <table className="min-w-full text-left text-sm">
            <thead className="border-b border-[var(--line)] text-xs uppercase tracking-wide text-[var(--muted)]">
              <tr>
                <th className="px-4 py-3">Model</th>
                {gapKeys.map((k) => (
                  <th key={k} className="px-4 py-3">
                    {k.replaceAll("_", " ")}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              <tr className="border-b border-[var(--line)]">
                <td className="px-4 py-3 font-medium">TF–IDF</td>
                {gapKeys.map((k) => (
                  <td key={k} className="px-4 py-3 font-mono">
                    {fmt(tfidfBins[k])}
                  </td>
                ))}
              </tr>
              <tr>
                <td className="px-4 py-3 font-medium">Legal-BERT</td>
                {gapKeys.map((k) => (
                  <td key={k} className="px-4 py-3 font-mono">
                    {fmt(bertBins[k])}
                  </td>
                ))}
              </tr>
            </tbody>
          </table>
        </div>
      </main>
    </div>
  );
}

function fmt(v: unknown) {
  if (v == null || v === "—") return "—";
  if (typeof v === "number") return v.toFixed(3);
  return String(v);
}
