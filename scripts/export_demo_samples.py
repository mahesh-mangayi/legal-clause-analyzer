#!/usr/bin/env python3
"""Bundle a handful of BCC in-text examples for the live demo."""

from __future__ import annotations

import json
from pathlib import Path

from auditor.ingest import _load_json
from auditor.schema import contradiction_yes, is_legal, normalize_type, truncate


def main() -> None:
    root = Path("data/clause-legal/datasets")
    samples = []
    for path in sorted(root.rglob("*.json")):
        if "inText" not in path.as_posix() and "in_text" not in path.as_posix() and "intext" not in path.parent.name.lower():
            # keep in-text folders only
            name = path.parent.name.lower()
            if "legal" in name:
                continue
        for rec in _load_json(path):
            perts = rec.get("perturbation") or []
            if not isinstance(perts, list) or not perts:
                continue
            file_name = rec.get("file_name") or path.stem
            chunks = []
            findings = []
            for pert in perts:
                if not isinstance(pert, dict) or not contradiction_yes(pert.get("contradiction_exists")):
                    continue
                if is_legal(pert.get("type"), pert):
                    continue
                a = pert.get("changed_text") or ""
                b = pert.get("contradicted_text") or ""
                if len(a) < 80 or len(b) < 80:
                    continue
                loc_a = pert.get("location") or "Changed provision"
                loc_b = pert.get("contradicted_location") or "Contradicted provision"
                chunks.append(f"{loc_a}\n{a}")
                chunks.append(f"{loc_b}\n{b}")
                findings.append(
                    {
                        "type": normalize_type(pert.get("type")),
                        "location_a": loc_a,
                        "location_b": loc_b,
                        "explanation": truncate(pert.get("justification") or pert.get("explanation") or "", 500),
                    }
                )
            if len(findings) < 1:
                continue
            body = "\n\n".join(chunks)
            if len(body) < 400:
                continue
            samples.append(
                {
                    "id": f"sample-{len(samples)+1}",
                    "title": str(file_name)[:80],
                    "corpus": "nli" if "NLI" in path.as_posix() else "cuad",
                    "n_gold": len(findings),
                    "gold": findings[:4],
                    "text": body[:12000],
                }
            )
            if len(samples) >= 8:
                break
        if len(samples) >= 8:
            break

    out = Path("artifacts/demo_samples.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"samples": samples}, indent=2), encoding="utf-8")
    print(f"wrote {len(samples)} samples -> {out}")


if __name__ == "__main__":
    main()
