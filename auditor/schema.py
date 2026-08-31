from __future__ import annotations

TYPE_MAP = {
    "ambiguity": "Ambiguity",
    "ambiguities": "Ambiguity",
    "omission": "Omission",
    "omissions": "Omission",
    "misaligned": "MisalignedTerminology",
    "terminology": "MisalignedTerminology",
    "structural": "StructuralFlaws",
    "inconsistenc": "Inconsistency",
}

CANONICAL_TYPES = [
    "Ambiguity",
    "Omission",
    "MisalignedTerminology",
    "StructuralFlaws",
    "Inconsistency",
]


def normalize_type(raw: str | None) -> str:
    if not raw:
        return "Inconsistency"
    lower = raw.lower()
    for key, value in TYPE_MAP.items():
        if key in lower:
            return value
    return "Inconsistency"


def is_legal(raw: str | None, fields: dict | None = None) -> bool:
    text = (raw or "").lower()
    if "legal" in text and "in text" not in text and "in-text" not in text:
        return True
    if fields and (fields.get("law_citation") or fields.get("contradicted_law")):
        return True
    return False


def contradiction_yes(value: object) -> bool:
    if value is None:
        return True
    return str(value).strip().upper() in {"YES", "Y", "TRUE", "1"}


def parse_section_key(location: str | None) -> tuple[int | None, str]:
    """Best-effort first integer in a location string for gap bins."""
    if not location:
        return None, ""
    cleaned = location.strip()
    num = ""
    for ch in cleaned:
        if ch.isdigit():
            num += ch
        elif num:
            break
    if not num:
        return None, cleaned.lower()
    try:
        return int(num), cleaned.lower()
    except ValueError:
        return None, cleaned.lower()


def section_gap(loc_a: str | None, loc_b: str | None) -> int | None:
    a, _ = parse_section_key(loc_a)
    b, _ = parse_section_key(loc_b)
    if a is None or b is None:
        return None
    return abs(a - b)


def gap_bin(gap: int | None) -> str:
    if gap is None:
        return "unknown"
    if gap <= 0:
        return "same_section"
    if gap <= 3:
        return "nearby"
    return "far"


def truncate(text: str | None, limit: int = 1800) -> str:
    if not text:
        return ""
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"
