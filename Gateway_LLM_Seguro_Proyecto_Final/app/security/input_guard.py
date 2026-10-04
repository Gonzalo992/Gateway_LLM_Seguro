import re
import unicodedata
from dataclasses import dataclass


@dataclass(frozen=True)
class InputGuardResult:
    allowed: bool
    sanitized: str
    reason: str | None = None


BLOCK_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+(instructions|rules)", re.I),
    re.compile(r"disregard\s+(the\s+)?(system|developer)\s+(prompt|instructions)", re.I),
    re.compile(r"reveal\s+(the\s+)?(system|developer)\s+(prompt|instructions)", re.I),
    re.compile(r"print\s+(the\s+)?(system|developer)\s+(prompt|instructions)", re.I),
    re.compile(r"override\s+(the\s+)?(system|developer)\s+(prompt|instructions)", re.I),
]


def sanitize_user_input(raw: str, max_chars: int = 8000) -> InputGuardResult:
    text = unicodedata.normalize("NFKC", raw)
    text = "".join(ch for ch in text if ch == "\n" or ch == "\t" or ord(ch) >= 32)
    text = text.strip()

    if not text:
        return InputGuardResult(False, "", "empty_input")

    if len(text) > max_chars:
        return InputGuardResult(False, "", "input_too_long")

    for pattern in BLOCK_PATTERNS:
        if pattern.search(text):
            return InputGuardResult(False, "", "prompt_injection_pattern")

    return InputGuardResult(True, text)
