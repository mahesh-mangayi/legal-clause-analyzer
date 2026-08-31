import { Nav } from "@/components/nav";
import { fetchMeta } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function BenchmarkPage() {
  let metrics: {
    model?: string;
    n_train?: number;
    test?: {
      n?: number;
      precision?: number;
      recall?: number;
      f1?: number;
      type_macro_f1_on_gold_positives?: number | null;
      f1_by_gap_bin_gold_positives?: Record<string, number>;
    };
    legalbert?: Record<string, unknown>;
  } = {};
  let error: string | null = null;
  try {
    const meta = await fetchMeta();
    metrics = meta.metrics || {};
  } catch {
    error = "Start the API to load live metrics, or read artifacts/metrics.json.";
  }

  const test = metrics.test || {};
  const bins = test.f1_by_gap_bin_gold_positives || {};

  const rows = [
    {
      name: "TF–IDF pair logistic (this demo)",
      f1: test.f1,
      precision: test.precision,
      recall: test.recall,
      typeF1: test.type_macro_f1_on_gold_positives,
      notes: `${metrics.n_train ?? "—"} train pairs · CPU`,
    },
    {
      name: "Legal-BERT single clause",
      f1: "—",
      precision: "—",
      recall: "—",
      typeF1: "—",
      notes: "Run notebooks/train_legalbert_colab.ipynb on T4, then paste metrics",
    },
    {
      name: "Legal-BERT cross-encoder (Colab T4)",
      f1: "—",
      precision: "—",
      recall: "—",
      typeF1: "—",
      notes: "Upload artifacts/pairs_colab.jsonl.gz to Drive",
    },
    {
      name: "Embedding kNN / RAG",
      f1: "—",
      precision: "—",
      recall: "—",
      typeF1: "—",
      notes: "Same Colab notebook, cosine baseline cell can be added",
    },
  ];

  return (
    <div className="min-h-full">
      <Nav current="/benchmark" />
      <main className="mx-auto max-w-6xl px-4 py-8">
        <h1 className="font-serif text-3xl">Benchmark</h1>
        <p className="mt-3 max-w-3xl text-sm leading-6 text-[var(--muted)]">
          The paper table is pair F1 <strong>by document distance</strong> (same section / nearby /
          far), not hop length. BCC gold is a two-span conflict. Legal-BERT numbers appear after the
          T4 notebook finishes.
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
        <h2 className="mt-10 font-serif text-2xl">Gold-positive recall by section gap</h2>
        <p className="mt-2 text-sm text-[var(--muted)]">
          Among labeled contradictions, how often the pair model still fires, binned by parsed
          section numbers.
        </p>
        <div className="mt-4 grid gap-3 sm:grid-cols-4">
          {Object.entries(bins).map(([k, v]) => (
            <div key={k} className="rounded-xl border border-[var(--line)] bg-white p-4">
              <div className="text-xs uppercase text-[var(--muted)]">{k.replaceAll("_", " ")}</div>
              <div className="mt-2 font-serif text-2xl">{typeof v === "number" ? v.toFixed(3) : v}</div>
            </div>
          ))}
          {Object.keys(bins).length === 0 ? (
            <div className="text-sm text-[var(--muted)]">No bin metrics loaded.</div>
          ) : null}
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
