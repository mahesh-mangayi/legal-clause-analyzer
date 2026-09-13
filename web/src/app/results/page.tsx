"use client";

import { Nav } from "@/components/nav";
import type { AnalyzeResult } from "@/lib/api";
import Link from "next/link";
import { useEffect, useState } from "react";

type LoadState =
  | { status: "loading" }
  | { status: "empty" }
  | { status: "ready"; result: AnalyzeResult; title: string };

function badge(conf: string) {
  if (conf === "high") return "bg-[var(--ok)]/15 text-[var(--ok)]";
  if (conf === "medium") return "bg-[var(--warn)]/15 text-[var(--warn)]";
  return "border border-dashed border-[var(--muted)] text-[var(--muted)]";
}

function confidenceIcon(conf: string) {
  if (conf === "high") return "🔴";
  if (conf === "medium") return "🟡";
  return "⚪";
}

export default function ResultsPage() {
  const [state, setState] = useState<LoadState>({ status: "loading" });

  useEffect(() => {
    // This runs only on the client, so sessionStorage is always available here
    let raw: string | null = null;
    let storedTitle = "Last analysis";

    try {
      raw = sessionStorage.getItem("dca-result");
      storedTitle = sessionStorage.getItem("dca-title") || "Last analysis";
    } catch {
      // sessionStorage blocked (private mode, etc.) — treat as empty
    }

    if (!raw) {
      setState({ status: "empty" });
      return;
    }

    try {
      const parsed = JSON.parse(raw) as AnalyzeResult;
      setState({ status: "ready", result: parsed, title: storedTitle });
    } catch {
      setState({ status: "empty" });
    }
  }, []);

  // ── Loading state ──────────────────────────────────────────────────────────
  if (state.status === "loading") {
    return (
      <div className="min-h-full">
        <Nav current="/results" />
        <main className="mx-auto max-w-3xl px-4 py-16 text-center text-[var(--muted)]">
          <div className="inline-block h-8 w-8 animate-spin rounded-full border-2 border-[var(--line)] border-t-[var(--ink)]" />
          <p className="mt-4 text-sm">Loading results…</p>
        </main>
      </div>
    );
  }

  // ── Empty state ────────────────────────────────────────────────────────────
  if (state.status === "empty") {
    return (
      <div className="min-h-full">
        <Nav current="/results" />
        <main className="mx-auto max-w-3xl px-4 py-16 text-center">
          <div className="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-full border-2 border-dashed border-[var(--line)]">
            <span className="text-2xl">📄</span>
          </div>
          <h1 className="font-serif text-3xl">No analysis yet</h1>
          <p className="mt-3 text-[var(--muted)]">Run the auditor on a contract first.</p>
          <Link
            href="/upload"
            className="mt-6 inline-block rounded-full bg-[var(--ink)] px-5 py-2.5 text-sm text-[var(--paper)] hover:opacity-90 transition-opacity"
          >
            Go to Upload
          </Link>
        </main>
      </div>
    );
  }

  // ── Results state ──────────────────────────────────────────────────────────
  const { result, title } = state;

  return (
    <div className="min-h-full">
      <Nav current="/results" />
      <main className="mx-auto max-w-6xl px-4 py-8">
        {/* Header */}
        <p className="text-sm text-[var(--muted)]">{title}</p>
        <h1 className="mt-1 font-serif text-3xl">Ranked discrepancies</h1>
        <div className="mt-2 flex flex-wrap gap-4 text-sm text-[var(--muted)]">
          <span>
            <strong className="text-[var(--ink)]">{result.n_clauses}</strong> clauses
          </span>
          <span>
            <strong className="text-[var(--ink)]">{result.n_candidates}</strong> candidate pairs
          </span>
          <span>
            threshold <strong className="text-[var(--ink)]">{result.threshold}</strong>
          </span>
          {result.timings?.total_ms != null && (
            <span>
              completed in{" "}
              <strong className="text-[var(--ink)]">{Math.round(result.timings.total_ms)} ms</strong>
            </span>
          )}
        </div>

        {/* Warning */}
        {result.warning ? (
          <p className="mt-4 rounded-lg border border-[var(--warn)]/40 bg-white px-4 py-3 text-sm">
            ⚠ {result.warning}
          </p>
        ) : null}

        {/* Navigation to explorer */}
        {result.findings.length > 0 && (
          <div className="mt-4 flex gap-3">
            <Link
              href="/explorer"
              className="rounded-full border border-[var(--line)] px-4 py-1.5 text-sm hover:border-[var(--ink)] transition-colors"
            >
              Open Arc Explorer →
            </Link>
          </div>
        )}

        {/* Findings */}
        {result.findings.length === 0 ? (
          <div className="mt-10 rounded-xl border border-[var(--line)] bg-white p-8 text-center">
            <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-[var(--wash)]">
              <span className="text-xl">✓</span>
            </div>
            <h2 className="font-serif text-2xl">No discrepancies above threshold</h2>
            <p className="mt-2 text-sm text-[var(--muted)]">
              The scorer did not find a conflicting pair above the{" "}
              <code className="rounded bg-[var(--wash)] px-1">{result.threshold}</code> threshold
              — not that the document has no clauses.
            </p>
            <p className="mt-1 text-xs text-[var(--muted)]">
              Try lowering the threshold or uploading a longer contract.
            </p>
            <Link
              href="/upload"
              className="mt-6 inline-block rounded-full bg-[var(--ink)] px-5 py-2.5 text-sm text-[var(--paper)]"
            >
              Try another contract
            </Link>
          </div>
        ) : (
          <ol className="mt-8 space-y-4">
            {result.findings.map((f, i) => (
              <li
                key={`${f.clause_id_a}-${f.clause_id_b}-${i}`}
                className="rounded-xl border border-[var(--line)] bg-white p-5 hover:border-[var(--muted)] transition-colors"
              >
                {/* Finding metadata row */}
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-mono text-xs text-[var(--muted)]">#{i + 1}</span>
                  <span className="rounded-full bg-[var(--wash)] px-2 py-0.5 text-xs font-medium">
                    {f.type}
                  </span>
                  <span className={`rounded-full px-2 py-0.5 text-xs ${badge(f.confidence)}`}>
                    {confidenceIcon(f.confidence)} {f.confidence} · {f.score.toFixed(3)}
                  </span>
                  <span className="text-xs text-[var(--muted)]">
                    {f.gap_bin.replace(/_/g, " ")} · via {f.candidate_reason}
                  </span>
                  <span className="text-xs text-[var(--muted)]">
                    §gap {f.section_gap}
                  </span>
                </div>

                {/* Headings arrow */}
                <p className="mt-3 text-sm">
                  <span className="font-medium text-[var(--accent)]">{f.heading_a || f.clause_id_a}</span>
                  <span className="mx-2 text-[var(--muted)]">→</span>
                  <span className="font-medium text-[var(--accent)]">{f.heading_b || f.clause_id_b}</span>
                </p>

                {/* Clause excerpts */}
                <div className="mt-3 grid gap-3 md:grid-cols-2">
                  <div className="rounded-lg border border-[var(--line)] bg-[var(--wash)] p-3">
                    <p className="mb-1 text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
                      Clause A
                    </p>
                    <p className="text-sm leading-6">{f.span_a.slice(0, 500)}{f.span_a.length > 500 ? "…" : ""}</p>
                  </div>
                  <div className="rounded-lg border border-[var(--line)] bg-[var(--wash)] p-3">
                    <p className="mb-1 text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
                      Clause B
                    </p>
                    <p className="text-sm leading-6">{f.span_b.slice(0, 500)}{f.span_b.length > 500 ? "…" : ""}</p>
                  </div>
                </div>

                {/* Link to explorer */}
                <Link
                  href={`/explorer?i=${i}`}
                  className="mt-3 inline-block text-sm text-[var(--accent)] underline underline-offset-2 hover:text-[var(--ink)] transition-colors"
                >
                  Open in Arc Explorer →
                </Link>
              </li>
            ))}
          </ol>
        )}
      </main>
    </div>
  );
}
