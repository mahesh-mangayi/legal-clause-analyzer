"use client";

import { Nav } from "@/components/nav";
import type { AnalyzeResult } from "@/lib/api";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useMemo, useState } from "react";

function ExplorerInner() {
  const params = useSearchParams();
  const idx = Number(params.get("i") || "0");
  const [result, setResult] = useState<AnalyzeResult | null>(null);
  const [title, setTitle] = useState("");
  const [empty, setEmpty] = useState(false);

  useEffect(() => {
    const raw = sessionStorage.getItem("dca-result");
    setTitle(sessionStorage.getItem("dca-title") || "");
    if (!raw) {
      setEmpty(true);
      return;
    }
    setResult(JSON.parse(raw) as AnalyzeResult);
  }, []);

  const finding = result?.findings[idx] ?? result?.findings[0];
  const n = result?.clauses.length ?? 0;
  const width = Math.max(640, n * 28);

  const arc = useMemo(() => {
    if (!finding || n === 0) return null;
    const x1 = finding.order_a * 28 + 20;
    const x2 = finding.order_b * 28 + 20;
    const mid = (x1 + x2) / 2;
    const lift = Math.min(120, 28 + Math.abs(x2 - x1) * 0.35);
    return `M ${x1} 130 Q ${mid} ${130 - lift} ${x2} 130`;
  }, [finding, n]);

  if (empty) {
    return (
      <div className="min-h-full">
        <Nav current="/explorer" />
        <main className="mx-auto max-w-3xl px-4 py-16 text-center">
          <h1 className="font-serif text-3xl">Nothing to explore</h1>
          <Link href="/upload" className="mt-6 inline-block text-[var(--accent)] underline">
            Analyze a contract
          </Link>
        </main>
      </div>
    );
  }

  if (!result) {
    return (
      <div className="min-h-full">
        <Nav current="/explorer" />
        <main className="p-8 text-[var(--muted)]">Loading…</main>
      </div>
    );
  }

  return (
    <div className="min-h-full">
      <Nav current="/explorer" />
      <main className="mx-auto max-w-6xl px-4 py-8">
        <p className="text-sm text-[var(--muted)]">{title}</p>
        <h1 className="font-serif text-3xl">Conflict explorer</h1>
        <p className="mt-2 max-w-2xl text-sm text-[var(--muted)]">
          Clauses in document order. The arc is the scored pair — BCC gold is two spans, not a 3-hop
          path.
        </p>
        <div className="mt-6 overflow-x-auto rounded-xl border border-[var(--line)] bg-white p-4">
          <svg width={width} height={160} className="block">
            {arc && finding ? (
              <path
                d={arc}
                fill="none"
                stroke={finding.confidence === "low" ? "#6b6258" : "#7a2e24"}
                strokeWidth="2"
                strokeDasharray={finding.confidence === "low" ? "6 4" : undefined}
              />
            ) : null}
            {result.clauses.map((c) => {
              const active =
                finding && (c.clause_id === finding.clause_id_a || c.clause_id === finding.clause_id_b);
              return (
                <g key={c.clause_id} transform={`translate(${c.order * 28 + 20}, 130)`}>
                  <circle r={active ? 7 : 4} fill={active ? "#7a2e24" : "#1c1915"} />
                  <text y="22" x="-6" className="fill-[var(--muted)]" fontSize="9">
                    {c.order + 1}
                  </text>
                </g>
              );
            })}
          </svg>
        </div>
        {finding ? (
          <div className="mt-6 grid gap-4 lg:grid-cols-2">
            <article className="rounded-xl border border-[var(--accent)]/40 bg-white p-4">
              <h2 className="text-sm font-medium text-[var(--accent)]">{finding.heading_a}</h2>
              <p className="mt-3 whitespace-pre-wrap text-sm leading-6">{finding.span_a}</p>
            </article>
            <article className="rounded-xl border border-[var(--accent)]/40 bg-white p-4">
              <h2 className="text-sm font-medium text-[var(--accent)]">{finding.heading_b}</h2>
              <p className="mt-3 whitespace-pre-wrap text-sm leading-6">{finding.span_b}</p>
            </article>
          </div>
        ) : (
          <p className="mt-6 text-sm text-[var(--muted)]">No finding to highlight.</p>
        )}
        <div className="mt-6 flex flex-wrap gap-2">
          {result.findings.map((f, i) => (
            <Link
              key={i}
              href={`/explorer?i=${i}`}
              className={`rounded-full px-3 py-1 text-xs ${
                i === idx ? "bg-[var(--ink)] text-[var(--paper)]" : "border border-[var(--line)]"
              }`}
            >
              {i + 1} {f.type}
            </Link>
          ))}
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
          <main className="p-8 text-[var(--muted)]">Loading explorer…</main>
        </div>
      }
    >
      <ExplorerInner />
    </Suspense>
  );
}
