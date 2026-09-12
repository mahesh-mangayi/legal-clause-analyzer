"""NVIDIA Build OpenAI-compatible chat: JSON pair list from a long contract."""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request

NVIDIA_URL = "https://integrate.api.nvidia.com/v1/chat/completions"

SYSTEM = (
    "You are a contract reviewer. List pairs of clauses that disagree or are inconsistent. "
    "Reply with JSON only: a list of objects with keys span_a, span_b, type. "
    "type must be one of Ambiguity, Inconsistency, MisalignedTerminology, Omission, StructuralFlaws. "
    "Copy short clause excerpts from the contract. Do not invent sections. Prefer precision over recall."
)


def predict_pairs(contract_text: str, model: str, temperature: float = 0.2, timeout: int = 180) -> list[dict]:
    key = os.environ.get("NVIDIA_API_KEY") or os.environ.get("NGC_API_KEY")
    if not key:
        raise RuntimeError("Set NVIDIA_API_KEY for NVIDIA Build eval.")
    body = {
        "model": model,
        "temperature": temperature,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {
                "role": "user",
                "content": "Contract:\n" + contract_text + "\n\nJSON list of disagreeing pairs:",
            },
        ],
    }
    req = urllib.request.Request(
        NVIDIA_URL,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    text = payload["choices"][0]["message"]["content"]
    return _parse_json_list(text)


def _parse_json_list(text: str) -> list[dict]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text).strip()
        text = re.sub(r"```$", "", text).strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\[.*\]", text, re.S)
        if not match:
            return []
        data = json.loads(match.group(0))
    if not isinstance(data, list):
        return []
    out = []
    for item in data:
        if not isinstance(item, dict):
            continue
        a = item.get("span_a") or item.get("text_a") or ""
        b = item.get("span_b") or item.get("text_b") or ""
        if len(str(a)) < 20 or len(str(b)) < 20:
            continue
        out.append(
            {
                "span_a": str(a)[:900],
                "span_b": str(b)[:900],
                "type": item.get("type") or "Inconsistency",
            }
        )
    return out
