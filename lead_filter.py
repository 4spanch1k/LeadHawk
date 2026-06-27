from __future__ import annotations

from constants import GOOD_KEYWORDS, JOB_KEYWORDS, PROJECT_SIGNALS
from utils import normalize_text


def looks_like_job(text: str) -> bool:
    normalized = f" {normalize_text(text)} "
    job_matches = sum(keyword in normalized for keyword in JOB_KEYWORDS)
    project_matches = sum(signal in normalized for signal in PROJECT_SIGNALS)
    return job_matches > 0 and project_matches == 0


def is_lead(text: str) -> bool:
    normalized = normalize_text(text)
    if not normalized or not any(keyword in normalized for keyword in GOOD_KEYWORDS):
        return False
    return not looks_like_job(normalized)

