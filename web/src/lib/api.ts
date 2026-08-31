export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || "/backend";

export type Finding = {
  span_a: string;
  span_b: string;
  heading_a: string;
  heading_b: string;
  clause_id_a: string;
  clause_id_b: string;
  order_a: number;
  order_b: number;
  kind: string;
  type: string;
  score: number;
  confidence: string;
  candidate_reason: string;
  gap_bin: string;
  section_gap: number;
};

export type Clause = {
  clause_id: string;
  heading: string;
  text: string;
  order: number;
  start: number;
  end: number;
};

export type AnalyzeResult = {
  clauses: Clause[];
  findings: Finding[];
  n_candidates: number;
  n_clauses: number;
  threshold: number;
  timings: Record<string, number>;
  warning?: string;
};

export type Sample = {
  id: string;
  title: string;
  corpus: string;
  n_gold: number;
  text: string;
  gold: { type: string; location_a: string; location_b: string; explanation: string }[];
};

export async function fetchMeta() {
  const res = await fetch(`${API_BASE}/meta`, { cache: "no-store" });
  if (!res.ok) throw new Error("API unavailable");
  return res.json();
}

export async function fetchSamples(): Promise<{ samples: Sample[] }> {
  const res = await fetch(`${API_BASE}/samples`, { cache: "no-store" });
  if (!res.ok) throw new Error("API unavailable");
  return res.json();
}

export async function analyzeContract(text: string, threshold = 0.55): Promise<AnalyzeResult> {
  const res = await fetch(`${API_BASE}/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, threshold }),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(detail || "Analyze failed");
  }
  return res.json();
}
