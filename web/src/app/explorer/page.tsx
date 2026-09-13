"use client";

import { Nav } from "@/components/nav";
import type { AnalyzeResult } from "@/lib/api";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useMemo, useState } from "react";

type LoadState =
  | { status: "loading" }
  | { status: "empty" }
  | { status: "ready"; result: AnalyzeResult; title: string };

function ExplorerInner() {
  const params = useSearchParams();
  const idx = Math.max(0, Number(params.get("i") || "0"));
  const [state, setState] = useState<LoadState>({ status: "loading" });

  useEffect(() => {
    let raw: string | null = null;
    let storedTitle = "";

    try {
      raw = sessionStorage.getItem("dca-result");
      storedTitle = sessionStorage.getItem("dca-title") || "";
    } catch {
      // sessionStorage blocked
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

  const finding = useMemo(() => {
    if (state.status !== "ready") return null;
    return state.result.findings[idx] ?? state.result.findings[0] ?? null;
  }, [state, idx]);

  const arc = useMemo(() => {
    if (state.status !== "ready" || !finding) return null;
    const n = state.result.clauses.length;
    if (n === 0) return null;
    const x1 = finding.order_a * 28 + 20;
    const x2 = finding.order_b * 28 + 20;
    const mid = (x1 + x2) / 2;
    const lift = Math.min(120, 28 + Math.abs(x2 - x1) * 0.35);
    return { path: `M ${x1} 130 Q ${mid} ${130 - lift} ${x2} 130`, x1, x2 };
  }, [state, finding]);

  // ── Loading ──────────────────────────────────────────────────────────────
  if (state.status === "loading") {
    return (
      <div className="min-h-full">
        <Nav current="/explorer" />
        <main className="mx-auto max-w-3xl px-4 py-16 text-center text-[var(--muted)]">
          <div className="inline-block h-8 w-8 animate-spin rounded-full border-2 border-[var(--line)] border-t-[var(--ink)]" />
          <p className="mt-4 text-sm">Loading explorer…</p>
        </main>
      </div>
    );
  }

  // ── Empty ────────────────────────────────────────────────────────────────
  if (state.status === "empty") {
    return (
      <div className="min-h-full">
        <Nav current="/explorer" />
        <main className="mx-auto max-w-3xl px-4 py-16 text-center">
          <div className="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-full border-2 border-dashed border-[var(--line)]">
            <span className="text-2xl">🗺</span>
          </div>
          <h1 className="font-serif text-3xl">Nothing to explore</h1>
          <p className="mt-3 text-[var(--muted)]">Analyze a contract first to see the arc diagram.</p>
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

  // ── Ready ─────────────────────────────────────────────────────────────────
  const { result, title } = state;
  const n = result.clauses.length;
  const width = Math.max(640, n * 28 + 40);

  const safeIdx = Math.min(idx, result.findings.length - 1);

  return (
    <div className="min-h-full">
      <Nav current="/explorer" />
      <main className="mx-auto max-w-6xl px-4 py-8">
        {title && <p className="text-sm text-[var(--muted)]">{title}</p>}
        <h1 className="mt-1 font-serif text-3xl">Conflict explorer</h1>
        <p className="mt-2 max-w-2xl text-sm text-[var(--muted)]">
          Clauses shown in document order. The arc connects the two contradictory clauses — solid arc
          = high confidence, dashed = low confidence.
        </p>

        {/* Arc diagram */}
        <div className="mt-6 overflow-x-auto rounded-xl border border-[var(--line)] bg-white p-4">
          {n === 0 ? (
            <p className="py-8 text-center text-sm text-[var(--muted)]">No clauses segmented.</p>
          ) : (
            <svg width={width} height={180} className="block" aria-label="Clause arc diagram">
              {/* Baseline */}
              <line x1="0" y1="130" x2={width} y2="130" stroke="var(--line)" strokeWidth="1" />

              {/* Arc */}
              {arc && finding ? (
                <>
                  <path
                    d={arc.path}
                    fill="none"
                    stroke={finding.confidence === "low" ? "var(--muted)" : "var(--accent)"}
                    strokeWidth={finding.confidence === "high" ? 2.5 : 1.5}
                    strokeDasharray={finding.confidence === "low" ? "6 4" : undefined}
                    opacity={finding.confidence === "low" ? 0.6 : 1}
                  />
                  {/* Score label at arc peak */}
                  <text
                    x={(arc.x1 + arc.x2) / 2}
                    y={130 - Math.min(120, 28 + Math.abs(arc.x2 - arc.x1) * 0.35) - 6}
                    textAnchor="middle"
                    fontSize="10"
                    fill="var(--accent)"
                  >
                    {finding.score.toFixed(2)}
                  </text>
                </>
              ) : null}

              {/* Clause nodes */}
              {result.clauses.map((c) => {
                const isA = finding && c.clause_id === finding.clause_id_a;
                const isB = finding && c.clause_id === finding.clause_id_b;
                const active = isA || isB;
                const cx = c.order * 28 + 20;
                return (
                  <g key={c.clause_id} transform={`translate(${cx}, 130)`}>
                    <circle
                      r={active ? 8 : 4}
                      fill={isA ? "#7a2e24" : isB ? "#9a4030" : "var(--muted)"}
                      opacity={active ? 1 : 0.4}
                    />
                    {active && (
                      <circle r={12} fill="none" stroke="var(--accent)" strokeWidth="1" opacity="0.4" />
                    )}
                    <text
                      y="22"
                      textAnchor="middle"
                      fill="var(--muted)"
                      fontSize={active ? "10" : "8"}
                      fontWeight={active ? "bold" : "normal"}
                    >
                      {c.order + 1}
                    </text>
                    {active && (
                      <text y="36" textAnchor="middle" fill="var(--accent)" fontSize="8">
                        {isA ? "A" : "B"}
                      </text>
                    )}
                  </g>
                );
              })}
            </svg>
          )}
        </div>

        {/* Clause text panels */}
        {finding ? (
          <div className="mt-6 grid gap-4 lg:grid-cols-2">
            <article className="rounded-xl border border-[var(--accent)]/40 bg-white p-4">
              <div className="flex items-center gap-2">
                <span className="rounded bg-[var(--accent)] px-1.5 py-0.5 text-xs font-bold text-[var(--paper)]">A</span>
                <h2 className="text-sm font-medium text-[var(--accent)] line-clamp-1">
                  {finding.heading_a || finding.clause_id_a}
                </h2>
              </div>
              <p className="mt-3 whitespace-pre-wrap text-sm leading-6">
                {finding.span_a}
              </p>
            </article>
            <article className="rounded-xl border border-[var(--accent)]/40 bg-white p-4">
              <div className="flex items-center gap-2">
                <span className="rounded bg-[var(--accent)] px-1.5 py-0.5 text-xs font-bold text-[var(--paper)]">B</span>
                <h2 className="text-sm font-medium text-[var(--accent)] line-clamp-1">
                  {finding.heading_b || finding.clause_id_b}
                </h2>
              </div>
              <p className="mt-3 whitespace-pre-wrap text-sm leading-6">
                {finding.span_b}
              </p>
            </article>
          </div>
        ) : (
          <p className="mt-6 text-sm text-[var(--muted)]">No finding to highlight.</p>
        )}

        {/* Finding selector */}
        {result.findings.length > 0 && (
          <div className="mt-6">
            <p className="mb-2 text-xs uppercase tracking-wide text-[var(--muted)]">
              All findings ({result.findings.length})
            </p>
            <div className="flex flex-wrap gap-2">
              {result.findings.map((f, i) => (
                <Link
                  key={i}
                  href={`/explorer?i=${i}`}
                  className={`rounded-full px-3 py-1 text-xs transition-colors ${
                    i === safeIdx
                      ? "bg-[var(--ink)] text-[var(--paper)]"
                      : "border border-[var(--line)] hover:border-[var(--ink)]"
                  }`}
                >
                  {i + 1} · {f.type}
                </Link>
              ))}
            </div>
          </div>
        )}

        {/* Back to results */}
        <div className="mt-8 border-t border-[var(--line)] pt-4">
          <Link href="/results" className="text-sm text-[var(--muted)] hover:text-[var(--ink)] transition-colors">
            ← Back to results table
          </Link>
        </div>
      </main>
    </div>
  );
}

export default function ExplorerPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-full">
          <Nav current="/explorer" />
          <main className="mx-auto max-w-3xl px-4 py-16 text-center text-[var(--muted)]">
            <div className="inline-block h-8 w-8 animate-spin rounded-full border-2 border-[var(--line)] border-t-[var(--ink)]" />
            <p className="mt-4 text-sm">Loading explorer…</p>
          </main>
        </div>
      }
    >
      <ExplorerInner />
    </Suspense>
  );
}
