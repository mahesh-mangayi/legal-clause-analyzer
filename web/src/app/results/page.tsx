"use client";

import { Nav } from "@/components/nav";
import type { AnalyzeResult } from "@/lib/api";
import Link from "next/link";
import { useEffect, useState } from "react";

function badge(conf: string) {
  if (conf === "high") return "bg-[var(--ok)]/15 text-[var(--ok)]";
  if (conf === "medium") return "bg-[var(--warn)]/15 text-[var(--warn)]";
  return "border border-dashed border-[var(--muted)] text-[var(--muted)]";
}

export default function ResultsPage() {
  const [title, setTitle] = useState("Last analysis");
  const [result, setResult] = useState<AnalyzeResult | null>(null);
  const [empty, setEmpty] = useState(false);

  useEffect(() => {
    const raw = sessionStorage.getItem("dca-result");
    setTitle(sessionStorage.getItem("dca-title") || "Last analysis");
    if (!raw) {
      setEmpty(true);
      return;
    }
    setResult(JSON.parse(raw) as AnalyzeResult);
  }, []);

  if (empty) {
    return (
      <div className="min-h-full">
        <Nav current="/results" />
        <main className="mx-auto max-w-3xl px-4 py-16 text-center">
          <h1 className="font-serif text-3xl">No analysis yet</h1>
          <p className="mt-3 text-[var(--muted)]">Run the auditor on a contract first.</p>
          <Link href="/upload" className="mt-6 inline-block rounded-full bg-[var(--ink)] px-5 py-2.5 text-sm text-[var(--paper)]">
            Go to upload
          </Link>
        </main>
      </div>
    );
  }

  if (!result) {
    return (
      <div className="min-h-full">
        <Nav current="/results" />
        <main className="mx-auto max-w-3xl px-4 py-16 text-[var(--muted)]">Loading…</main>
      </div>
    );
  }

  return (
    <div className="min-h-full">
      <Nav current="/results" />
      <main className="mx-auto max-w-6xl px-4 py-8">
        <p className="text-sm text-[var(--muted)]">{title}</p>
        <h1 className="font-serif text-3xl">Ranked discrepancies</h1>
        <p className="mt-2 text-sm text-[var(--muted)]">
          {result.n_clauses} clauses · {result.n_candidates} candidate pairs · threshold {result.threshold}
        </p>
        {result.warning ? (
          <p className="mt-4 rounded-lg border border-[var(--warn)]/40 bg-white px-4 py-3 text-sm">{result.warning}</p>
        ) : null}
        {result.findings.length === 0 ? (
          <div className="mt-10 rounded-xl border border-[var(--line)] bg-white p-8">
            <h2 className="font-serif text-2xl">No discrepancies above threshold</h2>
            <p className="mt-2 text-sm text-[var(--muted)]">
              That means the scorer did not find a conflicting pair — not that the document has no clauses.
            </p>
          </div>
        ) : (
          <ol className="mt-8 space-y-4">
            {result.findings.map((f, i) => (
              <li key={`${f.clause_id_a}-${f.clause_id_b}`} className="rounded-xl border border-[var(--line)] bg-white p-5">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-mono text-xs text-[var(--muted)]">#{i + 1}</span>
                  <span className="rounded-full bg-[var(--wash)] px-2 py-0.5 text-xs">{f.type}</span>
                  <span className={`rounded-full px-2 py-0.5 text-xs ${badge(f.confidence)}`}>
                    {f.confidence} · {f.score.toFixed(2)}
                  </span>
                  <span className="text-xs text-[var(--muted)]">
                    {f.gap_bin.replace("_", " ")} · via {f.candidate_reason}
                  </span>
                </div>
                <p className="mt-3 text-sm">
                  <span className="font-medium">{f.heading_a}</span>
                  <span className="text-[var(--muted)]"> → </span>
                  <span className="font-medium">{f.heading_b}</span>
                </p>
                <div className="mt-3 grid gap-3 md:grid-cols-2">
                  <p className="text-sm leading-6 text-[var(--muted)]">{f.span_a.slice(0, 420)}</p>
                  <p className="text-sm leading-6 text-[var(--muted)]">{f.span_b.slice(0, 420)}</p>
                </div>
                <Link
                  href={`/explorer?i=${i}`}
                  className="mt-3 inline-block text-sm text-[var(--accent)] underline"
                >
                  Open in explorer
                </Link>
              </li>
            ))}
          </ol>
        )}
      </main>
    </div>
  );
}
