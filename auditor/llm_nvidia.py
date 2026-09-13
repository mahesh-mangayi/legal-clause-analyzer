"""NVIDIA Build OpenAI-compatible chat: JSON pair list from a long contract."""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request

from pathlib import Path

NVIDIA_URL = "https://integrate.api.nvidia.com/v1/chat/completions"


def _load_env() -> None:
    env_file = Path(".env")
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k, v = k.strip(), v.strip().strip("'\"")
            if k and not os.environ.get(k):
                os.environ[k] = v


FALLBACK_MODELS = [
    "deepseek-ai/deepseek-v4-pro-0813",
    "nvidia/llama-3.1-nemotron-70b-instruct",
    "nvidia/nemotron-4-340b-instruct",
    "mistralai/mistral-large-2-instruct",
]

SYSTEM = (
    "You are a contract reviewer. List pairs of clauses that disagree or are inconsistent. "
    "Reply with JSON only: a list of objects with keys span_a, span_b, type. "
    "type must be one of Ambiguity, Inconsistency, MisalignedTerminology, Omission, StructuralFlaws. "
    "Copy short clause excerpts from the contract. Do not invent sections. Prefer precision over recall."
)


def predict_pairs(contract_text: str, model: str = "deepseek-ai/deepseek-v4-pro-0813", temperature: float = 0.2, timeout: int = 180) -> list[dict]:
    _load_env()
    key = os.environ.get("NVIDIA_API_KEY") or os.environ.get("NGC_API_KEY")
    if not key:
        raise RuntimeError(
            "Set NVIDIA_API_KEY environment variable or place NVIDIA_API_KEY=nvapi-... in a .env file."
        )

    candidate_models = [model] + [m for m in FALLBACK_MODELS if m != model]
    last_err = None

    for m_name in candidate_models:
        body = {
            "model": m_name,
            "temperature": temperature,
            "top_p": 0.95,
            "max_tokens": 8192,
            "seed": 42,
            "extra_body": {"chat_template_kwargs": {"thinking": False}},
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
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            text = payload["choices"][0]["message"]["content"]
            return _parse_json_list(text)
        except urllib.error.HTTPError as err:
            last_err = err
            if err.code in (404, 410):
                continue
            raise err

    if last_err:
        raise last_err
    return []


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
