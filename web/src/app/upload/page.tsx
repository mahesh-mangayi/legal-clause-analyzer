"use client";

import { Nav } from "@/components/nav";
import { analyzeContract, fetchSamples, type Sample } from "@/lib/api";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

const STAGES = [
  { key: "segment_ms", label: "Segment clauses" },
  { key: "candidates_ms", label: "Structure-guided pair candidates" },
  { key: "score_ms", label: "Score pairs" },
  { key: "total_ms", label: "Total" },
];

export default function UploadPage() {
  const router = useRouter();
  const [samples, setSamples] = useState<Sample[]>([]);
  const [text, setText] = useState("");
  const [title, setTitle] = useState("Pasted contract");
  const [error, setError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [stage, setStage] = useState(0);
  const [timings, setTimings] = useState<Record<string, number> | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    fetchSamples()
      .then((d) => setSamples(d.samples || []))
      .catch(() => setLoadError("Could not load CLAUSE samples. Is the API running on port 8765?"));
  }, []);

  async function run() {
    setError(null);
    if (text.trim().length < 80) {
      setError("Paste a longer contract excerpt (at least a few clauses).");
      return;
    }
    setRunning(true);
    setStage(0);
    setTimings(null);
    const tick = window.setInterval(() => {
      setStage((s) => Math.min(s + 1, STAGES.length - 2));
    }, 280);
    try {
      const result = await analyzeContract(text);
      window.clearInterval(tick);
      setStage(STAGES.length - 1);
      setTimings(result.timings);
      sessionStorage.setItem("dca-result", JSON.stringify(result));
      sessionStorage.setItem("dca-title", title);
      sessionStorage.setItem("dca-text", text);
      window.setTimeout(() => router.push("/results"), 450);
    } catch (e) {
      window.clearInterval(tick);
      setRunning(false);
      setError(e instanceof Error ? e.message : "Analyze failed");
    }
  }

  return (
    <div className="min-h-full">
      <Nav current="/upload" />
      <main className="mx-auto grid max-w-6xl gap-8 px-4 py-8 lg:grid-cols-[1fr_280px]">
        <section>
          <h1 className="font-serif text-3xl">Upload or pick a CLAUSE sample</h1>
          <p className="mt-2 text-sm text-[var(--muted)]">
            Processing shows real pipeline stages — segment, candidate pairs, score — not a spinner.
          </p>
          {loadError ? <p className="mt-4 text-sm text-[var(--accent)]">{loadError}</p> : null}
          <label className="mt-6 block text-sm font-medium">Contract text</label>
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={16}
            className="mt-2 w-full rounded-xl border border-[var(--line)] bg-white p-3 text-sm leading-6 outline-none focus:border-[var(--ink)]"
            placeholder="Paste contract text…"
          />
          {error ? <p className="mt-2 text-sm text-[var(--accent)]">{error}</p> : null}
          <button
            type="button"
            onClick={run}
            disabled={running}
            className="mt-4 rounded-full bg-[var(--ink)] px-5 py-2.5 text-sm text-[var(--paper)] disabled:opacity-50"
          >
            {running ? "Running pipeline…" : "Run auditor"}
          </button>
          {running || timings ? (
            <ol className="mt-6 space-y-2">
              {STAGES.map((s, i) => {
                const done = timings ? true : i <= stage;
                const ms = timings?.[s.key];
                return (
                  <li
                    key={s.key}
                    className={`flex items-center justify-between rounded-lg border px-3 py-2 text-sm ${
                      done ? "border-[var(--ok)]/30 bg-white" : "border-[var(--line)] text-[var(--muted)]"
                    }`}
                  >
                    <span>
                      {i + 1}. {s.label}
                    </span>
                    <span className="font-mono text-xs">
                      {ms != null ? `${Math.round(ms)} ms` : done ? "…" : ""}
                    </span>
                  </li>
                );
              })}
            </ol>
          ) : null}
        </section>
        <aside>
          <h2 className="text-sm font-medium uppercase tracking-wide text-[var(--muted)]">
            CLAUSE samples
          </h2>
          <ul className="mt-3 space-y-2">
            {samples.length === 0 && !loadError ? (
              <li className="text-sm text-[var(--muted)]">Loading samples…</li>
            ) : null}
            {samples.map((s) => (
              <li key={s.id}>
                <button
                  type="button"
                  className="w-full rounded-lg border border-[var(--line)] bg-white p-3 text-left text-sm hover:border-[var(--ink)]"
                  onClick={() => {
                    setText(s.text);
                    setTitle(s.title);
                  }}
                >
                  <div className="font-medium">{s.title}</div>
                  <div className="mt-1 text-xs text-[var(--muted)]">
                    {s.corpus.toUpperCase()} · {s.n_gold} gold conflicts
                  </div>
                </button>
              </li>
            ))}
          </ul>
        </aside>
      </main>
    </div>
  );
}
