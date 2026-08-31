import { Nav } from "@/components/nav";
import { fetchMeta } from "@/lib/api";
import Link from "next/link";

export const dynamic = "force-dynamic";

export default async function HomePage() {
  let meta: {
    ingest?: Record<string, unknown>;
    metrics?: { test?: Record<string, unknown>; model?: string };
    backend?: string;
  } | null = null;
  let error: string | null = null;
  try {
    meta = await fetchMeta();
  } catch {
    error = "API is not running. Start it with: PYTHONPATH=. uvicorn auditor.api:app --host 127.0.0.1 --port 8765";
  }

  const ingest = (meta?.ingest || {}) as {
    positives?: number;
    contracts?: number;
    rows?: number;
    by_kind_pos?: Record<string, number>;
    by_type_pos?: Record<string, number>;
  };
  const test = (meta?.metrics?.test || {}) as {
    f1?: number;
    precision?: number;
    recall?: number;
    type_macro_f1_on_gold_positives?: number;
  };

  const stats = [
    { label: "Source contracts", value: ingest.contracts ?? "—" },
    { label: "Gold contradictions", value: ingest.positives ?? "—" },
    { label: "Training pairs", value: ingest.rows ?? "—" },
    { label: "In-text / legal gold", value: ingest.by_kind_pos ? `${ingest.by_kind_pos.in_text} / ${ingest.by_kind_pos.legal}` : "—" },
  ];

  return (
    <div className="min-h-full">
      <Nav current="/" />
      <main className="mx-auto max-w-6xl px-4 py-10">
        <p className="text-sm uppercase tracking-[0.2em] text-[var(--accent)]">Better Call CLAUSE</p>
        <h1 className="mt-2 max-w-3xl font-serif text-4xl leading-tight sm:text-5xl">
          Catch two clauses that silently disagree — even when they sit pages apart.
        </h1>
        <p className="mt-4 max-w-2xl text-[var(--muted)]">
          Single-clause models never compare provisions. Retrieval looks for similar text. This
          auditor scores <em>pairs</em> of sections so a reviewer can see both spans, the discrepancy
          type, and a confidence score.
        </p>
        <div className="mt-8 flex flex-wrap gap-3">
          <Link
            href="/upload"
            className="rounded-full bg-[var(--ink)] px-5 py-2.5 text-sm text-[var(--paper)]"
          >
            Analyze a contract
          </Link>
          <Link
            href="/benchmark"
            className="rounded-full border border-[var(--line)] px-5 py-2.5 text-sm"
          >
            Open evaluation table
          </Link>
        </div>
        {error ? (
          <p className="mt-8 rounded-lg border border-[var(--accent)]/40 bg-white px-4 py-3 text-sm text-[var(--accent)]">
            {error}
          </p>
        ) : null}
        <div className="mt-10 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {stats.map((s) => (
            <div key={s.label} className="rounded-xl border border-[var(--line)] bg-white p-4">
              <div className="text-xs uppercase tracking-wide text-[var(--muted)]">{s.label}</div>
              <div className="mt-2 font-serif text-2xl">{String(s.value)}</div>
            </div>
          ))}
        </div>
        <div className="mt-10 grid gap-6 lg:grid-cols-2">
          <div className="rounded-xl border border-[var(--line)] bg-white p-5">
            <h2 className="font-serif text-xl">Who uses it</h2>
            <p className="mt-2 text-sm leading-6 text-[var(--muted)]">
              Contract reviewers upload a draft and inspect ranked findings. Advisors use the
              Benchmark page to see pair F1 and performance by section distance. This is not legal
              advice — it flags possible disagreements for a human to read.
            </p>
          </div>
          <div className="rounded-xl border border-[var(--line)] bg-white p-5">
            <h2 className="font-serif text-xl">Current backend</h2>
            <p className="mt-2 text-sm leading-6 text-[var(--muted)]">
              Demo scorer: <code className="rounded bg-[var(--wash)] px-1">{meta?.backend || "offline"}</code>
              . CPU TF–IDF logistic trained on CLAUSE pairs. Swap in Legal-BERT from the Colab T4
              notebook when that checkpoint is ready. Test pair F1 {test.f1 ?? "—"}; recall{" "}
              {test.recall ?? "—"}.
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}
