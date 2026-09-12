from __future__ import annotations

import re
from dataclasses import dataclass, field


HEADING_RE = re.compile(
    r"(?m)^(?P<head>\s*(?:Section\s+)?\d+(?:\.\d+)*\s*(?:\([a-z0-9]+\))?\.?\s+[A-Z][^\n]{0,80})",
)
ALT_HEADING_RE = re.compile(
    r"(?m)^(?P<head>\s*(?:ARTICLE|Article|SECTION|Section)\s+[IVXLC\d]+[^\n]{0,80})",
)


@dataclass
class Clause:
    clause_id: str
    heading: str
    text: str
    start: int
    end: int
    order: int


def segment_contract(text: str) -> list[Clause]:
    """Split a contract into headed sections; fall back to paragraphs."""
    text = text.replace("\r\n", "\n")
    if not text.strip():
        return []
    matches: list[tuple[int, str]] = []
    for rx in (HEADING_RE, ALT_HEADING_RE):
        for m in rx.finditer(text):
            matches.append((m.start(), m.group("head").strip()))
    matches = sorted(set(matches), key=lambda x: x[0])
    # de-dupe starts
    uniq: list[tuple[int, str]] = []
    seen = set()
    for start, head in matches:
        if start in seen:
            continue
        seen.add(start)
        uniq.append((start, head))
    clauses: list[Clause] = []
    if len(uniq) >= 3:
        for i, (start, head) in enumerate(uniq):
            end = uniq[i + 1][0] if i + 1 < len(uniq) else len(text)
            body = text[start:end].strip()
            if len(body) < 40:
                continue
            clauses.append(
                Clause(
                    clause_id=f"c{len(clauses)}",
                    heading=head[:120],
                    text=body[:4000],
                    start=start,
                    end=end,
                    order=len(clauses),
                )
            )
        if clauses:
            return clauses
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if len(p.strip()) > 80]
    if not paras:
        paras = [text.strip()[:4000]]
    for i, para in enumerate(paras[:80]):
        start = text.find(para[:80]) if para else 0
        clauses.append(
            Clause(
                clause_id=f"c{i}",
                heading=para.split("\n", 1)[0][:80],
                text=para[:4000],
                start=max(start, 0),
                end=max(start, 0) + len(para),
                order=i,
            )
        )
    return clauses


REF_RE = re.compile(r"(?:Section|Clause|Article)\s+(\d+(?:\.\d+)*)", re.I)
TERM_RE = re.compile(r"\b([A-Z][A-Za-z]{3,}(?:\s+[A-Z][A-Za-z]{3,}){0,3})\b")


def candidate_pairs(clauses: list[Clause], max_pairs: int = 200) -> list[tuple[int, int, str]]:
    """Return (i, j, reason) pairs to score. Structure-guided, not all-pairs."""
    n = len(clauses)
    scored: dict[tuple[int, int], str] = {}

    def add(i: int, j: int, reason: str) -> None:
        if i == j:
            return
        a, b = (i, j) if i < j else (j, i)
        if (a, b) not in scored:
            scored[(a, b)] = reason

    for i in range(n - 1):
        add(i, i + 1, "NEXT")
        if i + 2 < n:
            add(i, i + 2, "NEXT")

    heading_index: dict[str, int] = {}
    for i, c in enumerate(clauses):
        m = re.search(r"(\d+(?:\.\d+)*)", c.heading)
        if m:
            heading_index[m.group(1)] = i
    for i, c in enumerate(clauses):
        for ref in REF_RE.findall(c.text[:1500]):
            if ref in heading_index:
                add(i, heading_index[ref], "REFERENCES")

    term_map: dict[str, list[int]] = {}
    for i, c in enumerate(clauses):
        terms = {t.lower() for t in TERM_RE.findall(c.text[:800]) if len(t) > 5}
        for t in list(terms)[:12]:
            term_map.setdefault(t, []).append(i)
    for ids in term_map.values():
        uniq = sorted(set(ids))
        if 2 <= len(uniq) <= 6:
            add(uniq[0], uniq[-1], "SHARED_TERM")
            if len(uniq) > 2:
                add(uniq[0], uniq[len(uniq) // 2], "SHARED_TERM")

    # far pairs: first third vs last third
    if n >= 6:
        far_n = min(12, max(4, n // 4))
        for i in range(far_n):
            add(i, n - 1 - (i % max(n // 3, 1)), "FAR")
        mid = n // 2
        for i in range(min(6, n // 5 or 1)):
            add(i, min(mid + i, n - 1), "FAR")

    pairs = [(a, b, reason) for (a, b), reason in scored.items()]
    pairs.sort(key=lambda x: (x[0], x[1]))
    return pairs[:max_pairs]
