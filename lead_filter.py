from __future__ import annotations

from constants import (
    GOOD_KEYWORDS,
    JOB_KEYWORDS,
    PROJECT_SIGNALS,
    STRONG_JOB_KEYWORDS,
)
from text_processing import normalize_text


def looks_like_job(text: str) -> bool:
    normalized = f" {normalize_text(text)} "
    if any(keyword in normalized for keyword in STRONG_JOB_KEYWORDS):
        return True
    has_job_signal = any(keyword in normalized for keyword in JOB_KEYWORDS)
    has_project_signal = any(signal in normalized for signal in PROJECT_SIGNALS)
    return has_job_signal and not has_project_signal


def is_lead(text: str) -> bool:
    normalized = normalize_text(text)
    if not normalized or not any(keyword in normalized for keyword in GOOD_KEYWORDS):
        return False
    return not looks_like_job(normalized)
