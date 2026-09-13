"use client";

import { Nav } from "@/components/nav";
import { analyzeContract, type Sample } from "@/lib/api";
import bundled from "@/data/samples.json";
import { useRouter } from "next/navigation";
import { useRef, useState } from "react";

const STAGES = [
  { key: "segment_ms", label: "Segment clauses" },
  { key: "candidates_ms", label: "Structure-guided pair candidates" },
  { key: "score_ms", label: "Score pairs" },
  { key: "total_ms", label: "Total" },
];

const BUNDLED_SAMPLES = (bundled as { samples: Sample[] }).samples;

export default function UploadPage() {
  const router = useRouter();
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [text, setText] = useState("");
  const [title, setTitle] = useState("Pasted contract");
  const [error, setError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [stage, setStage] = useState(0);
  const [timings, setTimings] = useState<Record<string, number> | null>(null);
  const [done, setDone] = useState(false);

  function loadSample(s: Sample) {
    setText(s.text);
    setTitle(s.title);
    setError(null);
    setTimings(null);
    setDone(false);
    setStage(0);
    // Focus textarea so user can see the loaded text
    setTimeout(() => textareaRef.current?.focus(), 50);
  }

  async function run() {
    setError(null);
    setDone(false);
    const trimmed = text.trim();
    if (trimmed.length < 80) {
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
      const result = await analyzeContract(trimmed);
      window.clearInterval(tick);
      setStage(STAGES.length - 1);
      setTimings(result.timings);
      setDone(true);

      // Write to sessionStorage synchronously before navigation
      try {
        sessionStorage.setItem("dca-result", JSON.stringify(result));
        sessionStorage.setItem("dca-title", title);
        sessionStorage.setItem("dca-text", trimmed);
      } catch {
        // sessionStorage can fail in private browsing — still navigate
      }

      // Small delay so the user sees the "Total" timing row complete
      window.setTimeout(() => {
        setRunning(false);
        router.push("/results");
      }, 700);
    } catch (e) {
      window.clearInterval(tick);
      setRunning(false);
      setDone(false);
      setError(
        e instanceof Error
          ? e.message
          : "Analysis failed — is the backend running on port 8765?"
      );
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

          {/* Contract title */}
          <label className="mt-6 block text-sm font-medium" htmlFor="contract-title">
            Contract title
          </label>
          <input
            id="contract-title"
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="mt-1 w-full rounded-lg border border-[var(--line)] bg-white px-3 py-2 text-sm outline-none focus:border-[var(--ink)]"
            placeholder="My contract"
          />

          {/* Contract text */}
          <label className="mt-4 block text-sm font-medium" htmlFor="contract-text">
            Contract text
          </label>
          <textarea
            id="contract-text"
            ref={textareaRef}
            value={text}
            onChange={(e) => {
              setText(e.target.value);
              setError(null);
              setTimings(null);
              setDone(false);
            }}
            rows={16}
            className="mt-2 w-full rounded-xl border border-[var(--line)] bg-white p-3 text-sm leading-6 outline-none focus:border-[var(--ink)]"
            placeholder="Paste contract text…"
            disabled={running}
          />

          {error ? (
            <p className="mt-2 rounded-lg border border-[var(--accent)]/40 bg-white px-3 py-2 text-sm text-[var(--accent)]">
              ⚠ {error}
            </p>
          ) : null}

          <button
            type="button"
            onClick={run}
            disabled={running || text.trim().length < 10}
            className="mt-4 rounded-full bg-[var(--ink)] px-5 py-2.5 text-sm text-[var(--paper)] disabled:opacity-50 hover:opacity-90 transition-opacity"
          >
            {running ? "Running pipeline…" : done ? "✓ Done — redirecting…" : "Run auditor"}
          </button>

          {/* Pipeline stage indicators */}
          {(running || timings) ? (
            <ol className="mt-6 space-y-2">
              {STAGES.map((s, i) => {
                const active = !timings && i === stage;
                const complete = timings ? true : i < stage;
                const ms = timings?.[s.key];
                return (
                  <li
                    key={s.key}
                    className={`flex items-center justify-between rounded-lg border px-3 py-2 text-sm transition-colors ${
                      complete || active
                        ? "border-[var(--ok)]/40 bg-white"
                        : "border-[var(--line)] text-[var(--muted)]"
                    }`}
                  >
                    <span className="flex items-center gap-2">
                      <span
                        className={`inline-block h-2 w-2 rounded-full ${
                          complete ? "bg-[var(--ok)]" : active ? "bg-[var(--warn)] animate-pulse" : "bg-[var(--line)]"
                        }`}
                      />
                      {i + 1}. {s.label}
                    </span>
                    <span className="font-mono text-xs">
                      {ms != null ? `${Math.round(ms)} ms` : active ? "…" : ""}
                    </span>
                  </li>
                );
              })}
            </ol>
          ) : null}
        </section>

        {/* Sample contracts sidebar */}
        <aside>
          <h2 className="text-sm font-medium uppercase tracking-wide text-[var(--muted)]">
            CLAUSE samples
          </h2>
          {BUNDLED_SAMPLES.length === 0 ? (
            <p className="mt-3 text-xs text-[var(--muted)]">No samples available.</p>
          ) : (
            <ul className="mt-3 space-y-2">
              {BUNDLED_SAMPLES.map((s) => (
                <li key={s.id}>
                  <button
                    type="button"
                    disabled={running}
                    className="w-full rounded-lg border border-[var(--line)] bg-white p-3 text-left text-sm hover:border-[var(--ink)] transition-colors disabled:opacity-50"
                    onClick={() => loadSample(s)}
                  >
                    <div className="font-medium line-clamp-2">{s.title}</div>
                    <div className="mt-1 text-xs text-[var(--muted)]">
                      {s.corpus.toUpperCase()} · {s.n_gold} gold conflicts
                    </div>
                  </button>
                </li>
              ))}
            </ul>
          )}
          <p className="mt-4 text-xs leading-5 text-[var(--muted)]">
            Samples are drawn from the Better Call CLAUSE (BCC) dataset — real SEC CUAD contracts
            with annotated contradictions.
          </p>
        </aside>
      </main>
    </div>
  );
}
