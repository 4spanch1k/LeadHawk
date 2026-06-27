from __future__ import annotations

from datetime import datetime, timedelta, timezone

from constants import HIGH_VALUE_CATEGORIES, PROJECT_SIGNALS
from lead_filter import looks_like_job
from text_processing import normalize_text


def score_lead(
    *,
    text: str,
    task_summary: str,
    category: str,
    budget: str | None,
    contact_usernames: tuple[str, ...],
    sender_username: str | None,
    published_at: datetime,
    now: datetime | None = None,
) -> int:
    current_time = now or datetime.now(timezone.utc)
    published = (
        published_at.replace(tzinfo=timezone.utc)
        if published_at.tzinfo is None
        else published_at.astimezone(timezone.utc)
    )
    score = 0
    if len(task_summary) >= 20:
        score += 25
    if budget:
        score += 20
    if contact_usernames or sender_username:
        score += 20
    if current_time - published <= timedelta(hours=24):
        score += 15
    normalized = normalize_text(text)
    if any(signal in normalized for signal in PROJECT_SIGNALS):
        score += 10
    if category in HIGH_VALUE_CATEGORIES:
        score += 10
    if looks_like_job(text):
        score -= 40
    if not contact_usernames and not sender_username:
        score -= 20
    if len(normalized) < 30:
        score -= 20
    return max(0, min(100, score))
